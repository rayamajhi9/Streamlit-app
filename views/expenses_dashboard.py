import streamlit as st

st.title("Expenses Dashboard")

data = conn.read(
    worksheet="Expenses tracker"
)
st.dataframe(data)
