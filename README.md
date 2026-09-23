# Streamlit-app

This application records expenses in Google Sheets and stores optional receipt files in Google Drive.

## Receipt uploads

1. Create an `Expense Receipts` folder in the Google Drive account used for this app.
2. Share the folder with the service-account email from the `client_email` secret as an Editor.
3. Copy the folder ID from the Drive URL.
4. Add the folder ID to `.streamlit/secrets.toml`:

```toml
[connections.gsheets]
receipt_folder_id = "your-google-drive-folder-id"
```

The Google Drive API must be enabled for the same Google Cloud project as the service account. The app saves the uploaded file's shareable Drive URL in the worksheet's `Receipt` column.
