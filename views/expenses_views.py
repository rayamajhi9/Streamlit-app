import re
from datetime import date

import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection


WORKSHEET = "Expense Register"
conn = st.connection("gsheets", type=GSheetsConnection)
data = conn.read(worksheet=WORKSHEET)


def options_for(column: str, fallback: list[str]) -> list[str]:
    values = sorted(
        {
            str(value).strip()
            for value in data[column].dropna()
            if str(value).strip()
        }
    )
    return values or fallback


def next_expense_id() -> str:
    numbers = [
        int(match.group(1))
        for value in data["Expense ID"].dropna()
        if (match := re.fullmatch(r"EXP(\d+)", str(value).strip()))
    ]
    return f"EXP{max(numbers, default=0) + 1:04d}"


st.title("Add new expense", text_alignment="center")
st.caption("Log farm expenses with priority and budget tracking.", text_alignment="center")

with st.form("add_expense", clear_on_submit=True, border=True):
    first_row = st.columns(3)
    with first_row[0]:
        st.text_input("Expense ID", value=next_expense_id(), disabled=True)
    with first_row[1]:
        expense_date = st.date_input("Date", value=date.today())
    with first_row[2]:
        category = st.selectbox("Category", options_for("Category", ["Other"]))

    second_row = st.columns(3)
    with second_row[0]:
        subcategory = st.selectbox(
            "Subcategory",
            options_for("Subcategory", ["Other"]),
        )
    with second_row[1]:
        enterprise = st.selectbox(
            "Enterprise",
            options_for("Enterprise", ["Other"]),
        )
    with second_row[2]:
        description = st.text_input("Description")

    supplier = st.text_input("Supplier", placeholder="Enter supplier name")

    cost_row = st.columns(4)
    with cost_row[0]:
        quantity = st.number_input("Qty", min_value=0.0, step=1.0)
    with cost_row[1]:
        unit = st.selectbox("Unit", options_for("Unit", ["Item", "Kg", "Litre"]))
    with cost_row[2]:
        unit_cost = st.number_input(
            "Unit cost",
            min_value=0.0,
            step=0.01,
            format="%.2f",
        )
    with cost_row[3]:
        total_cost = quantity * unit_cost
        st.number_input(
            "Total cost",
            value=total_cost,
            disabled=True,
            format="%.2f",
        )

    payment_row = st.columns(3)
    with payment_row[0]:
        payment_method = st.selectbox(
            "Payment method",
            options_for("Payment Method", ["Cash", "Bank", "Other"]),
        )
    with payment_row[1]:
        paid_by = st.selectbox("Paid by", options_for("Paid By", ["Other"]))
    with payment_row[2]:
        receipt_file = st.file_uploader(
            "Upload receipt",
            type=["pdf", "png", "jpg", "jpeg"],
        )

    options_row = st.columns(3)
    with options_row[0]:
        recurring = st.checkbox("Recurring expense")
    with options_row[1]:
        priority = st.selectbox("Priority", ["High", "Med", "Low"])
    with options_row[2]:
        budgeted = st.checkbox("Budgeted expense")

    tax = st.number_input("Tax (%)", min_value=0.0, max_value=100.0, step=0.01, format="%.2f")
    notes = st.text_area("Notes", placeholder="Add any notes here...", height=120)

    action_row = st.columns(3)
    with action_row[0]:
        submitted = st.form_submit_button(
            "Save expense",
            type="primary",
            icon=":material/save:",
        )
    with action_row[1]:
        clear_form = st.form_submit_button(
            "Clear form",
            icon=":material/ink_eraser:",
        )
    with action_row[2]:
        cancelled = st.form_submit_button(
            "Cancel",
            icon=":material/close:",
        )

if cancelled:
    st.info("Expense entry cancelled.")
elif clear_form:
    st.info("Form cleared. Enter a new expense when ready.")
elif submitted:
    if not description.strip():
        st.error("Enter a description before adding the expense.")
    elif quantity <= 0:
        st.error("Quantity must be greater than zero.")
    elif unit_cost <= 0:
        st.error("Unit cost must be greater than zero.")
    else:
        new_row = pd.DataFrame(
            [
                {
                    "Expense ID": next_expense_id(),
                    "Date": expense_date.isoformat(),
                    "Category": category,
                    "Subcategory": subcategory.strip(),
                    "Enterprise": enterprise,
                    "Description": description.strip(),
                    "Supplier": supplier.strip(),
                    "Qty": quantity,
                    "Unit": unit.strip(),
                    "Unit Cost": unit_cost,
                    "Total Cost": total_cost,
                    "Payment Method": payment_method,
                    "Paid By": paid_by,
                    "Receipt": receipt_file.name if receipt_file else "",
                    "Recurring": "Yes" if recurring else "No",
                    "Priority": priority,
                    "Budgeted": "Yes" if budgeted else "No",
                    "Tax": tax,
                    "Notes": notes.strip(),
                }
            ],
            columns=data.columns,
        )
        conn.update(
            worksheet=WORKSHEET,
            data=pd.concat([data, new_row], ignore_index=True),
        )
        st.success(f"Added {description.strip()} to the expense register.")
        st.rerun()
