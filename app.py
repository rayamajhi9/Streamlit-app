import streamlit as st
from streamlit_gsheets import GSheetsConnection

conn = st.connection("gsheets", type=GSheetsConnection)

data = conn.read(
    spreadsheet="https://docs.google.com/spreadsheets/d/1KwRByJIUpQ4Ff8c1E-dj9EIPRpjeOno9QzqSfz0JGTk/edit?gid=221719433#gid=221719433",
    worksheet="Expenses tracker"
)
st.dataframe(data)