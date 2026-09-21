import streamlit as st

from auth import require_authorization

require_authorization()

# -- PAGE SETUP ---
expense_view = st.Page(
    page="views/expenses_view.py",
    title="Expense Tracker", 
    icon=":material/account_circle:",
)

project_1_page = st.Page(
    page="views/expenses_dashboard.py",
    title="Expenses Dashboard",
    icon=":material/bar_chart:",
)

project_2_page = st.Page(
    page="views/chatbot.py",
    title="Chatbot",
    icon=":material/smart_toy:",
)

pg = st.navigation(
    pages=[expense_view, project_1_page, project_2_page],
    default=expense_view,
    title="Expense Tracker",
    icon=":material/account_circle:",
    
)

pg.run()

# data = conn.read(
#    worksheet="Expenses tracker"
#)
#st.dataframe(data)


#data = conn.read(
#    worksheet="Expense Register"
#)
#st.dataframe(data)
