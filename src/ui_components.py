from __future__ import annotations

from html import escape

import streamlit as st


def apply_theme_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            color-scheme: dark;
            --canvas: #09090b;
            --surface: #151519;
            --surface-raised: #1b1b20;
            --border: #2a2a31;
            --muted: #8c8c97;
            --text: #f4f4f5;
            --green: #8be23f;
            --yellow: #f5c400;
        }
        .stApp {
            background: var(--canvas);
            color: var(--text);
        }
        .block-container {
            max-width: 1540px;
            padding: 2rem 2rem 3rem;
        }
        [data-testid="stSidebar"] {
            background: #151519;
            border-right: 1px solid #25252b;
        }
        [data-testid="stSidebar"] > div:first-child {
            position: relative;
            padding-top: 1rem;
        }
        [data-testid="stSidebar"] a {
            border-radius: 9px;
            margin: 0.15rem 0.45rem;
            color: #b6b6bf;
        }
        [data-testid="stSidebar"] a:hover {
            background: #222229;
            color: var(--text);
        }
        [data-testid="stSidebar"] a[aria-current="page"] {
            background: rgba(139, 226, 63, 0.12);
            color: var(--green);
        }
        [data-testid="stSidebar"] a p {
            font-size: 0.9rem;
        }
        .sw-brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.55rem 0.35rem 0.9rem;
            margin: 0 0.4rem 1.15rem;
            border-bottom: 1px solid var(--border);
        }
        .sw-brand-mark {
            display: grid;
            width: 2.6rem;
            height: 2.6rem;
            place-items: center;
            border: 1px solid rgba(139, 226, 63, 0.6);
            border-radius: 50%;
            color: var(--green);
            font-size: 1.35rem;
            background: rgba(139, 226, 63, 0.08);
        }
        .sw-brand-name {
            color: var(--text);
            font-size: 0.95rem;
            font-weight: 750;
            letter-spacing: 0.025em;
        }
        .sw-brand-caption {
            margin-top: 0.15rem;
            color: var(--muted);
            font-size: 0.64rem;
            letter-spacing: 0.09em;
            text-transform: uppercase;
        }
        .sw-nav-section {
            margin: 1.1rem 0.7rem 0.35rem;
            color: #777780;
            font-size: 0.68rem;
            font-weight: 650;
            letter-spacing: 0.09em;
            text-transform: uppercase;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--border);
            border-radius: 15px;
            background: var(--surface);
        }
        h1, h2, h3 {
            color: var(--text);
            letter-spacing: -0.025em;
        }
        h1 {
            font-size: clamp(1.7rem, 3vw, 2.2rem);
        }
        [data-testid="stCaptionContainer"], .stCaption {
            color: var(--muted);
        }
        [data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1rem 1.1rem;
        }
        [data-testid="stMetricLabel"] {
            color: #a4a4ae;
        }
        [data-testid="stMetricValue"] {
            color: var(--text);
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
        }
        [data-testid="stFileUploader"],
        [data-testid="stForm"],
        [data-testid="stExpander"] {
            border-color: var(--border);
            border-radius: 12px;
        }
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
            background: var(--surface);
            border-color: var(--border);
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 9px;
            border-color: #3a3a42;
            background: #202025;
            color: var(--text);
            transition: border-color 120ms ease, background 120ms ease;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            border-color: var(--green);
            color: var(--green);
        }
        .stButton > button[kind="primary"] {
            background: #78c735;
            border-color: #78c735;
            color: #10130d;
        }
        .sw-page-heading {
            margin-bottom: 1.4rem;
        }
        .sw-page-heading h1 {
            font-size: 2rem !important;
            margin-bottom: 0.15rem;
        }
        .sw-page-heading p {
            color: var(--muted);
            margin: 0;
        }
        .sw-card {
            min-height: 7rem;
            padding: 1rem 1.05rem;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: linear-gradient(145deg, #1a1a1f, #151519);
        }
        .sw-card-label {
            color: #a4a4ae;
            font-size: 0.8rem;
        }
        .sw-card-value {
            margin-top: 0.45rem;
            color: var(--text);
            font-size: 1.75rem;
            font-weight: 720;
            line-height: 1.15;
            overflow-wrap: anywhere;
        }
        .sw-card-delta {
            margin-top: 0.4rem;
            color: var(--muted);
            font-size: 0.75rem;
        }
        .sw-live {
            display: inline-flex;
            align-items: center;
            gap: 0.42rem;
            padding: 0.32rem 0.65rem;
            border: 1px solid #303036;
            border-radius: 999px;
            color: #b9b9c1;
            font-size: 0.72rem;
            white-space: nowrap;
        }
        .sw-live-dot {
            width: 0.42rem;
            height: 0.42rem;
            border-radius: 50%;
            background: var(--green);
            box-shadow: 0 0 10px rgba(139, 226, 63, 0.55);
        }
        .sw-section-heading {
            margin: 0.35rem 0 0.2rem;
            color: var(--text);
            font-size: 1.05rem;
            font-weight: 650;
        }
        .sw-section-caption {
            margin: 0 0 0.8rem;
            color: var(--muted);
            font-size: 0.78rem;
        }
        .sw-panel {
            height: 100%;
            padding: 1.2rem;
            border: 1px solid var(--border);
            border-radius: 15px;
            background: var(--surface);
        }
        .sw-panel-title {
            margin: 0;
            color: var(--text);
            font-size: 1.02rem;
            font-weight: 650;
        }
        .sw-panel-caption {
            margin-top: 0.35rem;
            color: var(--muted);
            font-size: 0.78rem;
        }
        .sw-alert {
            display: flex;
            align-items: center;
            gap: 0.85rem;
            padding: 0.9rem 1rem;
            border: 1px solid rgba(245, 196, 0, 0.3);
            border-radius: 12px;
            background: rgba(245, 196, 0, 0.07);
        }
        .sw-alert-icon {
            display: grid;
            width: 2.3rem;
            height: 2.3rem;
            flex: 0 0 auto;
            place-items: center;
            border: 1px solid rgba(245, 196, 0, 0.35);
            border-radius: 9px;
            color: var(--yellow);
        }
        .sw-alert-title {
            color: #f2dc7b;
            font-size: 0.86rem;
            font-weight: 650;
        }
        .sw-alert-caption {
            margin-top: 0.2rem;
            color: var(--muted);
            font-size: 0.74rem;
        }
        .sw-empty {
            padding: 2rem 1rem;
            border: 1px dashed #35353d;
            border-radius: 12px;
            color: var(--muted);
            text-align: center;
        }
        .sw-health {
            display: flex;
            align-items: center;
            gap: 1.2rem;
            min-height: 10.1rem;
        }
        .sw-health-ring {
            display: grid;
            width: 6rem;
            height: 6rem;
            flex: 0 0 auto;
            place-items: center;
            border-radius: 50%;
            background: conic-gradient(var(--yellow) var(--health-score), #34343b 0);
        }
        .sw-health-ring-inner {
            display: grid;
            width: 4.9rem;
            height: 4.9rem;
            place-content: center;
            border-radius: 50%;
            background: var(--surface);
            text-align: center;
        }
        .sw-health-score {
            color: var(--yellow);
            font-size: 1.65rem;
            font-weight: 750;
            line-height: 1;
        }
        .sw-health-percent {
            margin-top: 0.2rem;
            color: var(--muted);
            font-size: 0.66rem;
        }
        @media (max-width: 760px) {
            .block-container {
                padding: 1.25rem 1rem 2rem;
            }
            [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap;
                gap: 0.65rem;
            }
            [data-testid="stHorizontalBlock"] > [data-testid="column"] {
                flex: 1 1 100%;
                min-width: 100%;
                width: 100%;
            }
            .sw-page-heading {
                margin-bottom: 1rem;
            }
            .sw-page-heading h1 {
                font-size: 1.7rem !important;
            }
            .sw-health {
                gap: 0.85rem;
            }
            .sw-card {
                min-height: 6.2rem;
                padding: 0.85rem;
            }
            .sw-card-value {
                font-size: 1.5rem;
            }
            .sw-panel {
                padding: 0.9rem;
            }
            .sw-alert {
                align-items: flex-start;
                padding: 0.75rem;
            }
            [data-testid="stDataFrame"] {
                overflow-x: auto;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    st.sidebar.markdown(
        """
        <div class="sw-brand">
            <div class="sw-brand-mark">◉</div>
            <div>
                <div class="sw-brand-name">STOCKWISE AI</div>
                <div class="sw-brand-caption">Inventory intelligence</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_title(title: str, subtitle: str | None = None) -> None:
    caption = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f'<div class="sw-page-heading"><h1>{escape(title)}</h1>{caption}</div>',
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, delta: str | None = None) -> None:
    delta_html = f'<div class="sw-card-delta">{escape(delta)}</div>' if delta else ""
    st.markdown(
        f"""
        <div class="sw-card">
            <div class="sw-card-label">{escape(label)}</div>
            <div class="sw-card-value">{escape(value)}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(text: str, variant: str = "info") -> str:
    colors = {
        "info": "#38bdf8",
        "success": "#8be23f",
        "warning": "#f5c400",
        "danger": "#fb7185",
    }
    color = colors.get(variant, colors["info"])
    return (
        f'<span style="display:inline-block;padding:0.25rem 0.6rem;'
        f'border:1px solid {color};border-radius:999px;color:{color};'
        f'font-size:0.75rem;font-weight:600">{escape(text)}</span>'
    )
