# AI-Powered Sales Forecasting and Business Analytics Using Machine Learning

Day 1 establishes the Flask application foundation and a clean navigation UI. Forecasting, segmentation, sentiment analysis, report generation, and other ML features are intentionally not implemented yet.

## Project Structure

```text
.
|-- app.py
|-- requirements.txt
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
    `-- page.html
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
