"""
SolarSelect — Phase 9 Reusable UI Components
Adheres strictly to the light theme, minimal professional SaaS design system.
"""

from typing import Optional, List, Dict, Any
import streamlit as st
import html


def render_page_header(
    title: str,
    subtitle: str,
    breadcrumb: Optional[str] = None
) -> None:
    """Renders a clean, structured page header with optional breadcrumbs."""
    bc_html = ""
    if breadcrumb:
        safe_bc = html.escape(breadcrumb)
        bc_html = f'<div class="ss-breadcrumb">{safe_bc}</div>'

    safe_title = html.escape(title)
    safe_subtitle = html.escape(subtitle)

    st.markdown(
        f"""
        <div class="ss-page-header">
            {bc_html}
            <h1 class="ss-page-title">{safe_title}</h1>
            <p class="ss-page-subtitle">{safe_subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_metric_card(
    label: str,
    value: str,
    caption: Optional[str] = None,
    badge_text: Optional[str] = None,
    badge_variant: str = "neutral"
) -> None:
    """Renders a minimal professional metric card with optional status badge."""
    safe_label = html.escape(label)
    safe_value = html.escape(value)
    caption_html = f'<div class="ss-metric-caption">{html.escape(caption)}</div>' if caption else ""

    badge_html = ""
    if badge_text:
        badge_html = render_status_badge(badge_text, variant=badge_variant, return_html=True)

    st.markdown(
        f"""
        <div class="ss-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:0.5rem; flex-wrap:wrap; margin-bottom:0.35rem;">
                <div class="ss-metric-label" style="margin-bottom:0;">{safe_label}</div>
                {badge_html}
            </div>
            <div class="ss-metric-value">{safe_value}</div>
            {caption_html}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_status_badge(
    text: str,
    variant: str = "neutral",
    return_html: bool = False
) -> Optional[str]:
    """
    Renders or returns a semantic status badge.
    Variants: 'success', 'warning', 'error', 'neutral'.
    """
    variant_clean = variant.lower() if variant.lower() in ("success", "warning", "error", "neutral") else "neutral"

    icons = {
        "success": "●",
        "warning": "▲",
        "error": "✕",
        "neutral": "○"
    }
    icon = icons.get(variant_clean, "○")
    safe_text = html.escape(text)

    badge_html = f'<span class="ss-badge ss-badge-{variant_clean}"><span>{icon}</span> {safe_text}</span>'

    if return_html:
        return badge_html
    st.markdown(badge_html, unsafe_allow_html=True)
    return None


def render_banner(
    message: str,
    variant: str = "info",
    title: Optional[str] = None
) -> None:
    """
    Renders an information or warning banner.
    Variants: 'info', 'warning', 'error', 'success'.
    """
    variant_clean = variant.lower() if variant.lower() in ("info", "warning", "error", "success") else "info"

    icons = {
        "info": "ℹ",
        "warning": "⚠",
        "error": "⛔",
        "success": "✓"
    }
    icon = icons.get(variant_clean, "ℹ")

    title_html = f"<strong>{html.escape(title)}: </strong>" if title else ""
    safe_msg = html.escape(message)

    st.markdown(
        f"""
        <div class="ss-banner ss-banner-{variant_clean}">
            <div style="font-size: 1.1rem; line-height: 1;">{icon}</div>
            <div>{title_html}{safe_msg}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_section_header(title: str, subtitle: Optional[str] = None) -> None:
    """Renders a clean section header with subtle divider."""
    safe_title = html.escape(title)
    sub_html = f'<div style="font-size:0.85rem; color:#475569; margin-top:-0.4rem; margin-bottom:0.75rem;">{html.escape(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="ss-section-header">{safe_title}</div>
        {sub_html}
        """,
        unsafe_allow_html=True
    )


def render_empty_state(
    title: str,
    description: str,
    action_label: Optional[str] = None,
    badge_text: Optional[str] = "Placeholder / Future Integration"
) -> None:
    """Renders a clean dashed placeholder / empty state."""
    safe_title = html.escape(title)
    safe_desc = html.escape(description)
    badge_html = ""
    if badge_text:
        badge_html = f'<div style="margin-bottom:0.75rem;">{render_status_badge(badge_text, variant="neutral", return_html=True)}</div>'

    st.markdown(
        f"""
        <div class="ss-empty-state">
            {badge_html}
            <div class="ss-empty-title">{safe_title}</div>
            <div class="ss-empty-desc">{safe_desc}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_step_card(
    step_num: str,
    title: str,
    description: str,
    status_label: Optional[str] = None,
    status_variant: str = "neutral"
) -> None:
    """Renders a clean step box for workflow visualization."""
    safe_step = html.escape(step_num)
    safe_title = html.escape(title)
    safe_desc = html.escape(description)
    badge_html = ""
    if status_label:
        badge_html = f'<div style="margin-top:0.4rem;">{render_status_badge(status_label, variant=status_variant, return_html=True)}</div>'

    st.markdown(
        f"""
        <div class="ss-step-box">
            <div class="ss-step-num">{safe_step}</div>
            <div class="ss-step-title">{safe_title}</div>
            <div class="ss-step-desc">{safe_desc}</div>
            {badge_html}
        </div>
        """,
        unsafe_allow_html=True
    )
