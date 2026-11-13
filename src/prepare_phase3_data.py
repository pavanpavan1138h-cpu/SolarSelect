"""
SolarSelect — Phase 3: Data Preparation, Feature Engineering, and Dual-Cohort Pipeline.

This script transforms raw UNISOLAR and Kaggle solar telemetry into clean, leakage-free,
machine-learning-ready tabular datasets. It executes the following core operations:

1. Astronomical Solar Geometry:
   - Computes deterministic extraterrestrial solar irradiance (H0), solar declination,
     solar elevation, and daylight hours from latitude, longitude, and day-of-year.
2. Valid Site-Day Filtering:
   - Enforces the a-priori valid site-day rule (requires 96 15-minute intervals per day
     and >= 26 out of 28 core daytime intervals between 09:00 and 15:45).
3. Target Definition:
   - Computes Daily Specific Yield (Yf = total daily energy in kWh / documented kWp).
4. Calendar-Aware Lag Engineering:
   - Shifts autoregressive yields and regional weather on a continuous daily grid
     (freq='D') to ensure a strict 24-hour day-ahead forecast horizon (tau >= 24h).
5. Dual-Cohort Partitioning:
   - Full Cohort (Dataset A, 24 sites): Preserves unclipped raw telemetry including
     anomalous Sites 19 and 24 for facility monitoring.
   - Peer Cohort (Dataset B, 22 sites): Quarantines Sites 19 and 24 to provide an
     uncorrupted, physically bounded benchmark for commercial rooftop models.
6. Zero-Leakage Chronological Splitting & Imputation:
   - Divides observations into Train (May–Dec 2021), Validation (Jan–Feb 2022),
     and Test (Mar–Apr 2022).
   - Missing historical lags are imputed strictly using medians computed from the
     training partition (Date <= 2021-12-31).
"""

import os
import json
import numpy as np
import pandas as pd

def calculate_solar_features(lat, lon, dt):
    """
    Computes deterministic astronomical solar features for given latitude, longitude, and date.
    Based on established NOAA / Spencer (1971) solar geometry algorithms.
    
    Parameters:
    -----------
    lat : float
        Latitude in decimal degrees (negative for Southern Hemisphere, e.g. -37.72 for Victoria, AU).
    lon : float
        Longitude in decimal degrees (e.g. 145.13 for Clayton campus).
    dt : pd.Timestamp
        Calendar date of observation.
        
    Returns:
    --------
    dict containing:
        - solar_declination_deg: Earth's axial tilt angle relative to the sun (-23.45° to +23.45°).
        - solar_noon_elevation_deg: Maximum solar angle above the horizon at midday.
        - solar_noon_zenith_deg: Angle between the sun and the vertical zenith at midday.
        - daylight_hours: Astronomical daylight duration based on sunrise/sunset hour angles.
        - extraterrestrial_radiation_h0: Daily top-of-atmosphere solar insolation (kWh/m2/day).
    """
    # 1. Day of Year (1 to 365/366)
    doy = dt.dayofyear
    
    # 2. Fractional year angle (gamma) in radians
    gamma = 2 * np.pi / 365.25 * (doy - 1)
    
    # 3. Solar declination angle (decl) in radians using Spencer (1971) Fourier expansion
    decl = (0.006918 - 0.399912 * np.cos(gamma) + 0.070257 * np.sin(gamma)
            - 0.006758 * np.cos(2 * gamma) + 0.000907 * np.sin(2 * gamma)
            - 0.002697 * np.cos(3 * gamma) + 0.00148 * np.sin(3 * gamma))
    
    lat_rad = np.radians(lat)
    
    # 4. Sunset hour angle (omega_s) in radians
    #    cos(omega_s) = -tan(latitude) * tan(declination)
    #    Clipped to [-1.0, 1.0] to handle polar day/night safely
    cos_omega_s = -np.tan(lat_rad) * np.tan(decl)
    cos_omega_s = np.clip(cos_omega_s, -1.0, 1.0)
    omega_s = np.arccos(cos_omega_s)
    
    # 5. Astronomical daylight duration (hours)
    #    Each 15 degrees of solar rotation corresponds to 1 hour of time
    daylight_hours = 2.0 * np.degrees(omega_s) / 15.0
    
    # 6. Midday solar zenith and elevation angles (degrees)
    #    At solar noon, zenith angle = |latitude - declination|
    noon_zenith = np.degrees(np.abs(lat_rad - decl))
    noon_elevation = 90.0 - noon_zenith
    
    # 7. Extraterrestrial horizontal daily solar insolation (H0 in kWh/m2/day)
    #    Gsc = Solar constant (1.367 kW/m2)
    #    dr = Earth-Sun distance eccentricity correction factor
    Gsc = 1.367
    dr = 1.0 + 0.033 * np.cos(2 * np.pi * doy / 365.25)
    H0 = (24.0 / np.pi) * Gsc * dr * (
        np.cos(lat_rad) * np.cos(decl) * np.sin(omega_s) + omega_s * np.sin(lat_rad) * np.sin(decl)
    )
    H0 = max(0.0, float(H0))
    
    return {
        'solar_declination_deg': float(np.degrees(decl)),
        'solar_noon_elevation_deg': float(noon_elevation),
        'solar_noon_zenith_deg': float(noon_zenith),
        'daylight_hours': float(daylight_hours),
        'extraterrestrial_radiation_h0': float(H0)
    }

def main():
    print("=== STARTING PHASE 3 DATA PREPARATION PIPELINE (FINAL CORRECTION PASS) ===")
    
    out_unisolar = "data/processed/unisolar"
    out_peer = "data/processed/unisolar/peer_cohort"
    out_kaggle = "data/processed/kaggle_benchmark"
    os.makedirs(out_unisolar, exist_ok=True)
    os.makedirs(out_peer, exist_ok=True)
    os.makedirs(out_kaggle, exist_ok=True)
    
    # =========================================================================
    # PART 1: UNISOLAR DATASET & CALENDAR GRID
    # =========================================================================
    # In Part 1, we:
    # 1. Ingest site metadata for Monash University Campus 1 (Clayton campus).
    # 2. Define the cohort of 24 documented installations (and 22 peer sites).
    # 3. Ingest raw 15-minute generation telemetry, adding a 2-month warm-up
    #    buffer (starting March 1, 2021) so 30-day rolling lags on May 1 are populated.
    # 4. Enforce the A-Priori Valid Site-Day Rule:
    #    - Exactly 96 15-minute intervals present per day.
    #    - >= 26 non-null readings during the 28 core midday intervals (09:00-15:45).
    #    - Documented peak capacity kWp > 0.
    # 5. Compute target daily specific yield: Yf = daily_energy_kwh / kWp (kWh/kWp/day).
    # =========================================================================
    print("\n--- Part 1: Loading UNISOLAR Metadata & Generation ---")
    
    site_details = pd.read_csv("data/raw/unisolar/Solar_Site_Details.csv")
    
    # 24 installations with documented kWp on Campus 1
    cohort_24 = [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40]
    # Peer cohort of 22 sites quarantines anomalous Sites 19 & 24 (capacity metadata errors)
    peer_cohort_22 = [s for s in cohort_24 if s not in [19, 24]]
    c1_cohort = site_details[(site_details['CampusKey'] == 1) & (site_details['SiteKey'].isin(cohort_24))].copy()
    print(f"Loaded {len(c1_cohort)} cohort installations (24 total, 22 peer).")
    
    # Load generation with historical warm-up buffer (from March 1, 2021)
    gen = pd.read_csv("data/raw/unisolar/Solar_Energy_Generation.csv")
    gen['Timestamp'] = pd.to_datetime(gen['Timestamp'])
    
    # Filter for Campus 1 cohort sites within the buffer window (March 1, 2021 - April 30, 2022)
    mask_buffer = (gen['CampusKey'] == 1) & (gen['SiteKey'].isin(cohort_24)) & \
                  (gen['Timestamp'] >= '2021-03-01') & (gen['Timestamp'] < '2022-05-01')
    g_buf = gen[mask_buffer].copy()
    g_buf['Date'] = g_buf['Timestamp'].dt.normalize()
    g_buf['Time_str'] = g_buf['Timestamp'].dt.strftime('%H:%M')
    
    # Define core daytime window: 09:00 to 15:45 (28 15-minute intervals)
    # Peak solar insolation occurs during these hours; missingness here indicates genuine data loss.
    core_times = [f'{h:02d}:{m:02d}' for h in range(9, 16) for m in [0, 15, 30, 45]]
    g_buf['is_core'] = g_buf['Time_str'].isin(core_times)
    
    # Aggregate intervals, core non-null counts, and daily energy per (SiteKey, Date)
    g_core = g_buf[g_buf['is_core']]
    core_counts = g_core.groupby(['SiteKey', 'Date'])['SolarGeneration'].count().rename('core_nonnull_interval_count')
    total_counts = g_buf.groupby(['SiteKey', 'Date'])['SolarGeneration'].size().rename('total_intervals')
    daily_nonnull_counts = g_buf.groupby(['SiteKey', 'Date'])['SolarGeneration'].count().rename('daily_nonnull_interval_count')
    daily_energy = g_buf.groupby(['SiteKey', 'Date'])['SolarGeneration'].sum().rename('daily_energy_kwh')
    
    # Combine aggregated site-day metrics
    sd_all = pd.concat([total_counts, daily_nonnull_counts, core_counts, daily_energy], axis=1).reset_index()
    sd_all['core_nonnull_interval_count'] = sd_all['core_nonnull_interval_count'].fillna(0).astype(int)
    sd_all['daily_nonnull_interval_count'] = sd_all['daily_nonnull_interval_count'].fillna(0).astype(int)
    sd_all['total_intervals'] = sd_all['total_intervals'].fillna(0).astype(int)
    
    # Merge static physical metadata (kWp, coordinates, hardware)
    sd_all = sd_all.merge(c1_cohort[['SiteKey', 'kWp', 'lat', 'Lon', 'Number of panels', 'Panel', 'Inverter']], on='SiteKey', how='left')
    
    # Valid site-day rule:
    # 1. Exactly 96 intervals expected across 24h.
    # 2. At least 26 of 28 core midday intervals observed.
    # 3. Documented capacity must be positive.
    sd_all['is_valid_site_day'] = (sd_all['total_intervals'] == 96) & (sd_all['core_nonnull_interval_count'] >= 26) & (sd_all['kWp'] > 0)
    
    # Compute primary target: Specific Yield Yf (kWh/kWp/day)
    sd_all['target_daily_yield'] = sd_all['daily_energy_kwh'] / sd_all['kWp']
    sd_all['capacity_factor_24h'] = sd_all['target_daily_yield'] / 24.0
    
    # Construct complete annual calendar grid (24 sites x 365 days = 8,760 expected site-days)
    # Using an explicit grid guarantees that missing days are identified and not silently dropped.
    window_dates = pd.date_range('2021-05-01', '2022-04-30', freq='D')
    expected_grid = pd.MultiIndex.from_product([cohort_24, window_dates], names=['SiteKey', 'Date']).to_frame().reset_index(drop=True)
    
    sd_window = expected_grid.merge(sd_all, on=['SiteKey', 'Date'], how='left')
    for col in ['kWp', 'lat', 'Lon', 'Number of panels', 'Panel', 'Inverter']:
        if col in sd_window.columns:
            sd_window[col] = sd_window.groupby('SiteKey')[col].transform(lambda s: s.ffill().bfill())
            
    sd_window['total_intervals'] = sd_window['total_intervals'].fillna(0).astype(int)
    sd_window['daily_nonnull_interval_count'] = sd_window['daily_nonnull_interval_count'].fillna(0).astype(int)
    sd_window['core_nonnull_interval_count'] = sd_window['core_nonnull_interval_count'].fillna(0).astype(int)
    sd_window['is_valid_site_day'] = sd_window['is_valid_site_day'].fillna(False).astype(bool)
    
    # Compute data quality completeness ratios
    sd_window['noncore_nonnull_interval_count'] = sd_window['daily_nonnull_interval_count'] - sd_window['core_nonnull_interval_count']
    sd_window['missing_interval_count'] = 96 - sd_window['daily_nonnull_interval_count']
    sd_window['daily_interval_coverage'] = sd_window['daily_nonnull_interval_count'] / 96.0
    
    # Document explicit exclusion reason for each site-day
    def assign_exclusion_reason(r):
        if r['is_valid_site_day']:
            return 'valid'
        if r['total_intervals'] == 0:
            return 'entirely_absent_date (0/96 intervals)'
        reasons = []
        if r['total_intervals'] < 96:
            reasons.append(f'incomplete_intervals ({r["total_intervals"]}/96)')
        if r['core_nonnull_interval_count'] < 26:
            reasons.append(f'low_core_coverage ({r["core_nonnull_interval_count"]}/28)')
        if pd.isna(r['kWp']) or r['kWp'] <= 0:
            reasons.append('missing_capacity')
        return '; '.join(reasons)
        
    sd_window['exclusion_reason'] = sd_window.apply(assign_exclusion_reason, axis=1)
    
    # Export full target dataset (8,760 rows) and audit log of excluded site-days (1,721 rows)
    target_dataset_path = os.path.join(out_unisolar, "target_dataset.csv")
    sd_window.to_csv(target_dataset_path, index=False)
    print(f"Saved {target_dataset_path} ({len(sd_window)} site-days total).")
    
    excluded_df = sd_window[~sd_window['is_valid_site_day']].copy()
    excluded_path = os.path.join(out_unisolar, "excluded_site_days.csv")
    excluded_df.to_csv(excluded_path, index=False)
    print(f"Saved {excluded_path} ({len(excluded_df)} excluded site-days).")
    print(f"Valid site-days in window: {sd_window['is_valid_site_day'].sum()} ({sd_window['is_valid_site_day'].mean()*100:.2f}%)")
    
    # =========================================================================
    # PART 2: WEATHER PREPARATION (HISTORICAL 1-DAY LAG, TAU >= 24H)
    # =========================================================================
    # In Part 2, we:
    # 1. Aggregate regional weather (AirTemperature, RelativeHumidity) to daily metrics:
    #    - Mean, Max, Min temperature, and diurnal range (max - min).
    #    - Mean relative humidity.
    # 2. Shift weather by 1 full calendar day (shift(1)) so that day D uses day D-1
    #    observations strictly, enforcing tau >= 24h forecasting horizon.
    # 3. Impute any missing weather values using medians computed ONLY from the
    #    training split (Date <= 2021-12-31) to prevent lookahead data leakage.
    # =========================================================================
    print("\n--- Part 2: Processing Weather Data with 1-Day Lag ---")
    weather = pd.read_csv("data/raw/unisolar/Weather_Data_reordered_all.csv")
    weather['Timestamp'] = pd.to_datetime(weather['Timestamp'])
    w_c1 = weather[(weather['CampusKey'] == 1) & (weather['Timestamp'] >= '2021-03-01') & (weather['Timestamp'] < '2022-05-01')].copy()
    w_c1['Date'] = w_c1['Timestamp'].dt.normalize()
    
    dw = w_c1.groupby('Date').agg(
        temp_mean=('AirTemperature', 'mean'),
        temp_max=('AirTemperature', 'max'),
        temp_min=('AirTemperature', 'min'),
        rh_mean=('RelativeHumidity', 'mean')
    ).reset_index()
    dw['temp_range'] = dw['temp_max'] - dw['temp_min']
    
    # Align to continuous calendar grid from 2021-03-01 to 2022-04-30
    all_dates = pd.date_range('2021-03-01', '2022-04-30', freq='D')
    dw = dw.set_index('Date').reindex(all_dates).reset_index().rename(columns={'index': 'Date'})
    
    # Construct historical D-1 lagged weather features (tau >= 24h)
    dw['lag1_temp_mean'] = dw['temp_mean'].shift(1)
    dw['lag1_temp_max'] = dw['temp_max'].shift(1)
    dw['lag1_temp_min'] = dw['temp_min'].shift(1)
    dw['lag1_temp_range'] = dw['temp_range'].shift(1)
    dw['lag1_rh_mean'] = dw['rh_mean'].shift(1)
    
    # Training set imputer values (strictly fit on Date <= 2021-12-31)
    # Never leak validation or test weather statistics into the imputer!
    train_dw = dw[(dw['Date'] >= '2021-05-01') & (dw['Date'] <= '2021-12-31')]
    weather_imp_dict = {
        'lag1_temp_mean': float(train_dw['lag1_temp_mean'].median()),
        'lag1_temp_max': float(train_dw['lag1_temp_max'].median()),
        'lag1_temp_min': float(train_dw['lag1_temp_min'].median()),
        'lag1_temp_range': float(train_dw['lag1_temp_range'].median()),
        'lag1_rh_mean': float(train_dw['lag1_rh_mean'].median())
    }
    for col, val in weather_imp_dict.items():
        dw[col] = dw[col].fillna(val)
        
    weather_feats = dw[['Date', 'lag1_temp_mean', 'lag1_temp_max', 'lag1_temp_min', 'lag1_temp_range', 'lag1_rh_mean']]
    
    # =========================================================================
    # PART 3: FEATURE ENGINEERING ON CONTINUOUS CALENDAR GRID
    # =========================================================================
    # In Part 3, we:
    # 1. Loop through each cohort site and reindex its observations to a continuous
    #    daily grid (all_dates from 2021-03-01 to 2022-04-30).
    # 2. Construct calendar-aware historical generation lags:
    #    - has_valid_lag1: binary flag indicating if day D-1 was an observed valid day.
    #    - lag1_daily_yield, lag2_daily_yield, lag7_daily_yield.
    #    - Rolling yield means and std dev (7-day, 14-day, 30-day).
    # 3. Add continuous calendar features (day of year, month, weekday, weekend flag,
    #    and cyclical sin/cos transformations so end-of-year connects seamlessly).
    # 4. Compute deterministic astronomical solar geometry (H0, declination,
    #    solar noon elevation, zenith, and daylight duration).
    # 5. Assign chronological partitions:
    #    - Train:      2021-05-01 to 2021-12-31 (8 months, Winter + Spring)
    #    - Validation: 2022-01-01 to 2022-02-28 (2 months, Peak Summer)
    #    - Test:       2022-03-01 to 2022-04-23 (2 months, Autumn Transition)
    # =========================================================================
    print("\n--- Part 3: Engineering Calendar-Aware Lag and Astronomical Features ---")
    site_dfs = []
    for sk in cohort_24:
        # Align site telemetry to continuous daily calendar
        sub = sd_all[sd_all['SiteKey'] == sk].copy().set_index('Date').reindex(all_dates).reset_index().rename(columns={'index': 'Date'})
        sub['SiteKey'] = sk
        
        # Merge static metadata (capacity and coordinates)
        site_meta = c1_cohort[c1_cohort['SiteKey'] == sk].iloc[0]
        sub['kWp'] = site_meta['kWp']
        sub['lat'] = site_meta['lat']
        sub['Lon'] = site_meta['Lon']
        
        # Valid yield series: use target_daily_yield if valid, else NaN (NOT zero!)
        # CRITICAL: Missing telemetry days must be NaN so rolling calculations do not treat them as zero production!
        valid_y = sub['target_daily_yield'].where(sub['is_valid_site_day'], np.nan)
        
        # Exact calendar lags (shift(1) on daily grid = strictly calendar day D-1)
        sub['has_valid_lag1'] = sub['is_valid_site_day'].shift(1).fillna(False).astype(int)
        sub['lag1_daily_yield'] = valid_y.shift(1)
        sub['lag2_daily_yield'] = valid_y.shift(2)
        sub['lag7_daily_yield'] = valid_y.shift(7)  # Same weekday of prior week
        
        # Rolling historical features over prior window [D-7, D-1], [D-14, D-1], [D-30, D-1]
        y_hist = valid_y.shift(1)
        sub['rolling_mean_7d_yield'] = y_hist.rolling(window=7, min_periods=1).mean()
        sub['rolling_std_7d_yield'] = y_hist.rolling(window=7, min_periods=1).std().fillna(0.0)
        sub['rolling_mean_14d_yield'] = y_hist.rolling(window=14, min_periods=1).mean()
        sub['rolling_mean_30d_yield'] = y_hist.rolling(window=30, min_periods=1).mean()
        
        site_dfs.append(sub)
        
    full_grid = pd.concat(site_dfs, ignore_index=True)
    
    # Restrict to verified valid site-days in window 2021-05-01 to 2022-04-30
    valid_features = full_grid[
        (full_grid['Date'] >= '2021-05-01') & 
        (full_grid['Date'] <= '2022-04-30') & 
        (full_grid['is_valid_site_day'] == True)
    ].copy()
    
    # Merge lagged weather features
    valid_features = valid_features.merge(weather_feats, on='Date', how='left')
    
    # Calendar Features
    valid_features['day_of_year'] = valid_features['Date'].dt.dayofyear
    valid_features['month'] = valid_features['Date'].dt.month
    valid_features['day_of_week'] = valid_features['Date'].dt.dayofweek
    valid_features['is_weekend'] = (valid_features['day_of_week'] >= 5).astype(int)
    
    # Cyclical sine and cosine transformations for periodic calendar signals
    valid_features['sin_doy'] = np.sin(2 * np.pi * valid_features['day_of_year'] / 365.25)
    valid_features['cos_doy'] = np.cos(2 * np.pi * valid_features['day_of_year'] / 365.25)
    valid_features['sin_month'] = np.sin(2 * np.pi * valid_features['month'] / 12.0)
    valid_features['cos_month'] = np.cos(2 * np.pi * valid_features['month'] / 12.0)
    
    # Astronomical Features computed via NOAA/Spencer celestial mechanics algorithms
    print("Computing deterministic astronomical solar geometry features...")
    astro_records = []
    for _, row in valid_features.iterrows():
        astro = calculate_solar_features(row['lat'], row['Lon'], row['Date'])
        astro_records.append(astro)
    df_astro = pd.DataFrame(astro_records)
    for col in df_astro.columns:
        valid_features[col] = df_astro[col].values
        
    # Chronological Split Assignment (Zero lookahead, strict temporal quarantine)
    def assign_split(d):
        if d <= pd.to_datetime('2021-12-31'):
            return 'train'
        elif d <= pd.to_datetime('2022-02-28'):
            return 'validation'
        else:
            return 'test'
            
    valid_features['split'] = valid_features['Date'].apply(assign_split)
    
    # Diagnostic & Quality Columns (Kept separate from predictive model inputs)
    valid_features['is_site_19'] = (valid_features['SiteKey'] == 19).astype(int)
    valid_features['is_site_24'] = (valid_features['SiteKey'] == 24).astype(int)
    valid_features['is_provisional_site'] = (valid_features['SiteKey'].isin([19, 24])).astype(int)
    valid_features['is_site_16'] = (valid_features['SiteKey'] == 16).astype(int)
    valid_features['is_site_39'] = (valid_features['SiteKey'] == 39).astype(int)
    valid_features['is_low_yield_site'] = (valid_features['SiteKey'].isin([16, 39])).astype(int)
    
    valid_features['daily_nonnull_interval_count'] = valid_features['daily_nonnull_interval_count'].astype(int)
    valid_features['core_nonnull_interval_count'] = valid_features['core_nonnull_interval_count'].astype(int)
    valid_features['noncore_nonnull_interval_count'] = valid_features['daily_nonnull_interval_count'] - valid_features['core_nonnull_interval_count']
    valid_features['missing_interval_count'] = 96 - valid_features['daily_nonnull_interval_count']
    valid_features['daily_interval_coverage'] = valid_features['daily_nonnull_interval_count'] / 96.0
    
    # Define primary predictive continuous/cyclical features (29 features)
    # These are the ONLY 29 features that model estimators are permitted to see.
    primary_predictive_features = [
        # Static Metadata (3)
        'kWp', 'lat', 'Lon',
        # Calendar Cycles (8)
        'day_of_year', 'month', 'day_of_week', 'is_weekend', 'sin_doy', 'cos_doy', 'sin_month', 'cos_month',
        # Deterministic Astronomical Solar Geometry (5)
        'solar_declination_deg', 'solar_noon_elevation_deg', 'solar_noon_zenith_deg', 'daylight_hours', 'extraterrestrial_radiation_h0',
        # Autoregressive Historical Generation Lags & Rolling (8)
        'has_valid_lag1', 'lag1_daily_yield', 'lag2_daily_yield', 'lag7_daily_yield',
        'rolling_mean_7d_yield', 'rolling_std_7d_yield', 'rolling_mean_14d_yield', 'rolling_mean_30d_yield',
        # Historical Weather Lags (5)
        'lag1_temp_mean', 'lag1_temp_max', 'lag1_temp_min', 'lag1_temp_range', 'lag1_rh_mean'
    ]
    
    # Primary Model Feature Matrix columns (33 columns: Identifiers 3 + Target 1 + Predictive 29)
    model_matrix_cols = ['SiteKey', 'Date', 'split', 'target_daily_yield'] + primary_predictive_features
    
    # Diagnostic Metadata columns (17 columns: Identifiers 3 + Target derivatives 2 + Target 1 + Diagnostic flags 6 + Quality indicators 5)
    # Kept in diagnostic_metadata.csv for post-hoc error analysis only!
    diagnostic_cols = [
        'SiteKey', 'Date', 'split', 'target_daily_yield', 'capacity_factor_24h', 'daily_energy_kwh',
        'is_site_19', 'is_site_24', 'is_provisional_site', 'is_site_16', 'is_site_39', 'is_low_yield_site',
        'daily_nonnull_interval_count', 'core_nonnull_interval_count', 'noncore_nonnull_interval_count',
        'daily_interval_coverage', 'missing_interval_count'
    ]
    
    # =========================================================================
    # PART 4: DATASET A — FULL COHORT (24 SITES, n=7,039)
    # =========================================================================
    # In Part 4, we generate the Full Cohort datasets (all 24 sites including 19 and 24).
    # Missing lags are imputed using training-partition medians (Date <= 2021-12-31).
    # =========================================================================
    print("\n--- Part 4: Generating Dataset A (Full Cohort, 24 Sites) ---")
    full_df = valid_features.copy()
    
    # Training-only imputation fitted strictly on training partition of Full Cohort
    full_train_mask = (full_df['split'] == 'train')
    full_imp_dict = weather_imp_dict.copy()
    lag_cols = [
        'lag1_daily_yield', 'lag2_daily_yield', 'lag7_daily_yield',
        'rolling_mean_7d_yield', 'rolling_std_7d_yield',
        'rolling_mean_14d_yield', 'rolling_mean_30d_yield'
    ]
    for col in lag_cols:
        med_val = float(full_df.loc[full_train_mask, col].median())
        full_df[col] = full_df[col].fillna(med_val)
        full_imp_dict[col] = med_val
        
    full_features_df = full_df[model_matrix_cols].copy()
    full_diagnostic_df = full_df[diagnostic_cols].copy()
    
    # Save Full Cohort files
    full_features_path = os.path.join(out_unisolar, "features.csv")
    full_diagnostic_path = os.path.join(out_unisolar, "diagnostic_metadata.csv")
    full_train_path = os.path.join(out_unisolar, "train.csv")
    full_val_path = os.path.join(out_unisolar, "validation.csv")
    full_test_path = os.path.join(out_unisolar, "test.csv")
    
    full_features_df.to_csv(full_features_path, index=False)
    full_diagnostic_df.to_csv(full_diagnostic_path, index=False)
    
    full_train_df = full_features_df[full_features_df['split'] == 'train'].copy()
    full_val_df = full_features_df[full_features_df['split'] == 'validation'].copy()
    full_test_df = full_features_df[full_features_df['split'] == 'test'].copy()
    
    full_train_df.to_csv(full_train_path, index=False)
    full_val_df.to_csv(full_val_path, index=False)
    full_test_df.to_csv(full_test_path, index=False)
    
    print(f"Saved Full Cohort Features: {full_features_path} ({len(full_features_df)} rows, {len(model_matrix_cols)} cols)")
    print(f"Saved Full Cohort Diagnostics: {full_diagnostic_path} ({len(full_diagnostic_df)} rows, {len(diagnostic_cols)} cols)")
    print(f"Saved Full Train: {full_train_path} ({len(full_train_df)} rows)")
    print(f"Saved Full Val:   {full_val_path} ({len(full_val_df)} rows)")
    print(f"Saved Full Test:  {full_test_path} ({len(full_test_df)} rows)")
    
    # =========================================================================
    # PART 5: DATASET B — PEER COHORT (22 SITES, EXCL. 19 & 24, n=6,456)
    # =========================================================================
    # In Part 5, we generate the clean Peer Cohort datasets (excluding Sites 19 and 24).
    # Missing lags are imputed using peer training-partition medians.
    # =========================================================================
    print("\n--- Part 5: Generating Dataset B (Peer Cohort, 22 Sites) ---")
    peer_df = valid_features[~valid_features['SiteKey'].isin([19, 24])].copy()
    
    # Training-only imputation fitted strictly on training partition of Peer Cohort
    peer_train_mask = (peer_df['split'] == 'train')
    peer_imp_dict = weather_imp_dict.copy()
    for col in lag_cols:
        med_val = float(peer_df.loc[peer_train_mask, col].median())
        peer_df[col] = peer_df[col].fillna(med_val)
        peer_imp_dict[col] = med_val
        
    peer_features_df = peer_df[model_matrix_cols].copy()
    peer_diagnostic_df = peer_df[diagnostic_cols].copy()
    
    # Save Peer Cohort files
    peer_features_path = os.path.join(out_peer, "features.csv")
    peer_diagnostic_path = os.path.join(out_peer, "diagnostic_metadata.csv")
    peer_train_path = os.path.join(out_peer, "train.csv")
    peer_val_path = os.path.join(out_peer, "validation.csv")
    peer_test_path = os.path.join(out_peer, "test.csv")
    
    peer_features_df.to_csv(peer_features_path, index=False)
    peer_diagnostic_df.to_csv(peer_diagnostic_path, index=False)
    
    peer_train_df = peer_features_df[peer_features_df['split'] == 'train'].copy()
    peer_val_df = peer_features_df[peer_features_df['split'] == 'validation'].copy()
    peer_test_df = peer_features_df[peer_features_df['split'] == 'test'].copy()
    
    peer_train_df.to_csv(peer_train_path, index=False)
    peer_val_df.to_csv(peer_val_path, index=False)
    peer_test_df.to_csv(peer_test_path, index=False)
    
    print(f"Saved Peer Cohort Features: {peer_features_path} ({len(peer_features_df)} rows, {len(model_matrix_cols)} cols)")
    print(f"Saved Peer Cohort Diagnostics: {peer_diagnostic_path} ({len(peer_diagnostic_df)} rows, {len(diagnostic_cols)} cols)")
    print(f"Saved Peer Train: {peer_train_path} ({len(peer_train_df)} rows)")
    print(f"Saved Peer Val:   {peer_val_path} ({len(peer_val_df)} rows)")
    print(f"Saved Peer Test:  {peer_test_path} ({len(peer_test_df)} rows)")
    
    # =========================================================================
    # PART 6: COMPREHENSIVE FEATURE DICTIONARY (46 ATTRIBUTES)
    # =========================================================================
    # In Part 6, we document all 46 columns across the project:
    # - Identifiers (3): SiteKey, Date, split.
    # - Target & Target Derivatives (3): target_daily_yield, capacity_factor_24h, daily_energy_kwh.
    # - Primary Predictive Inputs (29): static metadata, calendar cycles, astronomical solar geometry,
    #   autoregressive historical yield lags, and historical weather lags.
    # - Diagnostic & Quality Indicators (11): outlier flags, interval counts, coverage ratios.
    # =========================================================================
    print("\n--- Part 6: Generating Comprehensive Feature Dictionary ---")
    dict_records = [
        # Identifiers
        {"Feature": "SiteKey", "Definition": "Installation identifier integer", "Unit": "Categorical ID", "Source": "Solar_Site_Details.csv", "Is_Predictive_Input": "No", "Is_Identifier": "Yes", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Static Metadata", "Leakage_Assessment": "None (Group / Entity Key)"},
        {"Feature": "Date", "Definition": "Observation date (YYYY-MM-DD)", "Unit": "Date", "Source": "Solar_Energy_Generation.csv", "Is_Predictive_Input": "No", "Is_Identifier": "Yes", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Deterministic Index", "Leakage_Assessment": "None (Temporal Index)"},
        {"Feature": "split", "Definition": "Chronological partition label (train/validation/test)", "Unit": "Category", "Source": "Preprocessing Rule", "Is_Predictive_Input": "No", "Is_Identifier": "Yes", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Partitioning Index", "Leakage_Assessment": "None (Evaluation Split)"},
        
        # Target & Target Derivatives
        {"Feature": "target_daily_yield", "Definition": "Daily Specific Yield (Yf = Sum(E_15m) / kWp)", "Unit": "kWh / kWp / day", "Source": "Generation & Site Details", "Is_Predictive_Input": "No", "Is_Identifier": "No", "Is_Target_Derived": "Yes", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Target Ground Truth", "Leakage_Assessment": "Primary prediction target"},
        {"Feature": "capacity_factor_24h", "Definition": "24-hour capacity factor (Yf / 24h)", "Unit": "Fraction (0-1)", "Source": "Derived from Target", "Is_Predictive_Input": "No", "Is_Identifier": "No", "Is_Target_Derived": "Yes", "Is_Diagnostic_Metadata": "Yes", "Prediction_Time_Availability": "Evaluation Metric", "Leakage_Assessment": "Target derivative (separated from features)"},
        {"Feature": "daily_energy_kwh", "Definition": "Integrated daily absolute solar energy", "Unit": "kWh", "Source": "Solar_Energy_Generation.csv", "Is_Predictive_Input": "No", "Is_Identifier": "No", "Is_Target_Derived": "Yes", "Is_Diagnostic_Metadata": "Yes", "Prediction_Time_Availability": "Target Ground Truth", "Leakage_Assessment": "Target component (separated from features)"},
        
        # Primary Predictive Inputs: Static Metadata
        {"Feature": "kWp", "Definition": "Array DC peak nameplate capacity", "Unit": "kWp", "Source": "Solar_Site_Details.csv", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Static Metadata", "Leakage_Assessment": "Documented static hardware specification"},
        {"Feature": "lat", "Definition": "Installation latitude", "Unit": "Degrees South", "Source": "Solar_Site_Details.csv", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Static Metadata", "Leakage_Assessment": "Documented static geographic coordinate"},
        {"Feature": "Lon", "Definition": "Installation longitude", "Unit": "Degrees East", "Source": "Solar_Site_Details.csv", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Static Metadata", "Leakage_Assessment": "Documented static geographic coordinate"},
        
        # Primary Predictive Inputs: Calendar Cycles
        {"Feature": "day_of_year", "Definition": "Ordinal day of the calendar year", "Unit": "1-366", "Source": "Date", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Deterministic Calendar", "Leakage_Assessment": "None (deterministic calendar)"},
        {"Feature": "month", "Definition": "Calendar month integer", "Unit": "1-12", "Source": "Date", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Deterministic Calendar", "Leakage_Assessment": "None (deterministic calendar)"},
        {"Feature": "day_of_week", "Definition": "Day of week integer (0=Mon, 6=Sun)", "Unit": "0-6", "Source": "Date", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Deterministic Calendar", "Leakage_Assessment": "None (deterministic calendar)"},
        {"Feature": "is_weekend", "Definition": "Binary weekend indicator (Sat/Sun)", "Unit": "Binary (0/1)", "Source": "Date", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Deterministic Calendar", "Leakage_Assessment": "None (deterministic calendar)"},
        {"Feature": "sin_doy", "Definition": "Sine of continuous cyclical day of year", "Unit": "[-1, 1]", "Source": "Date", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Deterministic Calendar", "Leakage_Assessment": "None (deterministic continuous cycle)"},
        {"Feature": "cos_doy", "Definition": "Cosine of continuous cyclical day of year", "Unit": "[-1, 1]", "Source": "Date", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Deterministic Calendar", "Leakage_Assessment": "None (deterministic continuous cycle)"},
        {"Feature": "sin_month", "Definition": "Sine of continuous cyclical calendar month", "Unit": "[-1, 1]", "Source": "Date", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Deterministic Calendar", "Leakage_Assessment": "None (deterministic continuous cycle)"},
        {"Feature": "cos_month", "Definition": "Cosine of continuous cyclical calendar month", "Unit": "[-1, 1]", "Source": "Date", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Deterministic Calendar", "Leakage_Assessment": "None (deterministic continuous cycle)"},
        
        # Primary Predictive Inputs: Astronomical Solar Geometry
        {"Feature": "solar_declination_deg", "Definition": "Solar declination angle", "Unit": "Degrees", "Source": "Spencer (1971) Solar Ephemeris", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Deterministic Astronomical", "Leakage_Assessment": "Deterministic Keplerian celestial mechanics"},
        {"Feature": "solar_noon_elevation_deg", "Definition": "Maximum solar elevation angle at solar noon", "Unit": "Degrees", "Source": "NOAA Solar Geometry", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Deterministic Astronomical", "Leakage_Assessment": "Deterministic celestial geometry"},
        {"Feature": "solar_noon_zenith_deg", "Definition": "Minimum solar zenith angle at solar noon", "Unit": "Degrees", "Source": "NOAA Solar Geometry", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Deterministic Astronomical", "Leakage_Assessment": "Deterministic celestial geometry"},
        {"Feature": "daylight_hours", "Definition": "Theoretical astronomical daylight duration", "Unit": "Hours", "Source": "NOAA Solar Geometry", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Deterministic Astronomical", "Leakage_Assessment": "Deterministic celestial geometry"},
        {"Feature": "extraterrestrial_radiation_h0", "Definition": "Daily top-of-atmosphere extraterrestrial horizontal solar insolation", "Unit": "kWh / m2 / day", "Source": "NOAA Solar Geometry", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Deterministic Astronomical", "Leakage_Assessment": "Deterministic celestial radiation bound"},
        
        # Primary Predictive Inputs: Autoregressive Historical Generation
        {"Feature": "has_valid_lag1", "Definition": "Indicator if calendar day D-1 was a verified valid site-day", "Unit": "Binary (0/1)", "Source": "Historical Generation", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Historical (tau >= 24h)", "Leakage_Assessment": "Shifted by 1 calendar day; zero lookahead"},
        {"Feature": "lag1_daily_yield", "Definition": "Specific yield on calendar day D-1", "Unit": "kWh / kWp / day", "Source": "Historical Generation", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Historical (tau >= 24h)", "Leakage_Assessment": "Strict 1-day lag on continuous grid; training-imputed if missing"},
        {"Feature": "lag2_daily_yield", "Definition": "Specific yield on calendar day D-2", "Unit": "kWh / kWp / day", "Source": "Historical Generation", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Historical (tau >= 48h)", "Leakage_Assessment": "Strict 2-day lag on continuous grid; training-imputed if missing"},
        {"Feature": "lag7_daily_yield", "Definition": "Specific yield on calendar day D-7 (same weekday previous week)", "Unit": "kWh / kWp / day", "Source": "Historical Generation", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Historical (tau >= 168h)", "Leakage_Assessment": "Strict 7-day lag on continuous grid; training-imputed if missing"},
        {"Feature": "rolling_mean_7d_yield", "Definition": "Mean specific yield over trailing 7 calendar days [D-7, D-1]", "Unit": "kWh / kWp / day", "Source": "Historical Generation", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Historical (tau >= 24h)", "Leakage_Assessment": "Precedes Day D; averages valid days in trailing 7 calendar days"},
        {"Feature": "rolling_std_7d_yield", "Definition": "Std deviation of specific yield over trailing 7 calendar days [D-7, D-1]", "Unit": "kWh / kWp / day", "Source": "Historical Generation", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Historical (tau >= 24h)", "Leakage_Assessment": "Precedes Day D; zero lookahead"},
        {"Feature": "rolling_mean_14d_yield", "Definition": "Mean specific yield over trailing 14 calendar days [D-14, D-1]", "Unit": "kWh / kWp / day", "Source": "Historical Generation", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Historical (tau >= 24h)", "Leakage_Assessment": "Precedes Day D; averages valid days in trailing 14 calendar days"},
        {"Feature": "rolling_mean_30d_yield", "Definition": "Mean specific yield over trailing 30 calendar days [D-30, D-1]", "Unit": "kWh / kWp / day", "Source": "Historical Generation", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Historical (tau >= 24h)", "Leakage_Assessment": "Precedes Day D; averages valid days in trailing 30 calendar days"},
        
        # Primary Predictive Inputs: Historical Lagged Weather
        {"Feature": "lag1_temp_mean", "Definition": "Mean air temperature on calendar day D-1", "Unit": "°C", "Source": "Weather_Data_reordered_all.csv", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Historical (tau >= 24h)", "Leakage_Assessment": "Shifted by 1 calendar day; training median imputation"},
        {"Feature": "lag1_temp_max", "Definition": "Maximum air temperature on calendar day D-1", "Unit": "°C", "Source": "Weather_Data_reordered_all.csv", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Historical (tau >= 24h)", "Leakage_Assessment": "Shifted by 1 calendar day; training median imputation"},
        {"Feature": "lag1_temp_min", "Definition": "Minimum air temperature on calendar day D-1", "Unit": "°C", "Source": "Weather_Data_reordered_all.csv", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Historical (tau >= 24h)", "Leakage_Assessment": "Shifted by 1 calendar day; training median imputation"},
        {"Feature": "lag1_temp_range", "Definition": "Diurnal temperature range (max - min) on day D-1", "Unit": "°C", "Source": "Weather_Data_reordered_all.csv", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Historical (tau >= 24h)", "Leakage_Assessment": "Proxy for prior-day clear-sky insolation; tau >= 24h"},
        {"Feature": "lag1_rh_mean", "Definition": "Mean relative humidity on calendar day D-1", "Unit": "%", "Source": "Weather_Data_reordered_all.csv", "Is_Predictive_Input": "Yes", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "No", "Prediction_Time_Availability": "Historical (tau >= 24h)", "Leakage_Assessment": "Shifted by 1 calendar day; training median imputation"},
        
        # Diagnostic & Sensitivity Metadata Flags
        {"Feature": "is_site_19", "Definition": "Binary flag for anomalous Site 19", "Unit": "Binary (0/1)", "Source": "SiteKey", "Is_Predictive_Input": "No", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "Yes", "Prediction_Time_Availability": "Diagnostic Flag", "Leakage_Assessment": "Post-hoc diagnostic mask; strictly separated from predictive inputs"},
        {"Feature": "is_site_24", "Definition": "Binary flag for elevated Site 24", "Unit": "Binary (0/1)", "Source": "SiteKey", "Is_Predictive_Input": "No", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "Yes", "Prediction_Time_Availability": "Diagnostic Flag", "Leakage_Assessment": "Post-hoc diagnostic mask; strictly separated from predictive inputs"},
        {"Feature": "is_provisional_site", "Definition": "Binary indicator for provisional concern sites (19 & 24)", "Unit": "Binary (0/1)", "Source": "SiteKey", "Is_Predictive_Input": "No", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "Yes", "Prediction_Time_Availability": "Diagnostic Flag", "Leakage_Assessment": "Post-hoc diagnostic mask; strictly separated from predictive inputs"},
        {"Feature": "is_site_16", "Definition": "Binary flag for low-yield Site 16", "Unit": "Binary (0/1)", "Source": "SiteKey", "Is_Predictive_Input": "No", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "Yes", "Prediction_Time_Availability": "Diagnostic Flag", "Leakage_Assessment": "Post-hoc diagnostic mask; strictly separated from predictive inputs"},
        {"Feature": "is_site_39", "Definition": "Binary flag for low-yield Site 39", "Unit": "Binary (0/1)", "Source": "SiteKey", "Is_Predictive_Input": "No", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "Yes", "Prediction_Time_Availability": "Diagnostic Flag", "Leakage_Assessment": "Post-hoc diagnostic mask; strictly separated from predictive inputs"},
        {"Feature": "is_low_yield_site", "Definition": "Binary indicator for low-yield installations (16 & 39)", "Unit": "Binary (0/1)", "Source": "SiteKey", "Is_Predictive_Input": "No", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "Yes", "Prediction_Time_Availability": "Diagnostic Flag", "Leakage_Assessment": "Post-hoc diagnostic mask; strictly separated from predictive inputs"},
        
        # Quality Completeness Indicators
        {"Feature": "daily_nonnull_interval_count", "Definition": "Count of non-null 15-minute generation readings across all 96 intervals", "Unit": "Count (0-96)", "Source": "Solar_Energy_Generation.csv", "Is_Predictive_Input": "No", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "Yes", "Prediction_Time_Availability": "Quality Indicator", "Leakage_Assessment": "Same-day telemetry quality metadata; separated from model features"},
        {"Feature": "core_nonnull_interval_count", "Definition": "Count of non-null generation readings during core window (09:00-15:45)", "Unit": "Count (0-28)", "Source": "Solar_Energy_Generation.csv", "Is_Predictive_Input": "No", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "Yes", "Prediction_Time_Availability": "Quality Indicator", "Leakage_Assessment": "Core filter compliance indicator; separated from model features"},
        {"Feature": "noncore_nonnull_interval_count", "Definition": "Count of non-null generation readings outside core window (dawn/dusk shoulder)", "Unit": "Count (0-68)", "Source": "Solar_Energy_Generation.csv", "Is_Predictive_Input": "No", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "Yes", "Prediction_Time_Availability": "Quality Indicator", "Leakage_Assessment": "Seasonal daylight tracking indicator; separated from model features"},
        {"Feature": "daily_interval_coverage", "Definition": "Ratio of non-null generation intervals over expected 24h intervals (count / 96)", "Unit": "Fraction (0-1)", "Source": "Solar_Energy_Generation.csv", "Is_Predictive_Input": "No", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "Yes", "Prediction_Time_Availability": "Quality Indicator", "Leakage_Assessment": "Quality completeness ratio; separated from model features"},
        {"Feature": "missing_interval_count", "Definition": "Count of null/unrecorded intervals across 24h day (96 - nonnull_count)", "Unit": "Count (0-96)", "Source": "Solar_Energy_Generation.csv", "Is_Predictive_Input": "No", "Is_Identifier": "No", "Is_Target_Derived": "No", "Is_Diagnostic_Metadata": "Yes", "Prediction_Time_Availability": "Quality Indicator", "Leakage_Assessment": "Missingness count indicator; separated from model features"}
    ]
    df_dict = pd.DataFrame(dict_records)
    dict_path = os.path.join(out_unisolar, "feature_dictionary.csv")
    df_dict.to_csv(dict_path, index=False)
    print(f"Saved {dict_path} ({len(df_dict)} attribute definitions).")
    
    # =========================================================================
    # PART 7: PREPROCESSING METADATA JSON
    # =========================================================================
    print("\n--- Part 7: Generating Preprocessing Metadata JSONs ---")
    absent_dates = ['2021-07-10', '2021-08-11', '2021-11-27', '2022-04-24', '2022-04-25', '2022-04-26', '2022-04-27', '2022-04-28', '2022-04-29', '2022-04-30']
    
    # Full Cohort Metadata
    full_metadata = {
        "dataset_name": "UNISOLAR Campus 1 Full Cohort (Dataset A)",
        "primary_target": "target_daily_yield",
        "target_unit": "kWh/kWp/day",
        "cohort_sites": cohort_24,
        "cohort_site_count": len(cohort_24),
        "temporal_window": "2021-05-01 to 2022-04-30 (12 months / 1 complete annual cycle)",
        "telemetry_end_date": "2022-04-23",
        "expected_annual_calendar_days": 365,
        "expected_annual_site_days": 365 * len(cohort_24),
        "observed_telemetry_calendar_dates": 355,
        "observed_telemetry_site_days": 355 * len(cohort_24),
        "absent_telemetry_calendar_dates": absent_dates,
        "absent_telemetry_calendar_days_count": len(absent_dates),
        "absent_telemetry_site_days": len(absent_dates) * len(cohort_24),
        "valid_site_day_criteria": {
            "expected_intervals": 96,
            "core_window": "09:00 to 15:45 (28 intervals)",
            "min_core_nonnull_intervals": 26,
            "capacity_requirement": "documented kWp > 0"
        },
        "total_evaluated_site_days": len(sd_window),
        "total_valid_site_days": len(full_features_df),
        "total_excluded_site_days": len(excluded_df),
        "valid_site_day_percentage_of_annual": float(len(full_features_df) / len(sd_window) * 100),
        "valid_site_day_percentage_of_observed": float(len(full_features_df) / (355 * len(cohort_24)) * 100),
        "column_architecture": {
            "model_matrix_columns": len(model_matrix_cols),
            "identifiers": 3,
            "target": 1,
            "primary_predictive_features": len(primary_predictive_features),
            "diagnostic_metadata_columns": len(diagnostic_cols)
        },
        "split_boundaries": {
            "train": {"start": "2021-05-01", "end": "2021-12-31", "months": 8, "count": len(full_train_df)},
            "validation": {"start": "2022-01-01", "end": "2022-02-28", "months": 2, "count": len(full_val_df)},
            "test": {"start": "2022-03-01", "end": "2022-04-23", "months": 2, "count": len(full_test_df)}
        },
        "training_imputation_values": full_imp_dict,
        "provisional_concern_sites": {
            "site_19": {
                "documented_kwp": 34.32,
                "documented_inverter": "1 x SolarEdge SE27.6K",
                "mean_yf": float(full_df[full_df['SiteKey'] == 19]['target_daily_yield'].mean()),
                "median_yf": float(full_df[full_df['SiteKey'] == 19]['target_daily_yield'].median()),
                "max_yf": float(full_df[full_df['SiteKey'] == 19]['target_daily_yield'].max()),
                "max_24h_cf": float(full_df[full_df['SiteKey'] == 19]['target_daily_yield'].max() / 24.0),
                "unresolved_anomaly_note": "Observed 15m generation reaches 42.22 kWh (168.88 kW power = 492% STC rating) and target yield reaches 40.79 kWh/kWp/day. Feeder/building aggregation is an unproven hypothesis; anomaly is preserved without clipping."
            },
            "site_24": {
                "documented_kwp": 40.26,
                "documented_inverter": "1 x SolarEdge SE82.8K",
                "mean_yf": float(full_df[full_df['SiteKey'] == 24]['target_daily_yield'].mean()),
                "median_yf": float(full_df[full_df['SiteKey'] == 24]['target_daily_yield'].median()),
                "max_yf": float(full_df[full_df['SiteKey'] == 24]['target_daily_yield'].max()),
                "max_24h_cf": float(full_df[full_df['SiteKey'] == 24]['target_daily_yield'].max() / 24.0),
                "unresolved_anomaly_note": "Observed target yield averages 6.08 kWh/kWp/day (max 13.57). Inverter rating is 82.8 kW while panels document 40.26 kWp. Preserved without clipping."
            }
        },
        "peer_median_specific_yield": float(full_df[~full_df['SiteKey'].isin([19, 24])]['target_daily_yield'].median()),
        "peer_mean_specific_yield": float(full_df[~full_df['SiteKey'].isin([19, 24])]['target_daily_yield'].mean())
    }
    meta_path = os.path.join(out_unisolar, "preprocessing_metadata.json")
    with open(meta_path, 'w') as f:
        json.dump(full_metadata, f, indent=2)
    print(f"Saved {meta_path}.")
    
    # Peer Cohort Metadata
    peer_metadata = {
        "dataset_name": "UNISOLAR Campus 1 Peer Cohort (Dataset B - Excluding Sites 19 & 24)",
        "primary_target": "target_daily_yield",
        "target_unit": "kWh/kWp/day",
        "cohort_sites": peer_cohort_22,
        "cohort_site_count": len(peer_cohort_22),
        "excluded_anomalous_sites": [19, 24],
        "temporal_window": "2021-05-01 to 2022-04-30 (12 months / 1 complete annual cycle)",
        "telemetry_end_date": "2022-04-23",
        "expected_annual_calendar_days": 365,
        "expected_annual_site_days": 365 * len(peer_cohort_22),
        "total_valid_site_days": len(peer_features_df),
        "column_architecture": {
            "model_matrix_columns": len(model_matrix_cols),
            "identifiers": 3,
            "target": 1,
            "primary_predictive_features": len(primary_predictive_features),
            "diagnostic_metadata_columns": len(diagnostic_cols)
        },
        "split_boundaries": {
            "train": {"start": "2021-05-01", "end": "2021-12-31", "months": 8, "count": len(peer_train_df)},
            "validation": {"start": "2022-01-01", "end": "2022-02-28", "months": 2, "count": len(peer_val_df)},
            "test": {"start": "2022-03-01", "end": "2022-04-23", "months": 2, "count": len(peer_test_df)}
        },
        "training_imputation_values": peer_imp_dict,
        "target_statistics": {
            "min": float(peer_features_df['target_daily_yield'].min()),
            "median": float(peer_features_df['target_daily_yield'].median()),
            "mean": float(peer_features_df['target_daily_yield'].mean()),
            "max": float(peer_features_df['target_daily_yield'].max()),
            "std": float(peer_features_df['target_daily_yield'].std()),
            "max_24h_cf": float(peer_features_df['target_daily_yield'].max() / 24.0)
        }
    }
    peer_meta_path = os.path.join(out_peer, "preprocessing_metadata.json")
    with open(peer_meta_path, 'w') as f:
        json.dump(peer_metadata, f, indent=2)
    print(f"Saved {peer_meta_path}.")
    
    # =========================================================================
    # PART 8: KAGGLE BENCHMARK PREPARATION (PRESERVED & VERIFIED)
    # =========================================================================
    # In Part 8, we prepare the isolated secondary benchmark:
    # 1. Plants 1 & 2 15-minute generation and on-site pyranometer weather data.
    # 2. Plant 1 timestamp format is day-first (%d-%m-%Y %H:%M); Plant 2 is ISO.
    # 3. Target is instantaneous inverter active power (AC_POWER in kW).
    # 4. Strictly exclude DAILY_YIELD and TOTAL_YIELD (target leakage cumulative counters).
    # 5. Exclude DC_POWER due to unconfirmed 10x sensor scaling in Plant 1.
    # 6. Chronological split:
    #    - Train:      2020-05-15 to 2020-06-07 (24 days)
    #    - Validation: 2020-06-08 to 2020-06-12 (5 days)
    #    - Test:       2020-06-13 to 2020-06-17 (5 days)
    # =========================================================================
    print("\n--- Part 8: Processing Kaggle Benchmark Dataset ---")
    p1_g = pd.read_csv("data/raw/archive/Plant_1_Generation_Data.csv")
    p1_w = pd.read_csv("data/raw/archive/Plant_1_Weather_Sensor_Data.csv")
    p2_g = pd.read_csv("data/raw/archive/Plant_2_Generation_Data.csv")
    p2_w = pd.read_csv("data/raw/archive/Plant_2_Weather_Sensor_Data.csv")
    
    p1_g['DT'] = pd.to_datetime(p1_g['DATE_TIME'], format='%d-%m-%Y %H:%M')
    p1_w['DT'] = pd.to_datetime(p1_w['DATE_TIME'], format='%Y-%m-%d %H:%M:%S')
    p2_g['DT'] = pd.to_datetime(p2_g['DATE_TIME'], format='%Y-%m-%d %H:%M:%S')
    p2_w['DT'] = pd.to_datetime(p2_w['DATE_TIME'], format='%Y-%m-%d %H:%M:%S')
    
    k1 = p1_g.merge(p1_w[['PLANT_ID', 'DT', 'AMBIENT_TEMPERATURE', 'IRRADIATION']], on=['PLANT_ID', 'DT'], how='inner')
    k2 = p2_g.merge(p2_w[['PLANT_ID', 'DT', 'AMBIENT_TEMPERATURE', 'IRRADIATION']], on=['PLANT_ID', 'DT'], how='inner')
    
    for df, name in [(k1, "Plant 1"), (k2, "Plant 2")]:
        counts = df.groupby('DT')['SOURCE_KEY'].count().rename('active_inverter_count')
        df['active_inverter_count'] = df['DT'].map(counts)
        df['inverter_avail_ratio'] = df['active_inverter_count'] / 22.0
        
        df['hour'] = df['DT'].dt.hour
        df['minute'] = df['DT'].dt.minute
        df['time_hours'] = df['hour'] + df['minute'] / 60.0
        df['sin_hour'] = np.sin(2 * np.pi * df['time_hours'] / 24.0)
        df['cos_hour'] = np.cos(2 * np.pi * df['time_hours'] / 24.0)
        df['day_of_year'] = df['DT'].dt.dayofyear
        df['sin_doy'] = np.sin(2 * np.pi * df['day_of_year'] / 365.25)
        df['cos_doy'] = np.cos(2 * np.pi * df['day_of_year'] / 365.25)
        
        def assign_k_split(dt):
            if dt < pd.to_datetime('2020-06-08'):
                return 'train'
            elif dt < pd.to_datetime('2020-06-13'):
                return 'validation'
            else:
                return 'test'
        df['split'] = df['DT'].apply(assign_k_split)
        
    k_cols = [
        'PLANT_ID', 'DT', 'SOURCE_KEY', 'split',
        'AC_POWER',
        'IRRADIATION', 'AMBIENT_TEMPERATURE',
        'hour', 'minute', 'time_hours', 'sin_hour', 'cos_hour', 'day_of_year', 'sin_doy', 'cos_doy',
        'active_inverter_count', 'inverter_avail_ratio'
    ]
    
    k1_prep = k1[k_cols].rename(columns={'DT': 'Timestamp'}).copy()
    k2_prep = k2[k_cols].rename(columns={'DT': 'Timestamp'}).copy()
    
    p1_path = os.path.join(out_kaggle, "plant1_prepared.csv")
    p2_path = os.path.join(out_kaggle, "plant2_prepared.csv")
    k1_prep.to_csv(p1_path, index=False)
    k2_prep.to_csv(p2_path, index=False)
    print(f"Saved {p1_path} ({len(k1_prep)} rows).")
    print(f"Saved {p2_path} ({len(k2_prep)} rows).")
    
    k_combined = pd.concat([k1_prep, k2_prep], ignore_index=True)
    k_train = k_combined[k_combined['split'] == 'train'].copy()
    k_val = k_combined[k_combined['split'] == 'validation'].copy()
    k_test = k_combined[k_combined['split'] == 'test'].copy()
    
    k_train_path = os.path.join(out_kaggle, "train.csv")
    k_val_path = os.path.join(out_kaggle, "validation.csv")
    k_test_path = os.path.join(out_kaggle, "test.csv")
    
    k_train.to_csv(k_train_path, index=False)
    k_val.to_csv(k_val_path, index=False)
    k_test.to_csv(k_test_path, index=False)
    print(f"Saved Kaggle Train: {k_train_path} ({len(k_train)} rows)")
    print(f"Saved Kaggle Val:   {k_val_path} ({len(k_val)} rows)")
    print(f"Saved Kaggle Test:  {k_test_path} ({len(k_test)} rows)")
    
    kaggle_metadata = {
        "dataset_name": "Kaggle Plants 1 & 2 Short-Horizon Benchmark",
        "primary_target": "AC_POWER",
        "target_unit": "kW (Instantaneous Inverter Power)",
        "resolution": "15-minute",
        "plant_1": {"inverters": 22, "rows": len(k1_prep), "unmatched_rows": len(p1_g) - len(k1_prep)},
        "plant_2": {"inverters": 22, "rows": len(k2_prep), "unmatched_rows": len(p2_g) - len(k2_prep), "inverter_dropouts": "27.7% timestamps with <22 inverters"},
        "split_boundaries": {
            "train": {"start": "2020-05-15", "end": "2020-06-07 23:45", "days": 24, "count": len(k_train)},
            "validation": {"start": "2020-06-08", "end": "2020-06-12 23:45", "days": 5, "count": len(k_val)},
            "test": {"start": "2020-06-13", "end": "2020-06-17 23:45", "days": 5, "count": len(k_test)}
        },
        "excluded_features": [
            {"feature": "DAILY_YIELD", "reason": "Target leakage counter"},
            {"feature": "TOTAL_YIELD", "reason": "Target leakage counter"},
            {"feature": "DC_POWER", "reason": "Observed ~10x DC/AC numerical discrepancy in Plant 1 (unresolved scaling anomaly vs documented unit specification); also intermediate electrical state prior to inverter conversion"}
        ]
    }
    k_meta_path = os.path.join(out_kaggle, "preprocessing_metadata.json")
    with open(k_meta_path, 'w') as f:
        json.dump(kaggle_metadata, f, indent=2)
    print(f"Saved {k_meta_path}.")
    
    print("\n=== PHASE 3 PIPELINE COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
