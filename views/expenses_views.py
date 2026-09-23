import re
import io
from datetime import date, datetime

import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
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


@st.cache_resource
def drive_service():
    gsheets_secrets = dict(st.secrets["connections"]["gsheets"])
    credentials = service_account.Credentials.from_service_account_info(
        gsheets_secrets,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def upload_receipt(uploaded_file: object) -> str:
    if uploaded_file is None:
        return ""

    folder_id = str(
        st.secrets["connections"]["gsheets"].get("receipt_folder_id", "")
    ).strip()
    if not folder_id:
        raise RuntimeError(
            "Receipt uploads require connections.gsheets.receipt_folder_id "
            "in .streamlit/secrets.toml."
        )

    file_metadata = {
        "name": uploaded_file.name,
        "parents": [folder_id],
    }
    media = MediaIoBaseUpload(
        io.BytesIO(uploaded_file.getvalue()),
        mimetype=uploaded_file.type or "application/octet-stream",
        resumable=False,
    )
    service = drive_service()
    uploaded = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id,webViewLink")
        .execute()
    )
    service.permissions().create(
        fileId=uploaded["id"],
        body={"type": "anyone", "role": "reader"},
        fields="id",
    ).execute()
    return uploaded.get(
        "webViewLink",
        f"https://drive.google.com/file/d/{uploaded['id']}/view",
    )


st.title("Add new expense", text_alignment="center")
st.caption("Log farm expenses with priority and budget tracking.", text_alignment="center")

with st.form("add_expense", clear_on_submit=True, border=True):
    values: dict[str, object] = {}
    field_position = [0]

    def render_row(row: list[str]) -> None:
        row_columns = st.columns(len(row))
        for position, column in enumerate(row):
            with row_columns[position]:
                values[column] = render_field(column, field_position[0])
                field_position[0] += 1

    def render_total() -> None:
        total_column = next(
            (column for column in COLUMNS if is_column(column, "Total Cost")),
            None,
        )
        if not total_column:
            return
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
        values[total_column] = st.number_input(
            total_column,
            value=calculated_total,
            min_value=0.0,
            step=0.01,
            format="%.2f",
            key="expense_total",
            help="Calculated from quantity and unit cost.",
        )
        field_position[0] += 1

    visible_columns = [
        column for column in ordered_columns() if not is_column(column, "Expense ID")
    ]

    identity_row = [
        column
        for column in ("Date", "Category", "Subcategory")
        if column in COLUMNS
    ]
    if identity_row:
        st.subheader("Expense details")
        render_row(identity_row)

    description_row = [
        column
        for column in ("Enterprise", "Description", "Supplier")
        if column in COLUMNS
    ]
    if description_row:
        render_row(description_row)

    cost_columns = [
        column
        for column in ("Qty", "Quantity", "Unit", "Unit Cost")
        if column in COLUMNS
    ]
    if cost_columns:
        st.subheader("Cost details")
        render_row(cost_columns)
        render_total()

    payment_row = [
        column
        for column in ("Payment Method", "Paid By", "Receipt")
        if column in COLUMNS
    ]
    if payment_row:
        st.subheader("Payment details")
        render_row(payment_row)

    controls_row = [
        column
        for column in ("Recurring", "Priority", "Budgeted", "Tax")
        if column in COLUMNS
    ]
    if controls_row:
        st.subheader("Tracking")
        render_row(controls_row)

    notes_columns = [
        column for column in COLUMNS if is_column(column, "Notes") and column not in values
    ]
    if notes_columns:
        render_row(notes_columns)

    rendered_columns = set(values)
    extra_columns = [
        column
        for column in visible_columns
        if column not in rendered_columns and not is_column(column, "Total Cost")
    ]
    if extra_columns:
        with st.expander("Additional fields", expanded=False):
            for start in range(0, len(extra_columns), 3):
                render_row(extra_columns[start : start + 3])

    st.space("small")
    action_columns = st.columns([2, 1, 1], gap="medium")
    with action_columns[0]:
        submitted = st.form_submit_button(
            "Save expense",
            type="primary",
            icon=":material/save:",
            width="stretch",
        )
    with action_columns[1]:
        clear_form = st.form_submit_button(
            "Clear form",
            icon=":material/ink_eraser:",
            width="stretch",
        )
    with action_columns[2]:
        cancelled = st.form_submit_button(
            "Cancel",
            icon=":material/close:",
            width="stretch",
        )

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
        receipt_column = next(
            (column for column in COLUMNS if is_column(column, "Receipt")),
            None,
        )
        if receipt_column and values.get(receipt_column):
            try:
                row[receipt_column] = upload_receipt(values[receipt_column])
            except Exception as error:
                st.error(f"Receipt upload failed: {error}")
                st.stop()
        id_column = next(
            (column for column in COLUMNS if is_column(column, "Expense ID", "ID")),
            None,
        )
        if id_column:
            row[id_column] = next_expense_id()
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
