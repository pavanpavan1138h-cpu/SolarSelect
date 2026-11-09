import os
import json
import numpy as np
import pandas as pd

def calculate_solar_features(lat, lon, dt):
    """
    Computes deterministic astronomical solar features for given latitude, longitude, and date.
    Based on established NOAA / Spencer (1971) solar geometry algorithms.
    """
    doy = dt.dayofyear
    gamma = 2 * np.pi / 365.25 * (doy - 1)
    
    # Solar declination angle in radians
    decl = (0.006918 - 0.399912 * np.cos(gamma) + 0.070257 * np.sin(gamma)
            - 0.006758 * np.cos(2 * gamma) + 0.000907 * np.sin(2 * gamma)
            - 0.002697 * np.cos(3 * gamma) + 0.00148 * np.sin(3 * gamma))
    
    lat_rad = np.radians(lat)
    
    # Sunset hour angle (radians)
    cos_omega_s = -np.tan(lat_rad) * np.tan(decl)
    cos_omega_s = np.clip(cos_omega_s, -1.0, 1.0)
    omega_s = np.arccos(cos_omega_s)
    
    # Daylight duration in hours
    daylight_hours = 2.0 * np.degrees(omega_s) / 15.0
    
    # Solar noon zenith and elevation angles (degrees)
    noon_zenith = np.degrees(np.abs(lat_rad - decl))
    noon_elevation = 90.0 - noon_zenith
    
    # Daily extraterrestrial horizontal solar insolation (H0 in kWh/m2/day)
    # Solar constant Gsc = 1.367 kW/m2
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
    print("=== STARTING PHASE 3 DATA PREPARATION PIPELINE ===")
    
    # Ensure directories
    out_unisolar = "data/processed/unisolar"
    out_kaggle = "data/processed/kaggle_benchmark"
    os.makedirs(out_unisolar, exist_ok=True)
    os.makedirs(out_kaggle, exist_ok=True)
    
    # =========================================================================
    # PART 1: UNISOLAR PRIMARY DATASET PREPARATION
    # =========================================================================
    print("\n--- Part 1: Processing UNISOLAR Dataset ---")
    
    # 1. Load Metadata
    site_details = pd.read_csv("data/raw/unisolar/Solar_Site_Details.csv")
    cohort_24 = [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40]
    c1_cohort = site_details[(site_details['CampusKey'] == 1) & (site_details['SiteKey'].isin(cohort_24))].copy()
    print(f"Loaded {len(c1_cohort)} cohort sites with documented kWp ratings.")
    
    # 2. Load Generation with historical warm-up buffer (from March 1, 2021)
    gen = pd.read_csv("data/raw/unisolar/Solar_Energy_Generation.csv")
    gen['Timestamp'] = pd.to_datetime(gen['Timestamp'])
    
    # Filter to cohort sites and buffer window (2021-03-01 to 2022-04-30)
    mask_buffer = (gen['CampusKey'] == 1) & (gen['SiteKey'].isin(cohort_24)) & \
                  (gen['Timestamp'] >= '2021-03-01') & (gen['Timestamp'] < '2022-05-01')
    g_buf = gen[mask_buffer].copy()
    g_buf['Date'] = g_buf['Timestamp'].dt.normalize()
    g_buf['Time_str'] = g_buf['Timestamp'].dt.strftime('%H:%M')
    
    core_times = [f'{h:02d}:{m:02d}' for h in range(9, 16) for m in [0, 15, 30, 45]]
    g_buf['is_core'] = g_buf['Time_str'].isin(core_times)
    
    # Aggregate daily intervals and core counts
    g_core = g_buf[g_buf['is_core']]
    core_counts = g_core.groupby(['SiteKey', 'Date'])['SolarGeneration'].count().rename('core_valid')
    total_counts = g_buf.groupby(['SiteKey', 'Date'])['SolarGeneration'].size().rename('total_intervals')
    total_valid = g_buf.groupby(['SiteKey', 'Date'])['SolarGeneration'].count().rename('total_valid_intervals')
    daily_energy = g_buf.groupby(['SiteKey', 'Date'])['SolarGeneration'].sum().rename('daily_energy_kwh')
    
    sd_all = pd.concat([total_counts, core_counts, total_valid, daily_energy], axis=1).reset_index()
    sd_all['core_valid'] = sd_all['core_valid'].fillna(0).astype(int)
    sd_all['total_valid_intervals'] = sd_all['total_valid_intervals'].fillna(0).astype(int)
    
    # Merge metadata onto sd_all
    sd_all = sd_all.merge(c1_cohort[['SiteKey', 'kWp', 'lat', 'Lon', 'Number of panels', 'Panel', 'Inverter']], on='SiteKey', how='left')
    
    # Valid site-day rule on all observations (including warm-up buffer)
    sd_all['is_valid_site_day'] = (sd_all['total_intervals'] == 96) & (sd_all['core_valid'] >= 26) & (sd_all['kWp'] > 0)
    sd_all['target_daily_yield'] = sd_all['daily_energy_kwh'] / sd_all['kWp']
    sd_all['capacity_factor_24h'] = sd_all['target_daily_yield'] / 24.0
    
    # Construct complete annual calendar grid for the 24 cohort sites (365 calendar days = 8,760 site-days)
    window_dates = pd.date_range('2021-05-01', '2022-04-30', freq='D')
    expected_grid = pd.MultiIndex.from_product([cohort_24, window_dates], names=['SiteKey', 'Date']).to_frame().reset_index(drop=True)
    
    # Merge observed site-days into complete grid
    sd_window = expected_grid.merge(sd_all, on=['SiteKey', 'Date'], how='left')
    
    # Fill static metadata for unobserved site-days from c1_cohort
    for col in ['kWp', 'lat', 'Lon', 'Number of panels', 'Panel', 'Inverter']:
        if col in sd_window.columns:
            sd_window[col] = sd_window.groupby('SiteKey')[col].transform(lambda s: s.ffill().bfill())
            
    # Fill unobserved site-days (e.g. absent calendar dates)
    sd_window['total_intervals'] = sd_window['total_intervals'].fillna(0).astype(int)
    sd_window['core_valid'] = sd_window['core_valid'].fillna(0).astype(int)
    sd_window['total_valid_intervals'] = sd_window['total_valid_intervals'].fillna(0).astype(int)
    sd_window['is_valid_site_day'] = sd_window['is_valid_site_day'].fillna(False).astype(bool)
    
    # Document exclusion reasons
    def assign_exclusion_reason(r):
        if r['is_valid_site_day']:
            return 'valid'
        if r['total_intervals'] == 0:
            return 'entirely_absent_date (0/96 intervals)'
        reasons = []
        if r['total_intervals'] < 96:
            reasons.append(f'incomplete_intervals ({r["total_intervals"]}/96)')
        if r['core_valid'] < 26:
            reasons.append(f'low_core_coverage ({r["core_valid"]}/28)')
        if pd.isna(r['kWp']) or r['kWp'] <= 0:
            reasons.append('missing_capacity')
        return '; '.join(reasons)
        
    sd_window['exclusion_reason'] = sd_window.apply(assign_exclusion_reason, axis=1)
    
    # Target dataset file (all 8,760 evaluated site-days in window)
    target_dataset_path = os.path.join(out_unisolar, "target_dataset.csv")
    sd_window.to_csv(target_dataset_path, index=False)
    print(f"Saved {target_dataset_path} ({len(sd_window)} site-days total).")
    
    # Excluded site-days file (1,721 total: 1,481 observed invalid + 240 completely absent)
    excluded_df = sd_window[~sd_window['is_valid_site_day']].copy()
    excluded_path = os.path.join(out_unisolar, "excluded_site_days.csv")
    excluded_df.to_csv(excluded_path, index=False)
    print(f"Saved {excluded_path} ({len(excluded_df)} excluded site-days).")
    print(f"Valid site-days in window: {sd_window['is_valid_site_day'].sum()} ({sd_window['is_valid_site_day'].mean()*100:.2f}%)")
    
    # 3. Weather Preparation with Historical Lag
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
    
    # Reindex over full continuous date range
    all_dates = pd.date_range('2021-03-01', '2022-04-30', freq='D')
    dw = dw.set_index('Date').reindex(all_dates).reset_index().rename(columns={'index': 'Date'})
    
    # Construct historical D-1 lagged weather features (tau >= 1 day)
    dw['lag1_temp_mean'] = dw['temp_mean'].shift(1)
    dw['lag1_temp_max'] = dw['temp_max'].shift(1)
    dw['lag1_temp_min'] = dw['temp_min'].shift(1)
    dw['lag1_temp_range'] = dw['temp_range'].shift(1)
    dw['lag1_rh_mean'] = dw['rh_mean'].shift(1)
    
    # Training set imputer values (strictly fit on Date <= 2021-12-31)
    train_dw = dw[(dw['Date'] >= '2021-05-01') & (dw['Date'] <= '2021-12-31')]
    imp_dict = {
        'lag1_temp_mean': float(train_dw['lag1_temp_mean'].median()),
        'lag1_temp_max': float(train_dw['lag1_temp_max'].median()),
        'lag1_temp_min': float(train_dw['lag1_temp_min'].median()),
        'lag1_temp_range': float(train_dw['lag1_temp_range'].median()),
        'lag1_rh_mean': float(train_dw['lag1_rh_mean'].median())
    }
    for col, val in imp_dict.items():
        dw[col] = dw[col].fillna(val)
        
    weather_feats = dw[['Date', 'lag1_temp_mean', 'lag1_temp_max', 'lag1_temp_min', 'lag1_temp_range', 'lag1_rh_mean']]
    
    # 4. Feature Engineering for Valid Site-Days
    # Build a continuous daily grid for each site to compute exact lags and rolling windows
    site_dfs = []
    for sk in cohort_24:
        sub = sd_all[sd_all['SiteKey'] == sk].copy().set_index('Date').reindex(all_dates).reset_index().rename(columns={'index': 'Date'})
        sub['SiteKey'] = sk
        
        # Merge static metadata
        site_meta = c1_cohort[c1_cohort['SiteKey'] == sk].iloc[0]
        sub['kWp'] = site_meta['kWp']
        sub['lat'] = site_meta['lat']
        sub['Lon'] = site_meta['Lon']
        
        # Valid yield series: use target_daily_yield if valid, else NaN
        valid_y = sub['target_daily_yield'].where(sub['is_valid_site_day'], np.nan)
        
        # Lag 1: value of D-1 if valid, else forward-fill from recent valid (up to 7 days)
        sub['has_valid_lag1'] = sub['is_valid_site_day'].shift(1).fillna(False).astype(int)
        sub['lag1_daily_yield'] = valid_y.shift(1).ffill(limit=7)
        sub['lag2_daily_yield'] = valid_y.shift(2).ffill(limit=7)
        sub['lag7_daily_yield'] = valid_y.shift(7).ffill(limit=7)
        
        # Rolling historical features over prior window [D-7, D-1], [D-14, D-1], [D-30, D-1]
        # Shift by 1 first so day D never enters its own rolling window
        y_hist = valid_y.shift(1)
        sub['rolling_mean_7d_yield'] = y_hist.rolling(window=7, min_periods=1).mean()
        sub['rolling_std_7d_yield'] = y_hist.rolling(window=7, min_periods=1).std().fillna(0.0)
        sub['rolling_mean_14d_yield'] = y_hist.rolling(window=14, min_periods=1).mean()
        sub['rolling_mean_30d_yield'] = y_hist.rolling(window=30, min_periods=1).mean()
        
        site_dfs.append(sub)
        
    full_grid = pd.concat(site_dfs, ignore_index=True)
    
    # Restrict to verified valid site-days in the approved window 2021-05-01 to 2022-04-30
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
    
    valid_features['sin_doy'] = np.sin(2 * np.pi * valid_features['day_of_year'] / 365.25)
    valid_features['cos_doy'] = np.cos(2 * np.pi * valid_features['day_of_year'] / 365.25)
    valid_features['sin_month'] = np.sin(2 * np.pi * valid_features['month'] / 12.0)
    valid_features['cos_month'] = np.cos(2 * np.pi * valid_features['month'] / 12.0)
    
    # Astronomical Features
    print("Computing deterministic astronomical solar geometry features...")
    astro_records = []
    for _, row in valid_features.iterrows():
        astro = calculate_solar_features(row['lat'], row['Lon'], row['Date'])
        astro_records.append(astro)
    df_astro = pd.DataFrame(astro_records)
    for col in df_astro.columns:
        valid_features[col] = df_astro[col].values
        
    # Site Concern Flags
    valid_features['is_site_19'] = (valid_features['SiteKey'] == 19).astype(int)
    valid_features['is_site_24'] = (valid_features['SiteKey'] == 24).astype(int)
    valid_features['is_provisional_site'] = (valid_features['SiteKey'].isin([19, 24])).astype(int)
    valid_features['is_site_16'] = (valid_features['SiteKey'] == 16).astype(int)
    valid_features['is_site_39'] = (valid_features['SiteKey'] == 39).astype(int)
    valid_features['is_low_yield_site'] = (valid_features['SiteKey'].isin([16, 39])).astype(int)
    
    # Chronological Split
    def assign_split(d):
        if d <= pd.to_datetime('2021-12-31'):
            return 'train'
        elif d <= pd.to_datetime('2022-02-28'):
            return 'validation'
        else:
            return 'test'
            
    valid_features['split'] = valid_features['Date'].apply(assign_split)
    
    # Training-only imputation for lag/rolling features (strictly fitted on training split)
    train_mask = (valid_features['split'] == 'train')
    lag_cols = [
        'lag1_daily_yield', 'lag2_daily_yield', 'lag7_daily_yield',
        'rolling_mean_7d_yield', 'rolling_std_7d_yield',
        'rolling_mean_14d_yield', 'rolling_mean_30d_yield'
    ]
    for col in lag_cols:
        med_val = float(valid_features.loc[train_mask, col].median())
        valid_features[col] = valid_features[col].fillna(med_val)
        imp_dict[col] = med_val
    
    # Organize columns cleanly
    selected_cols = [
        # Identifiers & Target
        'SiteKey', 'Date', 'split', 'target_daily_yield', 'capacity_factor_24h', 'daily_energy_kwh',
        # Static Metadata
        'kWp', 'lat', 'Lon',
        # Calendar Features
        'day_of_year', 'month', 'day_of_week', 'is_weekend', 'sin_doy', 'cos_doy', 'sin_month', 'cos_month',
        # Astronomical Solar Features
        'solar_declination_deg', 'solar_noon_elevation_deg', 'solar_noon_zenith_deg', 'daylight_hours', 'extraterrestrial_radiation_h0',
        # Historical Lagged Generation (tau >= 1 day)
        'has_valid_lag1', 'lag1_daily_yield', 'lag2_daily_yield', 'lag7_daily_yield',
        'rolling_mean_7d_yield', 'rolling_std_7d_yield', 'rolling_mean_14d_yield', 'rolling_mean_30d_yield',
        # Historical Lagged Weather (tau >= 1 day)
        'lag1_temp_mean', 'lag1_temp_max', 'lag1_temp_min', 'lag1_temp_range', 'lag1_rh_mean',
        # Site Anomaly / Sensitivity Flags
        'is_site_19', 'is_site_24', 'is_provisional_site', 'is_site_16', 'is_site_39', 'is_low_yield_site'
    ]
    
    features_df = valid_features[selected_cols].copy()
    
    # Save full features dataset
    features_path = os.path.join(out_unisolar, "features.csv")
    features_df.to_csv(features_path, index=False)
    print(f"Saved {features_path} ({len(features_df)} rows, {len(selected_cols)} cols).")
    
    # Save splits
    train_df = features_df[features_df['split'] == 'train'].copy()
    val_df = features_df[features_df['split'] == 'validation'].copy()
    test_df = features_df[features_df['split'] == 'test'].copy()
    
    train_path = os.path.join(out_unisolar, "train.csv")
    val_path = os.path.join(out_unisolar, "validation.csv")
    test_path = os.path.join(out_unisolar, "test.csv")
    
    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)
    print(f"Saved Train: {train_path} ({len(train_df)} rows)")
    print(f"Saved Val:   {val_path} ({len(val_df)} rows)")
    print(f"Saved Test:  {test_path} ({len(test_df)} rows)")
    
    # Feature Dictionary
    dict_records = [
        {"Feature": "SiteKey", "Definition": "Installation identifier integer", "Source": "Solar_Site_Details.csv", "Unit": "Categorical ID", "Prediction Availability": "Static Metadata", "Transformation": "None (Group Key)", "Missingness Handling": "None (0% null)", "Leakage Assessment": "None (Identifier)"},
        {"Feature": "Date", "Definition": "Observation date (YYYY-MM-DD)", "Source": "Solar_Energy_Generation.csv", "Unit": "Date", "Prediction Availability": "Deterministic Index", "Transformation": "Normalized to Midnight", "Missingness Handling": "None (Contiguous)", "Leakage Assessment": "None (Index)"},
        {"Feature": "split", "Definition": "Chronological partition partition label", "Source": "Preprocessing", "Unit": "Category", "Prediction Availability": "Partition", "Transformation": "Date-based thresholding", "Missingness Handling": "None", "Leakage Assessment": "None"},
        {"Feature": "target_daily_yield", "Definition": "Daily Specific Yield (Yf = Sum(E_15m) / kWp)", "Source": "Generation & Details", "Unit": "kWh / kWp / day", "Prediction Availability": "Target Variable", "Transformation": "Daily sum of valid daytime intervals divided by kWp", "Missingness Handling": "Filtered via valid site-day filter (>= 26/28 core)", "Leakage Assessment": "Target ground truth"},
        {"Feature": "capacity_factor_24h", "Definition": "24-hour capacity factor (Yf / 24h)", "Source": "Derived from Target", "Unit": "Fraction (0-1)", "Prediction Availability": "Evaluation Metric", "Transformation": "Linear scaling of Yf", "Missingness Handling": "None", "Leakage Assessment": "Target derivative"},
        {"Feature": "daily_energy_kwh", "Definition": "Daily integrated absolute solar energy", "Source": "Solar_Energy_Generation.csv", "Unit": "kWh", "Prediction Availability": "Target Component", "Transformation": "Sum of 15m intervals", "Missingness Handling": "Valid-day filtering", "Leakage Assessment": "Target component"},
        {"Feature": "kWp", "Definition": "Array DC peak nameplate capacity", "Source": "Solar_Site_Details.csv", "Unit": "kWp", "Prediction Availability": "Static Metadata", "Transformation": "None (Normalizer)", "Missingness Handling": "Documented for all 24 cohort sites", "Leakage Assessment": "Static metadata"},
        {"Feature": "lat", "Definition": "Installation latitude", "Source": "Solar_Site_Details.csv", "Unit": "Degrees South", "Prediction Availability": "Static Metadata", "Transformation": "None", "Missingness Handling": "Complete", "Leakage Assessment": "Static metadata"},
        {"Feature": "Lon", "Definition": "Installation longitude", "Source": "Solar_Site_Details.csv", "Unit": "Degrees East", "Prediction Availability": "Static Metadata", "Transformation": "None", "Missingness Handling": "Complete", "Leakage Assessment": "Static metadata"},
        {"Feature": "day_of_year", "Definition": "Ordinal day of the calendar year", "Source": "Date", "Unit": "1-366", "Prediction Availability": "Deterministic Calendar", "Transformation": "dt.dayofyear", "Missingness Handling": "None", "Leakage Assessment": "None"},
        {"Feature": "month", "Definition": "Calendar month integer", "Source": "Date", "Unit": "1-12", "Prediction Availability": "Deterministic Calendar", "Transformation": "dt.month", "Missingness Handling": "None", "Leakage Assessment": "None"},
        {"Feature": "day_of_week", "Definition": "Day of the week integer (0=Mon, 6=Sun)", "Source": "Date", "Unit": "0-6", "Prediction Availability": "Deterministic Calendar", "Transformation": "dt.dayofweek", "Missingness Handling": "None", "Leakage Assessment": "None"},
        {"Feature": "is_weekend", "Definition": "Binary weekend indicator", "Source": "Date", "Unit": "Binary (0/1)", "Prediction Availability": "Deterministic Calendar", "Transformation": "day_of_week >= 5", "Missingness Handling": "None", "Leakage Assessment": "None"},
        {"Feature": "sin_doy", "Definition": "Sine of continuous cyclical day of year", "Source": "Date", "Unit": "[-1, 1]", "Prediction Availability": "Deterministic Calendar", "Transformation": "sin(2*pi*doy / 365.25)", "Missingness Handling": "None", "Leakage Assessment": "None"},
        {"Feature": "cos_doy", "Definition": "Cosine of continuous cyclical day of year", "Source": "Date", "Unit": "[-1, 1]", "Prediction Availability": "Deterministic Calendar", "Transformation": "cos(2*pi*doy / 365.25)", "Missingness Handling": "None", "Leakage Assessment": "None"},
        {"Feature": "sin_month", "Definition": "Sine of continuous cyclical calendar month", "Source": "Date", "Unit": "[-1, 1]", "Prediction Availability": "Deterministic Calendar", "Transformation": "sin(2*pi*month / 12)", "Missingness Handling": "None", "Leakage Assessment": "None"},
        {"Feature": "cos_month", "Definition": "Cosine of continuous cyclical calendar month", "Source": "Date", "Unit": "[-1, 1]", "Prediction Availability": "Deterministic Calendar", "Transformation": "cos(2*pi*month / 12)", "Missingness Handling": "None", "Leakage Assessment": "None"},
        {"Feature": "solar_declination_deg", "Definition": "Solar declination angle", "Source": "Astronomical Ephemeris", "Unit": "Degrees", "Prediction Availability": "Deterministic Astronomical", "Transformation": "Spencer (1971) solar geometry formula", "Missingness Handling": "None", "Leakage Assessment": "None"},
        {"Feature": "solar_noon_elevation_deg", "Definition": "Maximum solar elevation angle at solar noon", "Source": "Astronomical Ephemeris", "Unit": "Degrees", "Prediction Availability": "Deterministic Astronomical", "Transformation": "90 - |lat - decl|", "Missingness Handling": "None", "Leakage Assessment": "None"},
        {"Feature": "solar_noon_zenith_deg", "Definition": "Minimum solar zenith angle at solar noon", "Source": "Astronomical Ephemeris", "Unit": "Degrees", "Prediction Availability": "Deterministic Astronomical", "Transformation": "|lat - decl|", "Missingness Handling": "None", "Leakage Assessment": "None"},
        {"Feature": "daylight_hours", "Definition": "Theoretical astronomical daylight duration", "Source": "Astronomical Ephemeris", "Unit": "Hours", "Prediction Availability": "Deterministic Astronomical", "Transformation": "2 * arccos(-tan(lat)*tan(decl)) / 15 deg", "Missingness Handling": "None", "Leakage Assessment": "None"},
        {"Feature": "extraterrestrial_radiation_h0", "Definition": "Daily top-of-atmosphere extraterrestrial horizontal solar insolation", "Source": "Astronomical Ephemeris", "Unit": "kWh / m2 / day", "Prediction Availability": "Deterministic Astronomical", "Transformation": "NOAA solar constant integration (Gsc = 1.367 kW/m2)", "Missingness Handling": "None", "Leakage Assessment": "None"},
        {"Feature": "has_valid_lag1", "Definition": "Indicator if day D-1 was a verified valid site-day", "Source": "Historical Generation", "Unit": "Binary (0/1)", "Prediction Availability": "Genuine Historical (tau >= 1d)", "Transformation": "is_valid_site_day.shift(1)", "Missingness Handling": "0 if D-1 invalid", "Leakage Assessment": "Zero lookahead (prior day only)"},
        {"Feature": "lag1_daily_yield", "Definition": "Specific yield from day D-1", "Source": "Historical Generation", "Unit": "kWh / kWp / day", "Prediction Availability": "Genuine Historical (tau >= 1d)", "Transformation": "target_daily_yield.shift(1).ffill(7)", "Missingness Handling": "Forward-filled from last valid within 7d", "Leakage Assessment": "Zero lookahead (prior day only)"},
        {"Feature": "lag2_daily_yield", "Definition": "Specific yield from day D-2", "Source": "Historical Generation", "Unit": "kWh / kWp / day", "Prediction Availability": "Genuine Historical (tau >= 2d)", "Transformation": "target_daily_yield.shift(2).ffill(7)", "Missingness Handling": "Forward-filled from last valid within 7d", "Leakage Assessment": "Zero lookahead (prior days only)"},
        {"Feature": "lag7_daily_yield", "Definition": "Specific yield from day D-7 (same day previous week)", "Source": "Historical Generation", "Unit": "kWh / kWp / day", "Prediction Availability": "Genuine Historical (tau >= 7d)", "Transformation": "target_daily_yield.shift(7).ffill(7)", "Missingness Handling": "Forward-filled from last valid within 7d", "Leakage Assessment": "Zero lookahead (prior days only)"},
        {"Feature": "rolling_mean_7d_yield", "Definition": "Mean specific yield over prior 7 days [D-7, D-1]", "Source": "Historical Generation", "Unit": "kWh / kWp / day", "Prediction Availability": "Genuine Historical (tau >= 1d)", "Transformation": "valid_y.shift(1).rolling(7).mean()", "Missingness Handling": "Computed on valid days in window", "Leakage Assessment": "Zero lookahead"},
        {"Feature": "rolling_std_7d_yield", "Definition": "Std deviation of specific yield over prior 7 days [D-7, D-1]", "Source": "Historical Generation", "Unit": "kWh / kWp / day", "Prediction Availability": "Genuine Historical (tau >= 1d)", "Transformation": "valid_y.shift(1).rolling(7).std().fillna(0)", "Missingness Handling": "0 if single valid day", "Leakage Assessment": "Zero lookahead"},
        {"Feature": "rolling_mean_14d_yield", "Definition": "Mean specific yield over prior 14 days [D-14, D-1]", "Source": "Historical Generation", "Unit": "kWh / kWp / day", "Prediction Availability": "Genuine Historical (tau >= 1d)", "Transformation": "valid_y.shift(1).rolling(14).mean()", "Missingness Handling": "Computed on valid days in window", "Leakage Assessment": "Zero lookahead"},
        {"Feature": "rolling_mean_30d_yield", "Definition": "Mean specific yield over prior 30 days [D-30, D-1]", "Source": "Historical Generation", "Unit": "kWh / kWp / day", "Prediction Availability": "Genuine Historical (tau >= 1d)", "Transformation": "valid_y.shift(1).rolling(30).mean()", "Missingness Handling": "Computed on valid days in window", "Leakage Assessment": "Zero lookahead"},
        {"Feature": "lag1_temp_mean", "Definition": "Mean air temperature on day D-1", "Source": "Weather_Data_reordered_all.csv", "Unit": "°C", "Prediction Availability": "Genuine Historical (tau >= 1d)", "Transformation": "temp_mean.shift(1)", "Missingness Handling": "Training set median imputation", "Leakage Assessment": "Zero lookahead"},
        {"Feature": "lag1_temp_max", "Definition": "Maximum air temperature on day D-1", "Source": "Weather_Data_reordered_all.csv", "Unit": "°C", "Prediction Availability": "Genuine Historical (tau >= 1d)", "Transformation": "temp_max.shift(1)", "Missingness Handling": "Training set median imputation", "Leakage Assessment": "Zero lookahead"},
        {"Feature": "lag1_temp_min", "Definition": "Minimum air temperature on day D-1", "Source": "Weather_Data_reordered_all.csv", "Unit": "°C", "Prediction Availability": "Genuine Historical (tau >= 1d)", "Transformation": "temp_min.shift(1)", "Missingness Handling": "Training set median imputation", "Leakage Assessment": "Zero lookahead"},
        {"Feature": "lag1_temp_range", "Definition": "Diurnal temperature range (max - min) on day D-1", "Source": "Weather_Data_reordered_all.csv", "Unit": "°C", "Prediction Availability": "Genuine Historical (tau >= 1d)", "Transformation": "(temp_max - temp_min).shift(1)", "Missingness Handling": "Training set median imputation", "Leakage Assessment": "Zero lookahead; proxy for clear-sky conditions"},
        {"Feature": "lag1_rh_mean", "Definition": "Mean relative humidity on day D-1", "Source": "Weather_Data_reordered_all.csv", "Unit": "%", "Prediction Availability": "Genuine Historical (tau >= 1d)", "Transformation": "rh_mean.shift(1)", "Missingness Handling": "Training set median imputation", "Leakage Assessment": "Zero lookahead"},
        {"Feature": "is_site_19", "Definition": "Binary flag for anomalous Site 19", "Source": "SiteKey", "Unit": "Binary (0/1)", "Prediction Availability": "Metadata", "Transformation": "SiteKey == 19", "Missingness Handling": "Complete", "Leakage Assessment": "Sensitivity flag for Phase 4"},
        {"Feature": "is_site_24", "Definition": "Binary flag for elevated Site 24", "Source": "SiteKey", "Unit": "Binary (0/1)", "Prediction Availability": "Metadata", "Transformation": "SiteKey == 24", "Missingness Handling": "Complete", "Leakage Assessment": "Sensitivity flag for Phase 4"},
        {"Feature": "is_provisional_site", "Definition": "Binary indicator for provisional concern sites (19 & 24)", "Source": "SiteKey", "Unit": "Binary (0/1)", "Prediction Availability": "Metadata", "Transformation": "SiteKey in [19, 24]", "Missingness Handling": "Complete", "Leakage Assessment": "Sensitivity flag for Phase 4"},
        {"Feature": "is_site_16", "Definition": "Binary flag for low-yield Site 16", "Source": "SiteKey", "Unit": "Binary (0/1)", "Prediction Availability": "Metadata", "Transformation": "SiteKey == 16", "Missingness Handling": "Complete", "Leakage Assessment": "Baseline flag"},
        {"Feature": "is_site_39", "Definition": "Binary flag for low-yield Site 39", "Source": "SiteKey", "Unit": "Binary (0/1)", "Prediction Availability": "Metadata", "Transformation": "SiteKey == 39", "Missingness Handling": "Complete", "Leakage Assessment": "Baseline flag"},
        {"Feature": "is_low_yield_site", "Definition": "Binary indicator for low-yield installations (16 & 39)", "Source": "SiteKey", "Unit": "Binary (0/1)", "Prediction Availability": "Metadata", "Transformation": "SiteKey in [16, 39]", "Missingness Handling": "Complete", "Leakage Assessment": "Baseline flag"}
    ]
    df_dict = pd.DataFrame(dict_records)
    dict_path = os.path.join(out_unisolar, "feature_dictionary.csv")
    df_dict.to_csv(dict_path, index=False)
    print(f"Saved {dict_path} ({len(df_dict)} feature definitions).")
    
    # Metadata JSON
    absent_dates = ['2021-07-10', '2021-08-11', '2021-11-27', '2022-04-24', '2022-04-25', '2022-04-26', '2022-04-27', '2022-04-28', '2022-04-29', '2022-04-30']
    unisolar_metadata = {
        "dataset_name": "UNISOLAR Campus 1 Consistent Cohort",
        "primary_target": "target_daily_yield",
        "target_unit": "kWh/kWp/day",
        "cohort_sites": cohort_24,
        "cohort_site_count": len(cohort_24),
        "temporal_window": "2021-05-01 to 2022-04-30 (12 months / 1 complete annual cycle)",
        "expected_annual_calendar_days": 365,
        "expected_annual_site_days": 365 * len(cohort_24),  # 8,760
        "observed_telemetry_calendar_dates": 355,
        "observed_telemetry_site_days": 355 * len(cohort_24),  # 8,520
        "absent_telemetry_calendar_dates": absent_dates,
        "absent_telemetry_calendar_days_count": len(absent_dates),  # 10
        "absent_telemetry_site_days": len(absent_dates) * len(cohort_24),  # 240
        "valid_site_day_criteria": {
            "expected_intervals": 96,
            "core_window": "09:00 to 15:45 (28 intervals)",
            "min_core_valid_intervals": 26,
            "capacity_requirement": "documented kWp > 0"
        },
        "total_evaluated_site_days": len(sd_window),  # 8,760
        "total_valid_site_days": len(features_df),   # 7,039
        "total_excluded_site_days": len(excluded_df), # 1,721 (1,481 observed invalid + 240 completely absent)
        "valid_site_day_percentage_of_annual": float(len(features_df) / len(sd_window) * 100),  # 80.35%
        "valid_site_day_percentage_of_observed": float(len(features_df) / (355 * len(cohort_24)) * 100),  # 82.62%
        "column_accounting": {
            "total_columns": len(selected_cols),  # 41
            "identifiers_and_splits": 3,  # SiteKey, Date, split
            "target_and_derivatives": 3,  # target_daily_yield, capacity_factor_24h, daily_energy_kwh
            "primary_predictive_features": 29,  # 3 metadata + 8 calendar + 5 astro + 8 lag gen + 5 lag weather
            "site_diagnostic_flags": 6,  # is_site_19, is_site_24, is_provisional_site, is_site_16, is_site_39, is_low_yield_site
            "total_model_input_features": 35
        },
        "split_boundaries": {
            "train": {"start": "2021-05-01", "end": "2021-12-31", "months": 8, "count": len(train_df)},
            "validation": {"start": "2022-01-01", "end": "2022-02-28", "months": 2, "count": len(val_df)},
            "test": {"start": "2022-03-01", "end": "2022-04-30", "months": 2, "count": len(test_df)}
        },
        "training_imputation_values": imp_dict,
        "feature_count": len(selected_cols),
        "provisional_concern_sites": {
            "site_19": {"corrected_mean_yf": 18.21, "capacity_factor_24h": 0.7587, "hypothesis": "feeder/building aggregation"},
            "site_24": {"corrected_mean_yf": 6.08, "capacity_factor_24h": 0.2534, "hypothesis": "underreported DC capacity"}
        },
        "peer_median_specific_yield": 2.94
    }
    meta_path = os.path.join(out_unisolar, "preprocessing_metadata.json")
    with open(meta_path, 'w') as f:
        json.dump(unisolar_metadata, f, indent=2)
    print(f"Saved {meta_path}.")
    
    # =========================================================================
    # PART 2: KAGGLE BENCHMARK PREPARATION
    # =========================================================================
    print("\n--- Part 2: Processing Kaggle Benchmark Dataset ---")
    
    # Load raw files
    p1_g = pd.read_csv("data/raw/archive/Plant_1_Generation_Data.csv")
    p1_w = pd.read_csv("data/raw/archive/Plant_1_Weather_Sensor_Data.csv")
    p2_g = pd.read_csv("data/raw/archive/Plant_2_Generation_Data.csv")
    p2_w = pd.read_csv("data/raw/archive/Plant_2_Weather_Sensor_Data.csv")
    
    # Standardize timestamps
    p1_g['DT'] = pd.to_datetime(p1_g['DATE_TIME'], format='%d-%m-%Y %H:%M')
    p1_w['DT'] = pd.to_datetime(p1_w['DATE_TIME'], format='%Y-%m-%d %H:%M:%S')
    p2_g['DT'] = pd.to_datetime(p2_g['DATE_TIME'], format='%Y-%m-%d %H:%M:%S')
    p2_w['DT'] = pd.to_datetime(p2_w['DATE_TIME'], format='%Y-%m-%d %H:%M:%S')
    
    # Inner join on PLANT_ID and DT
    k1 = p1_g.merge(p1_w[['PLANT_ID', 'DT', 'AMBIENT_TEMPERATURE', 'IRRADIATION']], on=['PLANT_ID', 'DT'], how='inner')
    k2 = p2_g.merge(p2_w[['PLANT_ID', 'DT', 'AMBIENT_TEMPERATURE', 'IRRADIATION']], on=['PLANT_ID', 'DT'], how='inner')
    
    # Feature engineering for each plant
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
        
        # Chronological split: Train (May 15 - Jun 7, 24d), Val (Jun 8 - Jun 12, 5d), Test (Jun 13 - Jun 17, 5d)
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
        'AC_POWER',  # Target (kW)
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
    
    # Combined Kaggle Benchmark Splits
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
    
    # Kaggle Preprocessing Metadata
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
    
    print("\n=== PHASE 3 DATA PREPARATION PIPELINE COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
