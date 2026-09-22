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


with st.form("add_expense", clear_on_submit=True):
    expense_date = st.date_input("Date", value=date.today())
    category = st.selectbox(
        "Category",
        options_for("Category", ["Other"]),
    )
    subcategory = st.text_input("Subcategory")
    enterprise = st.selectbox(
        "Enterprise",
        options_for("Enterprise", ["Other"]),
    )
    description = st.text_input("Description")
    supplier = st.text_input("Supplier")
    quantity = st.number_input("Quantity", min_value=0.0, value=1.0, step=1.0)
    unit = st.text_input("Unit", placeholder="e.g. kg, item, litre")
    unit_cost = st.number_input("Unit cost", min_value=0.0, step=0.01, format="%.2f")
    payment_method = st.selectbox(
        "Payment method",
        options_for("Payment Method", ["Cash", "Bank", "Other"]),
    )
    paid_by = st.selectbox(
        "Paid by",
        options_for("Paid By", ["Other"]),
    )
    receipt = st.text_input("Receipt", placeholder="Optional receipt URL or reference")
    recurring = st.selectbox("Recurring", ["No", "Yes"])
    priority = st.selectbox("Priority", ["High", "Med", "Low"])
    budgeted = st.selectbox("Budgeted", ["Yes", "No"])
    tax = st.number_input("Tax", min_value=0.0, step=0.01, format="%.2f")
    notes = st.text_area("Notes")
    total_cost = quantity * unit_cost
    st.caption(f"Total cost: {total_cost:,.2f}")
    submitted = st.form_submit_button(
        "Add expense",
        type="primary",
        icon=":material/add:",
    )

if submitted:
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
                    "Receipt": receipt.strip(),
                    "Recurring": recurring,
                    "Priority": priority,
                    "Budgeted": budgeted,
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
