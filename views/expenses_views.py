import re
from datetime import date, datetime

import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection


WORKSHEET = "Expense Register"
conn = st.connection("gsheets", type=GSheetsConnection)
data = conn.read(worksheet=WORKSHEET)
COLUMNS = list(data.columns)


def normalized(column: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(column).lower()).strip()


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
    if "Expense ID" not in data.columns:
        return ""
    numbers = [
        int(match.group(1))
        for value in data["Expense ID"].dropna()
        if (match := re.fullmatch(r"EXP(\d+)", str(value).strip()))
    ]
    return f"EXP{max(numbers, default=0) + 1:04d}"


def is_column(column: str, *names: str) -> bool:
    return normalized(column) in {normalized(name) for name in names}


def ordered_columns() -> list[str]:
    groups = [
        ("Expense ID", "ID"),
        ("Date",),
        ("Category",),
        ("Subcategory",),
        ("Enterprise",),
        ("Description",),
        ("Supplier",),
        ("Qty", "Quantity"),
        ("Unit",),
        ("Unit Cost",),
        ("Total Cost",),
        ("Payment Method",),
        ("Paid By",),
        ("Receipt",),
        ("Recurring",),
        ("Priority",),
        ("Budgeted",),
        ("Tax",),
        ("Notes",),
    ]
    ordered = []
    for group in groups:
        ordered.extend(
            column
            for column in COLUMNS
            if column not in ordered and is_column(column, *group)
        )
    ordered.extend(column for column in COLUMNS if column not in ordered)
    return ordered


def render_field(column: str, position: int) -> object:
    key = f"expense_{position}_{normalized(column).replace(' ', '_')}"
    name = normalized(column)

    if is_column(column, "Expense ID"):
        return st.text_input(column, value=next_expense_id(), disabled=True, key=key)
    if is_column(column, "Date") or name.endswith(" date"):
        return st.date_input(column, value=date.today(), key=key)
    if is_column(column, "Category", "Subcategory", "Enterprise", "Payment Method", "Paid By", "Unit"):
        fallback = ["Other"]
        if is_column(column, "Payment Method"):
            fallback = ["Cash", "Bank", "Other"]
        elif is_column(column, "Unit"):
            fallback = ["Item", "Kg", "Litre"]
        return st.selectbox(column, options_for(column, fallback), key=key)
    if is_column(column, "Recurring", "Budgeted"):
        return st.checkbox(column, key=key)
    if is_column(column, "Priority"):
        return st.selectbox(column, ["High", "Med", "Low"], key=key)
    if is_column(column, "Receipt"):
        receipt = st.file_uploader(
            "Upload receipt",
            type=["pdf", "png", "jpg", "jpeg"],
            key=key,
        )
        return receipt.name if receipt else ""
    if is_column(column, "Tax") or name in {"qty", "quantity", "unit cost"}:
        return st.number_input(column, min_value=0.0, step=0.01, format="%.2f", key=key)

    series = data[column].dropna()
    if pd.api.types.is_numeric_dtype(series):
        return st.number_input(column, min_value=0.0, step=0.01, key=key)
    if pd.api.types.is_datetime64_any_dtype(series):
        return st.date_input(column, value=date.today(), key=key)

    values = sorted({str(value).strip() for value in series if str(value).strip()})
    if 0 < len(values) <= 12:
        return st.selectbox(column, ["Other", *values], key=key)
    return st.text_area(column, key=key) if "note" in name or "comment" in name else st.text_input(column, key=key)


def prepare_value(column: str, value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return value


st.title("Add new expense", text_alignment="center")
st.caption("Log farm expenses with priority and budget tracking.", text_alignment="center")

with st.form("add_expense", clear_on_submit=True, border=True):
    values: dict[str, object] = {}
    form_columns = ordered_columns()
    for start in range(0, len(form_columns), 3):
        row_columns = st.columns(min(3, len(form_columns) - start))
        for position, column in enumerate(form_columns[start : start + 3]):
            with row_columns[position]:
                if is_column(column, "Total Cost"):
                    quantity_column = next(
                        (name for name in COLUMNS if is_column(name, "Qty", "Quantity")),
                        None,
                    )
                    unit_cost_column = next(
                        (name for name in COLUMNS if is_column(name, "Unit Cost")),
                        None,
                    )
                    calculated_total = (
                        float(values.get(quantity_column) or 0)
                        * float(values.get(unit_cost_column) or 0)
                        if quantity_column and unit_cost_column
                        else 0.0
                    )
                    values[column] = st.number_input(
                        column,
                        value=calculated_total,
                        min_value=0.0,
                        step=0.01,
                        format="%.2f",
                        key=f"expense_total_{normalized(column)}",
                        help="Calculated from quantity and unit cost; you can adjust it if needed.",
                    )
                else:
                    values[column] = render_field(column, start + position)

    submitted = st.form_submit_button("Save expense", type="primary", icon=":material/save:")
    clear_form = st.form_submit_button("Clear form", icon=":material/ink_eraser:")
    cancelled = st.form_submit_button("Cancel", icon=":material/close:")

if cancelled:
    st.info("Expense entry cancelled.")
elif clear_form:
    st.info("Form cleared. Enter a new expense when ready.")
elif submitted:
    description_column = next((column for column in COLUMNS if is_column(column, "Description")), None)
    quantity_column = next((column for column in COLUMNS if is_column(column, "Qty", "Quantity")), None)
    unit_cost_column = next((column for column in COLUMNS if is_column(column, "Unit Cost")), None)
    errors = []
    if description_column and not str(values.get(description_column, "")).strip():
        errors.append("Enter a description before adding the expense.")
    if quantity_column and float(values.get(quantity_column) or 0) <= 0:
        errors.append("Quantity must be greater than zero.")
    if unit_cost_column and float(values.get(unit_cost_column) or 0) <= 0:
        errors.append("Unit cost must be greater than zero.")

    if errors:
        for error in errors:
            st.error(error)
    else:
        row = {column: prepare_value(column, values.get(column, "")) for column in COLUMNS}
        total_column = next(
            (column for column in COLUMNS if is_column(column, "Total Cost")),
            None,
        )
        if total_column and quantity_column and unit_cost_column:
            row[total_column] = float(values[quantity_column]) * float(values[unit_cost_column])
        conn.update(
            worksheet=WORKSHEET,
            data=pd.concat([data, pd.DataFrame([row], columns=COLUMNS)], ignore_index=True),
        )
        label = values.get(description_column, "expense") if description_column else "expense"
        st.success(f"Added {str(label).strip() or 'expense'} to the expense register.")
        st.rerun()
