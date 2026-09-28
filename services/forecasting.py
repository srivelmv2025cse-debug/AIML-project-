import json
from pathlib import Path

import numpy as np
import pandas as pd

from services.analytics import _column_map, latest_cleaned_dataset

try:
    from statsmodels.tsa.arima.model import ARIMA
except Exception:
    ARIMA = None

try:
    from prophet import Prophet
except Exception:
    Prophet = None


MIN_HISTORY_POINTS = 8
MIN_LSTM_HISTORY_POINTS = 30
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


def _validation_horizon(series, horizon):
    return max(2, min(horizon, len(series) // 4))


def _lstm_predict(training_values, steps):
    import tensorflow as tf
    from sklearn.preprocessing import MinMaxScaler

    tf.keras.utils.set_random_seed(42)
    values = np.asarray(training_values, dtype=float).reshape(-1, 1)
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(values)
    lookback = min(14, max(3, len(values) // 5))
    inputs = np.array([scaled[index - lookback:index, 0] for index in range(lookback, len(scaled))])
    targets = scaled[lookback:, 0]
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(lookback, 1)),
        tf.keras.layers.LSTM(16),
        tf.keras.layers.Dense(1),
    ])
    model.compile(optimizer="adam", loss="mean_squared_error")
    model.fit(inputs.reshape((-1, lookback, 1)), targets, epochs=25, batch_size=min(16, len(inputs)), verbose=0)
    window = scaled[-lookback:, 0].copy()
    predictions = []
    for _ in range(steps):
        predicted = float(model.predict(window.reshape((1, lookback, 1)), verbose=0)[0, 0])
        predictions.append(predicted)
        window = np.append(window[1:], predicted)
    return scaler.inverse_transform(np.asarray(predictions).reshape(-1, 1)).ravel()


def _lstm(series, horizon):
    if len(series) < MIN_LSTM_HISTORY_POINTS:
        return {"name": "LSTM", "available": False, "error": f"At least {MIN_LSTM_HISTORY_POINTS} observations are required; this dataset has {len(series)}."}
    try:
        import tensorflow
    except Exception as error:
        return {"name": "LSTM", "available": False, "error": f"TensorFlow is unavailable: {error}"}
    holdout = _validation_horizon(series, horizon)
    train, test = series.iloc[:-holdout], series.iloc[-holdout:]
    try:
        validation_prediction = _lstm_predict(train.values, holdout)
        forecast_values = _lstm_predict(series.values, horizon)
    except Exception as error:
        return {"name": "LSTM", "available": False, "error": f"LSTM training failed safely: {error}"}
    future_index = pd.date_range(start=series.index[-1], periods=horizon + 1, freq=series.index.freq)[1:]
    return {
        "name": "LSTM",
        "available": True,
        "metrics": _metrics(test.values, validation_prediction),
        "forecast": {"labels": [date.strftime("%Y-%m-%d") for date in future_index], "values": [round(max(float(value), 0), 2) for value in forecast_values]},
        "_validation_predictions": [float(value) for value in validation_prediction],
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
    holdout = _validation_horizon(series, horizon)
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
        "_validation_predictions": [float(value) for value in validation_prediction],
    }


def _prophet(series, horizon, aggregation):
    if Prophet is None:
        return {"name": "Prophet", "available": False, "error": "Prophet is not installed; it was skipped safely."}
    holdout = _validation_horizon(series, horizon)
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
        "_validation_predictions": [float(value) for value in validation_prediction],
    }


def _assumption_values(assumptions):
    defaults = {"demand_increase": 10.0, "demand_decrease": 10.0, "price_change": 0.0, "promotion_effect": 5.0}
    bounds = {"demand_increase": (0, 100), "demand_decrease": (0, 100), "price_change": (-100, 100), "promotion_effect": (0, 100)}
    values = {}
    for name, default in defaults.items():
        try:
            value = float((assumptions or {}).get(name, default))
        except (TypeError, ValueError):
            value = default
        values[name] = min(max(value, bounds[name][0]), bounds[name][1])
    return values


def _scenarios(ensemble_values, assumptions):
    demand_up = assumptions["demand_increase"] / 100
    demand_down = assumptions["demand_decrease"] / 100
    price_change = assumptions["price_change"] / 100
    promotion = assumptions["promotion_effect"] / 100
    multipliers = {
        "Best Case": (1 + demand_up) * (1 + promotion) * (1 + price_change),
        "Expected Case": (1 + (demand_up - demand_down) / 2) * (1 + promotion / 2) * (1 + price_change),
        "Worst Case": (1 - demand_down) * (1 + min(price_change, 0)),
    }
    return {
        name: [round(max(float(value) * multiplier, 0), 2) for value in ensemble_values]
        for name, multiplier in multipliers.items()
    }


def forecast_dataset(dataframe, aggregation="monthly", horizon=3, assumptions=None):
    aggregation = aggregation if aggregation in AGGREGATIONS else "monthly"
    try:
        horizon = max(1, min(int(horizon), 90))
    except (TypeError, ValueError):
        horizon = 3
    series, error = prepare_series(dataframe, aggregation)
    if error:
        return {"error": error, "aggregation": aggregation, "horizon": horizon}
    models = [_arima(series, horizon), _prophet(series, horizon, aggregation), _lstm(series, horizon)]
    available = [model for model in models if model["available"]]
    if not available:
        return {"error": "No forecasting model is available. " + " ".join(model["error"] for model in models), "aggregation": aggregation, "horizon": horizon, "models": models}
    validation_horizon = _validation_horizon(series, horizon)
    validation_values = np.mean([model["_validation_predictions"] for model in available], axis=0)
    ensemble_values = np.mean([model["forecast"]["values"] for model in available], axis=0)
    assumptions = _assumption_values(assumptions)
    scenario_values = _scenarios(ensemble_values, assumptions)
    labels = available[0]["forecast"]["labels"]
    public_models = [
        {key: value for key, value in model.items() if not key.startswith("_")}
        for model in models
    ]
    return {
        "error": None,
        "aggregation": aggregation,
        "horizon": horizon,
        "historical": {"labels": [date.strftime("%Y-%m-%d") for date in series.index], "values": [round(float(value), 2) for value in series.values]},
        "models": public_models,
        "best_model": "Ensemble",
        "ensemble_metrics": _metrics(series.iloc[-validation_horizon:].values, validation_values),
        "forecast": {"labels": labels, "values": [round(float(value), 2) for value in ensemble_values]},
        "assumptions": assumptions,
        "scenarios": {name: {"labels": labels, "values": values, "simulated": True} for name, values in scenario_values.items()},
    }


def latest_forecast(processed_dir, aggregation="monthly", horizon=3, assumptions=None):
    _path, dataframe = latest_cleaned_dataset(processed_dir)
    if dataframe is None:
        return {"error": "Upload and clean a dataset to create a sales forecast."}
    return forecast_dataset(dataframe, aggregation, horizon, assumptions)


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
