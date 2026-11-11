"""
SolarSelect — Phase 9 UI Design System Tokens
Strict Light Theme + Minimal Professional SaaS Aesthetic
"""

# Palette
COLOR_BG_PRIMARY = "#FFFFFF"
COLOR_BG_SECONDARY = "#F8FAFC"
COLOR_BG_CARD = "#FFFFFF"
COLOR_BG_SIDEBAR = "#F8FAFC"
COLOR_BG_HOVER = "#F1F5F9"

COLOR_TEXT_PRIMARY = "#0F172A"       # Charcoal primary text
COLOR_TEXT_SECONDARY = "#475569"     # Muted slate secondary text
COLOR_TEXT_MUTED = "#94A3B8"         # Tertiary / caption text

COLOR_ACCENT = "#15803D"             # Restrained solar green (tailwind green-700)
COLOR_ACCENT_HOVER = "#166534"       # Deep forest green (tailwind green-800)
COLOR_ACCENT_BG = "#DCFCE7"          # Light green badge background (tailwind green-100)
COLOR_ACCENT_BORDER = "#86EFAC"      # Light green border (tailwind green-300)

COLOR_BORDER_SUBTLE = "#E2E8F0"      # Light slate border
COLOR_BORDER_STRONG = "#CBD5E1"      # Medium slate border

# Semantic Status Tokens
STATUS_COLORS = {
    "SUCCESS": {
        "text": "#166534",
        "bg": "#DCFCE7",
        "border": "#86EFAC",
        "icon": "●"
    },
    "WARNING": {
        "text": "#92400E",
        "bg": "#FEF3C7",
        "border": "#FDE68A",
        "icon": "▲"
    },
    "ERROR": {
        "text": "#991B1B",
        "bg": "#FEE2E2",
        "border": "#FCA5A5",
        "icon": "✕"
    },
    "NEUTRAL": {
        "text": "#475569",
        "bg": "#F1F5F9",
        "border": "#CBD5E1",
        "icon": "○"
    },
}

# Typography
FONT_FAMILY = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, '
    'Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji"'
)
FONT_SIZE_XS = "0.75rem"
FONT_SIZE_SM = "0.875rem"
FONT_SIZE_BASE = "1rem"
FONT_SIZE_LG = "1.125rem"
FONT_SIZE_XL = "1.25rem"
FONT_SIZE_2XL = "1.5rem"

# Spacing & Shadows
SPACING_XS = "4px"
SPACING_SM = "8px"
SPACING_MD = "16px"
SPACING_LG = "24px"
SPACING_XL = "32px"

RADIUS_SM = "4px"
RADIUS_MD = "6px"
RADIUS_LG = "8px"

SHADOW_SM = "0 1px 2px 0 rgba(0, 0, 0, 0.05)"
SHADOW_MD = "0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)"

