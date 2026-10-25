import os
import sys

import streamlit as st

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

st.set_page_config(page_title="VisionMate", layout="wide", initial_sidebar_state="collapsed")

from views.auth_page import render_auth_page
from views.live_monitor_tab import render_live_tab
from views.model_comparison_tab import render_comparison_tab
from views.trip_analytics_tab import render_analytics_tab
from views.ui import APP_NAME, APP_TAGLINE, button, inject_css
from views.video_test_tab import render_video_test_tab
from utils.mobile_support import inject_head_tags

inject_css()


def init_session_state():
    for k, v in dict(logged_in=False, user=None, user_id=None, username=None).items():
        st.session_state.setdefault(k, v)


def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def render_header():
    user = st.session_state.get("user") or {}
    left, right = st.columns([5, 1])
    with left:
        st.markdown(f"<div class='dg-brand'><div class='dg-logo'></div><div><div class='dg-name'>{APP_NAME}</div>"
                    f"<div class='dg-tag'>{APP_TAGLINE} · signed in as <b style='color:#e5eef7'>{user.get('full_name', 'User')}</b></div></div></div>",
                    unsafe_allow_html=True)
    with right:
        if button("Sign out", key="logout_btn"):
            logout()
    st.divider()


def main():
    init_session_state()
    inject_head_tags()
    if not st.session_state["logged_in"]:
        render_auth_page()
        return
    render_header()
    user_id = st.session_state["user_id"]
    t_live, t_hist, t_cmp, t_vid = st.tabs(["Live Monitor", "Trip History", "Model Comparison", "Video Test"])
    with t_hist:
        render_analytics_tab(user_id)
    with t_cmp:
        render_comparison_tab()
    with t_vid:
        render_video_test_tab()
    with t_live:
        render_live_tab(user_id)


main()
