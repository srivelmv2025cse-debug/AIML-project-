# AI-Powered Sales Forecasting and Business Analytics Using Machine Learning

Day 1 establishes the Flask application foundation and navigation UI. Day 2 adds secure data upload and preprocessing. Days 3–5 add data-backed business analytics, sales forecasting, and simulated scenario analysis. Day 6 adds customer segmentation and churn-risk modeling. Report generation is not implemented.

## Project Structure

```text
.
|-- app.py
|-- requirements.txt
|-- README.md
|-- data/
|   |-- uploads/
|   |-- processed/
|   `-- sample/sample_sales.csv
|-- database/
|   |-- database.py
|   `-- sales_forecasting.db  (created on first run)
|-- models/
|-- services/
|   |-- analytics.py
|   |-- customer_analytics.py
|   |-- data_processing.py
|   `-- forecasting.py
|-- static/
|   |-- css/style.css
|   `-- js/app.js
|-- templates/
    |-- base.html
    |-- dashboard.html
   |-- customer_analytics.html
   |-- forecasting.html
    |-- home.html
   |-- page.html
   `-- upload_data.html
`-- tests/
   `-- test_customer_analytics.py
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

If the cleaned dataset does not contain a mapped date or sales/revenue field, the pages show a clear data requirement message. Customer analytics is covered in Day 6 below.

## Day 4 Sales Forecasting

The **Forecasting** page prepares the latest cleaned uploaded dataset by aggregating sales daily, weekly, or monthly. It uses ARIMA through `statsmodels` when enough historical observations are available, evaluates the model with MAE, RMSE, and MAPE on a holdout period, and displays historical and predicted sales together. Prophet is detected and used only when already available in the environment; otherwise it is listed as skipped without breaking the application. Successful forecasts are saved to `data/processed/forecast_results.json` and the Dashboard displays the saved forecast total.

The sample dataset has only five dated rows, so it correctly shows an insufficient-history message instead of producing fake predictions. Forecasting does not include report generation.

## Day 5 Advanced And Scenario Forecasting

The Forecasting page compares ARIMA, Prophet, and an optional TensorFlow/Keras LSTM when each backend is installed and has enough history. LSTM requires at least 30 aggregated observations; all models use a holdout window for MAE, RMSE, and MAPE. The ensemble is the mean of forecasts from models that successfully trained, with its own holdout metrics. Missing libraries, training failures, and small datasets are shown as skipped/unavailable without crashing or fabricating an ensemble.

Install TensorFlow separately in an environment supported by TensorFlow to enable LSTM (`pip install tensorflow`). Prophet remains optional. The page lets users change demand increase/decrease, price change, and promotion-effect assumptions and charts Best, Expected, and Worst Case paths. These are explicitly simulated scenarios derived from the ensemble, not model forecasts, accuracy claims, or guarantees. A successful ensemble is saved to `data/processed/forecast_results.json` and shown on the Dashboard.

The bundled sample still has only five rows and does not meet the forecasting minimums, so the application correctly reports insufficient history instead of showing invented predictions. Report generation remains out of scope.

## Day 6 Customer Analytics

The **Customers** page uses the latest cleaned upload when it contains customer and transaction fields. It calculates per-customer recency, purchase frequency, monetary value, average order value, and quantity, then standardizes the varying features and selects between two and five K-Means clusters using silhouette scoring. Cluster sizes, median characteristics, value-based descriptions, and an average-order-value versus recency plot are shown on the page. The Dashboard adds a segment-size chart when customer segments are available.

Churn risk uses two classifiers: Logistic Regression and Random Forest. Training labels are derived only from historical snapshots with a complete 90-day forward window; a customer is labeled inactive when no purchase appears during that window. The page shows low (<33%), medium (33–<67%), and high (>=67%) probability bands, each model's counts, combined customer probabilities, and feature factors learned by both models. Training is withheld unless there are at least 20 snapshots across five customers and both historical outcomes. Missing fields, insufficient history, or single-class history produce an explanation instead of fabricated scores. Quantity is omitted when it has no variation or is unavailable.

The bundled `sample_sales.csv` contains customer names and can produce K-Means segments for its four customers; its five rows do not provide enough history for churn training, so churn remains unavailable. Tests also use a deterministic in-memory customer transaction history in `tests/test_customer_analytics.py` to exercise both churn models, K-Means, and missing/insufficient-data behavior:

```powershell
python -m unittest discover -s tests -p "test_customer_analytics.py"
```

To see customer results in the app, upload and clean a transaction file with a customer ID or name, a transaction date, and a sales/revenue/amount field. Unit price can be used only when quantity is also present; quantity and order ID improve the derived features when available.

## Git Commands

```powershell
git status
git add .
git commit -m "DAY 6 — CUSTOMER ANALYTICS"
git push origin main
```

The repository is already connected to `origin` on `main`.
