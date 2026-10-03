"""Prime System Builder – entry point: page config, CSS, optional password gate, navigation."""
import hmac

import streamlit as st

from utils.state import init_state
from utils.ui import banner, inject_css, register_plotly_template

st.set_page_config(page_title="Prime System Builder", page_icon="💧", layout="wide", initial_sidebar_state="expanded")
st.session_state["_data_warnings_shown"] = set()
inject_css()
register_plotly_template()
init_state()


def _password_gate() -> bool:
    """If APP_PASSWORD is set in st.secrets, ask for it once per session. Otherwise skip."""
    try:
        expected = st.secrets.get("APP_PASSWORD", None)
    except Exception:  # noqa: BLE001 – no secrets file at all
        expected = None
    if not expected or st.session_state.get("authed"):
        return True
    banner()
    st.markdown(
        '<div class="hero"><div class="wordmark">Birla Opus Prime</div><h1>Prime System Builder</h1>'
        '<div class="sub">This prototype is password protected.</div></div>',
        unsafe_allow_html=True,
    )
    with st.form("pw_form"):
        pw = st.text_input("Password", type="password", key="pw_input")
        if st.form_submit_button("Enter", type="primary", icon=":material/lock_open:"):
            if hmac.compare_digest(str(pw), str(expected)):
                st.session_state["authed"] = True
                st.rerun()
            st.error("Incorrect password.")
    return False


if _password_gate():
    pg = st.navigation([
        st.Page("app_pages/system_builder.py", title="System Builder", icon=":material/construction:", default=True),
        st.Page("app_pages/resource_centre.py", title="Resource Centre", icon=":material/library_books:"),
        st.Page("app_pages/project_insights.py", title="Project Insights", icon=":material/insights:"),
    ])
    pg.run()
