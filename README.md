# Streamlit-app

This application records expenses in Google Sheets and stores optional receipt files in Google Drive.

## Receipt uploads

1. Create a **Shared Drive** and an `Expense Receipts` folder inside it. A normal folder in personal My Drive will fail because service accounts do not have personal Drive storage quota.
2. Add the service-account email from the `client_email` secret as a Contributor or Content manager on the Shared Drive.
3. Copy the receipt folder ID from the Drive URL.
4. Add the folder ID to `.streamlit/secrets.toml`:

```toml
[connections.gsheets]
receipt_folder_id = "your-google-drive-folder-id"
```

The Google Drive API must be enabled for the same Google Cloud project as the service account. The app saves the uploaded file's shareable Drive URL in the worksheet's `Receipt` column. Shared Drive administrators may need to allow link sharing for the app's permission step to succeed.
