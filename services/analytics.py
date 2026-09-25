from pathlib import Path

import pandas as pd
from sklearn.ensemble import IsolationForest

from services.data_processing import detect_columns, read_dataset


REQUIRED_FIELDS = {
    "date": "a date column",
    "sales": "a sales or revenue column",
}


def latest_cleaned_dataset(processed_dir):
    files = sorted(Path(processed_dir).glob("cleaned_*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not files:
        return None, None
    path = files[0]
    return path, read_dataset(path, "csv")


def _column_map(dataframe):
    detected = detect_columns(dataframe.columns)
    aliases = {
        "order": ("order_id", "order", "transaction_id", "invoice_id"),
        "customer": ("customer_id", "customer_name", "customer"),
        "sales": ("sales", "total_amount", "revenue", "amount", "net_sales"),
    }
    for field, candidates in aliases.items():
        if not detected.get(field):
            detected[field] = next((column for column in dataframe.columns if any(candidate in str(column).lower() for candidate in candidates)), None)
    return detected


def _required_message(detected):
    missing = [description for field, description in REQUIRED_FIELDS.items() if not detected.get(field)]
    if missing:
        return "The cleaned dataset needs " + " and ".join(missing) + " to build analytics. Map those fields during upload."
    return None


def _format_number(value, decimals=0):
    if pd.isna(value):
        return 0
    return round(float(value), decimals)


def _trend(values):
    if len(values) < 2:
        return "Stable"
    first = float(values.iloc[0])
    last = float(values.iloc[-1])
    average = max(float(values.mean()), 1)
    change = (last - first) / average
    if change > 0.05:
        return "Increasing"
    if change < -0.05:
        return "Decreasing"
    return "Stable"


def _series(dataframe, group_column, sales_column):
    grouped = dataframe.groupby(group_column, dropna=False)[sales_column].sum().sort_values(ascending=False).head(12)
    return {"labels": [str(label) for label in grouped.index], "values": [_format_number(value, 2) for value in grouped.values]}


def _anomalies(daily):
    if len(daily) < 5:
        return []
    model = IsolationForest(contamination="auto", random_state=42)
    flags = model.fit_predict(daily[["sales"]])
    return [
        {"date": row.date.strftime("%Y-%m-%d"), "sales": _format_number(row.sales, 2)}
        for row, flag in zip(daily.itertuples(index=False), flags)
        if flag == -1
    ]


def analyze_dataset(dataframe):
    detected = _column_map(dataframe)
    message = _required_message(detected)
    if message:
        return {"error": message, "detected": detected}

    frame = dataframe.copy()
    date_column = detected["date"]
    sales_column = detected["sales"]
    frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
    frame[sales_column] = pd.to_numeric(frame[sales_column], errors="coerce").fillna(0)
    frame = frame.dropna(subset=[date_column]).sort_values(date_column)
    if frame.empty:
        return {"error": "The cleaned dataset has no valid dates to analyze.", "detected": detected}

    daily = frame.groupby(date_column, as_index=False)[sales_column].sum().rename(columns={date_column: "date", sales_column: "sales"})
    daily["date"] = pd.to_datetime(daily["date"])
    monthly = daily.assign(period=daily["date"].dt.to_period("M")).groupby("period", as_index=False)["sales"].sum()
    monthly["label"] = monthly["period"].astype(str)

    unique_orders = frame[detected["order"]].nunique() if detected.get("order") else len(frame)
    unique_customers = frame[detected["customer"]].nunique() if detected.get("customer") else None
    unique_products = frame[detected["product"]].nunique() if detected.get("product") else None
    previous_sales = monthly.iloc[-2]["sales"] if len(monthly) > 1 else None
    latest_sales = monthly.iloc[-1]["sales"]
    growth = ((latest_sales - previous_sales) / previous_sales * 100) if previous_sales not in (None, 0) else None

    product_series = _series(frame, detected["product"], sales_column) if detected.get("product") else None
    category_series = _series(frame, detected["category"], sales_column) if detected.get("category") else None
    region_series = _series(frame, detected["region"], sales_column) if detected.get("region") else None
    weekly = frame.assign(weekday=frame[date_column].dt.day_name()).groupby("weekday")[sales_column].sum()
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekly = weekly.reindex([day for day in weekday_order if day in weekly.index])

    insights = []
    if product_series and product_series["labels"]:
        insights.append(f"{product_series['labels'][0]} generated the highest revenue.")
    if category_series and category_series["labels"]:
        insights.append(f"{category_series['labels'][0]} was the strongest category by sales.")
    insights.append(f"Sales show a {_trend(monthly['sales']).lower()} trend across the available periods.")

    return {
        "detected": detected,
        "metrics": {
            "total_sales": _format_number(frame[sales_column].sum(), 2),
            "total_orders": int(unique_orders),
            "total_customers": int(unique_customers) if unique_customers is not None else None,
            "total_products": int(unique_products) if unique_products is not None else None,
            "average_order_value": _format_number(frame[sales_column].sum() / unique_orders, 2) if unique_orders else 0,
            "sales_growth": _format_number(growth, 1) if growth is not None else None,
        },
        "charts": {
            "daily": {"labels": [date.strftime("%Y-%m-%d") for date in daily["date"]], "values": [_format_number(value, 2) for value in daily["sales"]]},
            "monthly": {"labels": monthly["label"].tolist(), "values": [_format_number(value, 2) for value in monthly["sales"]]},
            "product": product_series,
            "category": category_series,
            "region": region_series,
            "weekly": {"labels": weekly.index.tolist(), "values": [_format_number(value, 2) for value in weekly.values]} if len(weekly) >= 3 else None,
        },
        "trend": _trend(monthly["sales"]),
        "seasonality": "Monthly pattern available" if len(monthly) >= 2 else "Not enough monthly data",
        "weekly_seasonality": "Weekly pattern available" if len(weekly) >= 3 else "Not enough weekly data",
        "anomalies": _anomalies(daily),
        "insights": insights,
    }