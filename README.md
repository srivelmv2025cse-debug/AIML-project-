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

## Day 3 Business Analytics

The Dashboard and Analytics pages now load the newest cleaned CSV from `data/processed/`. They calculate total sales, orders, customers, products, average order value, and month-over-month sales growth. Chart.js renders daily, monthly, product, category, and regional sales charts. The analytics view also reports increasing, decreasing, or stable trends, monthly and (when enough dates exist) weekly patterns, generated insights, and daily anomalies detected with Isolation Forest.

If the cleaned dataset does not contain a mapped date or sales/revenue field, the pages show a clear data requirement message. Forecasting and customer ML modules remain reserved for later days.

## Day 4 Sales Forecasting

The **Forecasting** page prepares the latest cleaned uploaded dataset by aggregating sales daily, weekly, or monthly. It uses ARIMA through `statsmodels` when enough historical observations are available, evaluates the model with MAE, RMSE, and MAPE on a holdout period, and displays historical and predicted sales together. Prophet is detected and used only when already available in the environment; otherwise it is listed as skipped without breaking the application. Successful forecasts are saved to `data/processed/forecast_results.json` and the Dashboard displays the saved forecast total.

The sample dataset has only five dated rows, so it correctly shows an insufficient-history message instead of producing fake predictions. Forecasting does not include LSTM, customer segmentation, churn prediction, or report generation.

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
