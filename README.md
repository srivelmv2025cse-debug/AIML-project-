# AI-Powered Sales Forecasting and Business Analytics Using Machine Learning

Day 1 establishes the Flask application foundation and a clean navigation UI. Day 2 adds a secure data upload and preprocessing workflow. Forecasting, segmentation, sentiment analysis, report generation, and other ML features are intentionally not implemented yet.

## Project Structure

```text
.
|-- app.py
|-- requirements.txt
|-- services/data_processing.py
|-- data/
|   |-- uploads/
|   |-- processed/
|   `-- sample/sample_sales.csv
|-- database/
|   |-- database.py
|   `-- sales_forecasting.db  (created on first run)
|-- models/
|-- services/
|-- static/
|   |-- css/style.css
|   `-- js/app.js
`-- templates/
    |-- base.html
    |-- dashboard.html
    |-- home.html
   |-- page.html
   `-- upload_data.html
```

## Run Locally

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Start Flask:

   ```powershell
   python app.py
   ```

4. Open `http://127.0.0.1:5000` in your browser.

## Day 2 Data Upload

Open **Upload Data** in the sidebar and upload a CSV, XLSX, or JSON dataset up to 10 MB. The application validates the file, stores the original with a generated safe name in `data/uploads/`, reads it with pandas, shows quality statistics and a 15-row preview, detects common sales fields, and provides a mapping form. Confirming the form removes duplicates, handles missing values, converts mapped dates and numeric fields, and saves a cleaned CSV in `data/processed/`.

Day 2 does not include forecasting, analytics dashboards, customer segmentation, sentiment analysis, or report generation.

## Git Commands

```powershell
git init
git add .
git commit -m "Day 1 - Project setup and basic UI"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

If Git is already initialized, skip `git init`. Replace `YOUR_GITHUB_REPOSITORY_URL` with the repository URL before pushing.
