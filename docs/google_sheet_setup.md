# Google Sheet setup (curriculum MCP source)

Import the CSV files in `config/` into a Google Sheet with two tabs.

## Steps

1. Go to [Google Sheets](https://sheets.google.com) → **Blank spreadsheet**.
2. Rename tab 1 to **`cohort_tracker`**.
3. **File → Import → Upload** → select `config/cohort_tracker.csv` → **Replace current sheet**.
4. Add tab 2 named **`mentor_strengths`**.
5. **File → Import → Upload** → select `config/mentor_strengths.csv` → import into `mentor_strengths` tab.
6. **Share → Anyone with the link → Viewer** (required for CSV export).
7. Copy the sheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit
   ```
8. Add to `.env`:
   ```sh
   GOOGLE_SHEET_ID=SHEET_ID_HERE
   ```

Kusoma reads live data via the public CSV export URLs (same rows as `config/sandbox_members.json`).

If `GOOGLE_SHEET_ID` is not set, the app falls back to `config/sandbox_members.json`.

## Demo tip

Keep the sheet open in a browser tab during `/kusoma scan` so judges see external curriculum ground truth.
