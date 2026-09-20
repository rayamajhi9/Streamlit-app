import streamlit as st
from streamlit_gsheets import GSheetsConnection

conn = st.connection("gsheets", type=GSheetsConnection)

data = conn.read(
    worksheet="Expenses tracker"
)
st.dataframe(data)