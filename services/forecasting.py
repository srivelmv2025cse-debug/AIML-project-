import json
from pathlib import Path

import numpy as np
import pandas as pd

from services.analytics import _column_map, latest_cleaned_dataset

try:
    from statsmodels.tsa.arima.model import ARIMA
except ImportError:
    ARIMA = None

try:
    from prophet import Prophet
except ImportError:
    Prophet = None


MIN_HISTORY_POINTS = 8
AGGREGATIONS = {"daily": "D", "weekly": "W", "monthly": "MS"}


def _metrics(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    errors = actual - predicted
    non_zero = actual != 0
    return {
        "mae": round(float(np.mean(np.abs(errors))), 2),
        "rmse": round(float(np.sqrt(np.mean(errors ** 2))), 2),
        "mape": round(float(np.mean(np.abs(errors[non_zero] / actual[non_zero])) * 100), 2) if non_zero.any() else None,
    }


def prepare_series(dataframe, aggregation):
    columns = _column_map(dataframe)
    if not columns.get("date") or not columns.get("sales"):
        return None, "The cleaned dataset needs a date column and a sales or revenue column for forecasting."
    frame = dataframe[[columns["date"], columns["sales"]]].copy()
    frame.columns = ["date", "sales"]
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["sales"] = pd.to_numeric(frame["sales"], errors="coerce")
    frame = frame.dropna().set_index("date").sort_index()
    if frame.empty:
        return None, "The cleaned dataset has no valid dated sales rows for forecasting."
    frequency = AGGREGATIONS[aggregation]
    series = frame["sales"].resample(frequency).sum()
    if len(series) < MIN_HISTORY_POINTS:
        return None, f"At least {MIN_HISTORY_POINTS} {aggregation} observations are required; this dataset has {len(series)}."
    return series, None


def _arima(series, horizon):
    if ARIMA is None:
        return {"name": "ARIMA", "available": False, "error": "statsmodels is not installed in this environment."}
    holdout = max(2, min(horizon, len(series) // 4))
    train, test = series.iloc[:-holdout], series.iloc[-holdout:]
    try:
        validation_model = ARIMA(train, order=(1, 1, 1), enforce_stationarity=False, enforce_invertibility=False).fit()
        validation_prediction = validation_model.forecast(steps=holdout)
        model = ARIMA(series, order=(1, 1, 1), enforce_stationarity=False, enforce_invertibility=False).fit()
        forecast = model.forecast(steps=horizon)
    except Exception as error:
        return {"name": "ARIMA", "available": False, "error": f"ARIMA could not fit this series: {error}"}
    return {
        "name": "ARIMA",
        "available": True,
        "metrics": _metrics(test, validation_prediction),
        "forecast": {"labels": [date.strftime("%Y-%m-%d") for date in forecast.index], "values": [round(max(float(value), 0), 2) for value in forecast]},
    }


def _prophet(series, horizon, aggregation):
    if Prophet is None:
        return {"name": "Prophet", "available": False, "error": "Prophet is not installed; it was skipped safely."}
    holdout = max(2, min(horizon, len(series) // 4))
    train = series.iloc[:-holdout].reset_index()
    train.columns = ["ds", "y"]
    test = series.iloc[-holdout:]
    try:
        validation_model = Prophet(yearly_seasonality=False, weekly_seasonality=False, daily_seasonality=False).fit(train)
        validation_prediction = validation_model.predict(pd.DataFrame({"ds": test.index}))["yhat"]
        model = Prophet(yearly_seasonality=False, weekly_seasonality=False, daily_seasonality=False).fit(series.reset_index().rename(columns={"date": "ds", "sales": "y"}))
        future = model.make_future_dataframe(periods=horizon, freq=AGGREGATIONS[aggregation], include_history=False)
        forecast = model.predict(future)
    except Exception as error:
        return {"name": "Prophet", "available": False, "error": f"Prophet could not fit this series: {error}"}
    return {
        "name": "Prophet",
        "available": True,
        "metrics": _metrics(test, validation_prediction),
        "forecast": {"labels": [date.strftime("%Y-%m-%d") for date in forecast["ds"]], "values": [round(max(float(value), 0), 2) for value in forecast["yhat"]]},
    }


def forecast_dataset(dataframe, aggregation="monthly", horizon=3):
    aggregation = aggregation if aggregation in AGGREGATIONS else "monthly"
    try:
        horizon = max(1, min(int(horizon), 90))
    except (TypeError, ValueError):
        horizon = 3
    series, error = prepare_series(dataframe, aggregation)
    if error:
        return {"error": error, "aggregation": aggregation, "horizon": horizon}
    models = [_arima(series, horizon), _prophet(series, horizon, aggregation)]
    available = [model for model in models if model["available"]]
    if not available:
        return {"error": "No forecasting model is available. " + " ".join(model["error"] for model in models), "aggregation": aggregation, "horizon": horizon, "models": models}
    best = min(available, key=lambda model: model["metrics"]["mae"])
    return {
        "error": None,
        "aggregation": aggregation,
        "horizon": horizon,
        "historical": {"labels": [date.strftime("%Y-%m-%d") for date in series.index], "values": [round(float(value), 2) for value in series.values]},
        "models": models,
        "best_model": best["name"],
        "forecast": best["forecast"],
    }


def latest_forecast(processed_dir, aggregation="monthly", horizon=3):
    _path, dataframe = latest_cleaned_dataset(processed_dir)
    if dataframe is None:
        return {"error": "Upload and clean a dataset to create a sales forecast."}
    return forecast_dataset(dataframe, aggregation, horizon)


def save_forecast(result, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")


def load_forecast(processed_dir):
    path = Path(processed_dir) / "forecast_results.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
