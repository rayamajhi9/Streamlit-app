import streamlit as st
from streamlit_gsheets import GSheetsConnection

AUTHORIZED_USERS_WORKSHEET = "Authorized Users"


@st.cache_data(ttl=60)
def _get_allowed_emails() -> frozenset[str]:
    """Load normalized email addresses from the authorization worksheet."""
    connection = st.connection("gsheets", type=GSheetsConnection)
    users = connection.read(worksheet=AUTHORIZED_USERS_WORKSHEET)

    email_column = next(
        (column for column in users.columns if str(column).strip().lower() == "email"),
        users.columns[0],
    )
    return frozenset(
        str(email).strip().lower()
        for email in users[email_column].dropna()
        if str(email).strip()
    )


def require_authorization() -> str:
    """Require Google login and an approved email before continuing."""
    if "is_logged_in" not in st.user:
        st.error(
            "Authentication is not configured. Add an [auth] section to "
            ".streamlit/secrets.toml before starting the app."
        )
        st.stop()

    if not st.user["is_logged_in"]:
        st.title("Sign in required")
        st.write("Sign in with an authorized Google account to continue.")
        if st.button("Sign in with Google", type="primary"):
            st.login("google")
        st.stop()

    email = str(getattr(st.user, "email", "")).strip().lower()
    if email not in _get_allowed_emails():
        st.error("Your account is not authorized to access this app.")
        if st.button("Sign out"):
            st.logout()
        st.stop()

    return email
