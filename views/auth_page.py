import time

import streamlit as st

from views.ui import APP_NAME, APP_TAGLINE, button
from utils.auth_utils import login_user, register_user


def _login_form():
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Sign in", type="primary")
    if submitted:
        result = login_user(username, password)
        if result["success"]:
            u = result["user"]
            st.session_state.update(logged_in=True, user=u, user_id=u["id"], username=u["username"])
            st.success(result["message"])
            time.sleep(0.5)
            st.rerun()
        else:
            st.error(result["message"])


def _register_form():
    with st.form("register_form", clear_on_submit=False):
        full_name = st.text_input("Full name", placeholder="e.g. Aisyah Rahman", key="reg_fullname")
        username = st.text_input("Username", key="reg_username", help="3-30 letters, numbers, . _ -")
        password = st.text_input("Password", type="password", key="reg_password", help="At least 6 characters")
        submitted = st.form_submit_button("Create account", type="primary")
    if submitted:
        result = register_user(full_name, username, password)
        (st.success if result["success"] else st.error)(result["message"])


def render_auth_page():
    st.markdown(
        f"""<div style="text-align:center;padding:28px 0 8px 0;">
              <div class="dg-logo" style="margin:0 auto 10px auto;width:48px;height:48px;"></div>
              <h1 style="margin:4px 0 2px 0;font-size:2.4rem;background:linear-gradient(90deg,#5eead4,#7dd3fc);-webkit-background-clip:text;background-clip:text;color:transparent;">{APP_NAME}</h1>
              <p style="color:#9aa4b2;font-size:14px;margin:0;">{APP_TAGLINE}</p>
            </div>""", unsafe_allow_html=True)
    st.divider()
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        login_tab, register_tab = st.tabs(["Sign in", "Create account"])
        with login_tab:
            _login_form()
        with register_tab:
            _register_form()
        st.caption("Your trip history is stored per account on this server. No video is saved.")
