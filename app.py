import streamlit as st
from streamlit_gsheets import GSheetsConnection
from auth import require_authorization

require_authorization()

conn = st.connection("gsheets", type=GSheetsConnection)

data = conn.read(
    worksheet="Expenses tracker"
)
st.dataframe(data)