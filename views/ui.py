"""Shared look and feel: CSS, level colours, cards, gauge and version-safe widget helpers."""
import inspect

import plotly.graph_objects as go
import streamlit as st

APP_NAME = "VisionMate"
APP_TAGLINE = "Real-Time Driver Drowsiness Detection"

LEVEL_COLORS = {"Alert": "#34d399", "Warning": "#fbbf24", "Danger": "#f43f5e",
                "Calibrating": "#38bdf8", "No face": "#8fa3b8", "Starting": "#8fa3b8"}
CARD_BG = "rgba(0,0,0,0)"
CHART_THEME = dict(plot_bgcolor=CARD_BG, paper_bgcolor=CARD_BG, font=dict(color="#e0e0e0", size=12),
                   margin=dict(t=50, b=40, l=50, r=20))

CSS = """
<style>
  .stApp { background: radial-gradient(1200px 700px at 8% -10%, rgba(20,184,166,.18), transparent 60%),
                       radial-gradient(900px 600px at 100% 0%, rgba(99,102,241,.16), transparent 55%),
                       linear-gradient(160deg, #060d18 0%, #0a1626 55%, #07121f 100%); background-attachment: fixed; }
  [data-testid="stHeader"] { background: transparent; }
  .block-container { padding-top: 3.2rem; max-width: 1320px; }
  h1, h2, h3, h4, h5 { letter-spacing: .2px; }
  .stTabs [role="tablist"], .stTabs [data-baseweb="tab-list"] { background: rgba(255,255,255,.04); border: 1px solid rgba(148,214,226,.12);
        border-radius: 999px; padding: 5px; gap: 4px; width: fit-content; backdrop-filter: blur(10px); }
  .stTabs [role="tab"] { color: #8fa3b8; border-radius: 999px; padding: 8px 22px; height: auto; margin: 0; }
  .stTabs [role="tab"] p { color: inherit; margin: 0; }
  .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"], .stTabs .react-aria-SelectionIndicator { display: none !important; }
  .stTabs [role="tab"][aria-selected="true"] { background: linear-gradient(135deg, #2dd4bf, #38bdf8) !important; color: #04222a !important; font-weight: 700; }
  .stTabs [role="tab"]:hover { color: #e5eef7; }
  .stTabs [role="tab"][aria-selected="true"]:hover { color: #04222a; }
  .stButton > button, .stDownloadButton > button { border-radius: 14px; font-weight: 600; background: rgba(255,255,255,.05);
        border: 1px solid rgba(148,214,226,.18); color: #e5eef7; transition: all .15s; }
  .stButton > button:hover, .stDownloadButton > button:hover { border-color: #2dd4bf; color: #2dd4bf; background: rgba(45,212,191,.08); }
  .stButton > button[kind="primary"] { background: linear-gradient(135deg, #2dd4bf, #38bdf8); color: #04222a; border: none; }
  .stButton > button[kind="primary"]:hover { color: #04222a; filter: brightness(1.08); }
  .stButton > button:disabled { opacity: .35; }
  div[data-testid="stMetric"], div[data-testid="metric-container"] { background: rgba(255,255,255,.04); border: 1px solid rgba(148,214,226,.12);
        border-radius: 18px; padding: 14px 16px; backdrop-filter: blur(10px); }
  div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"] { background: rgba(255,255,255,.035); border: 1px solid rgba(148,214,226,.12);
        border-radius: 18px; padding: 6px; overflow: hidden; }
  div[data-testid="stExpander"] { background: rgba(255,255,255,.035); border: 1px solid rgba(148,214,226,.12); border-radius: 18px; }
  div[data-testid="stForm"] { background: rgba(255,255,255,.04); border: 1px solid rgba(148,214,226,.14); border-radius: 20px; backdrop-filter: blur(12px); }
  div[data-testid="stAlert"] { border-radius: 16px; }
  .stTextInput input, .stSelectbox [data-baseweb="select"] > div { border-radius: 12px !important; }
  .dg-card { background: rgba(255,255,255,.045); border: 1px solid rgba(148,214,226,.12); border-radius:18px; padding:16px 18px; margin-bottom:12px;
        border-left:4px solid #38bdf8; backdrop-filter: blur(10px); box-shadow: 0 8px 30px rgba(0,0,0,.25); }
  .dg-label { font-size:11px; color:#8fa3b8; margin:0 0 4px 0; text-transform:uppercase; letter-spacing:1.2px; }
  .dg-value { font-size:26px; font-weight:700; margin:0; line-height:1.15; }
  .dg-sub { font-size:12px; color:#8fa3b8; margin:3px 0 0 0; }
  .dg-bar { height:7px; background: rgba(255,255,255,.08); border-radius:999px; margin-top:9px; overflow:hidden; }
  .dg-bar > div { height:100%; border-radius:999px; }
  .dg-banner { border-radius:20px; padding:20px 22px; margin-bottom:14px; text-align:center; backdrop-filter: blur(10px); }
  .dg-banner h2 { margin:0; font-size:34px; letter-spacing:2px; }
  .dg-banner p { margin:4px 0 0 0; font-size:14px; opacity:.9; }
  @keyframes dgpulse { 0%{box-shadow:0 0 0 0 rgba(244,63,94,.65);} 70%{box-shadow:0 0 0 18px rgba(244,63,94,0);} 100%{box-shadow:0 0 0 0 rgba(244,63,94,0);} }
  .dg-danger { animation: dgpulse 1.2s infinite; }
  .dg-chip { display:inline-block; padding:3px 12px; border-radius:999px; font-size:12px; font-weight:600; margin-right:6px; }
  .dg-event { font-size:13px; padding:8px 12px; border-radius:12px; background: rgba(255,255,255,.045); margin-bottom:6px; }
  .dg-brand { display:flex; align-items:center; gap:12px; padding-top:2px; }
  .dg-logo { width:34px; height:34px; border-radius:50%; background: conic-gradient(from 210deg, #2dd4bf, #38bdf8, #a78bfa, #2dd4bf); position:relative; }
  .dg-logo::after { content:""; position:absolute; inset:9px; border-radius:50%; background:#0a1626; }
  .dg-name { font-size:21px; font-weight:800; line-height:1.05; background: linear-gradient(90deg, #5eead4, #7dd3fc); -webkit-background-clip:text; background-clip:text; color:transparent; }
  .dg-tag { font-size:12px; color:#8fa3b8; }
  @media (max-width: 768px) {
    .block-container { padding: 0.75rem 0.6rem 3rem 0.6rem !important; }
    h1, h2 { font-size: 1.4rem !important; }
    .stTabs [role="tablist"] { overflow-x: auto; max-width: 100%; }
    .stTabs [role="tab"] { padding: 8px 12px; font-size: 13px; white-space: nowrap; }
    .stButton > button { min-height: 48px; width: 100%; }
    .dg-banner h2 { font-size: 26px; }
    .dg-value { font-size: 22px; }
    video { max-width: 100% !important; height: auto !important; border-radius: 16px; }
  }
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def _has_width(fn) -> bool:
    try:
        return "width" in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False


_BTN_WIDTH = dict(width="stretch") if _has_width(st.button) else dict(use_container_width=True)
_PLOT_WIDTH = dict(width="stretch") if _has_width(st.plotly_chart) else dict(use_container_width=True)
_DF_WIDTH = dict(width="stretch") if _has_width(st.dataframe) else dict(use_container_width=True)
_IMG_WIDTH = dict(width="stretch") if _has_width(st.image) else dict(use_container_width=True)


def button(label, **kw):
    return st.button(label, **_BTN_WIDTH, **kw)


def download_button(label, data, file_name, mime="text/csv", **kw):
    return st.download_button(label, data, file_name=file_name, mime=mime, **_BTN_WIDTH, **kw)


def plot(fig, key=None):
    st.plotly_chart(fig, **_PLOT_WIDTH, key=key)


def table(df, **kw):
    st.dataframe(df, hide_index=True, **_DF_WIDTH, **kw)


def image(img, **kw):
    st.image(img, **_IMG_WIDTH, **kw)


def level_color(name: str) -> str:
    return LEVEL_COLORS.get(name, "#7f8c8d")


def card(label: str, value: str, color: str, sub: str = "", bar: float = None):
    bar_html = (f"<div class='dg-bar'><div style='width:{max(0, min(1, bar)) * 100:.0f}%;background:{color};'></div></div>"
                if bar is not None else "")
    sub_html = f"<p class='dg-sub'>{sub}</p>" if sub else ""
    st.markdown(f"<div class='dg-card' style='border-left-color:{color};'><p class='dg-label'>{label}</p>"
                f"<p class='dg-value' style='color:{color};'>{value}</p>{sub_html}{bar_html}</div>", unsafe_allow_html=True)


def banner(title: str, subtitle: str, color: str, pulse: bool = False):
    st.markdown(f"<div class='dg-banner {'dg-danger' if pulse else ''}' style='background:{color}26;border:2px solid {color};'>"
                f"<h2 style='color:{color};'>{title}</h2><p>{subtitle}</p></div>", unsafe_allow_html=True)


def gauge(score: float, height: int = 210):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=float(score),
        number=dict(font=dict(size=40, color="#e0e0e0"), suffix=""),
        title=dict(text="Drowsiness score", font=dict(size=13, color="#9aa4b2")),
        gauge=dict(axis=dict(range=[0, 100], tickcolor="#9aa4b2"), bar=dict(color="#e0e0e0", thickness=0.22),
                   bgcolor=CARD_BG, borderwidth=0,
                   steps=[dict(range=[0, 30], color="#1e6b3c"), dict(range=[30, 60], color="#8a5a0a"),
                          dict(range=[60, 100], color="#8a2a22")])))
    fig.update_layout(height=height, paper_bgcolor=CARD_BG, margin=dict(t=50, b=10, l=25, r=25), font=dict(color="#e0e0e0"))
    return fig
