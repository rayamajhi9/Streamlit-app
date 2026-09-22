import streamlit as st
from streamlit_gsheets import GSheetsConnection


conn = st.connection("gsheets", type=GSheetsConnection)

st.title("Expenses Dashboard")

data = conn.read(
    worksheet="Expense Register"
)
st.dataframe(data)
