import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import silhouette_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from services.data_processing import detect_columns, normalize_name


CHURN_HORIZON_DAYS = 90
MIN_CHURN_SNAPSHOTS = 20
MIN_CHURN_CUSTOMERS = 5
FEATURE_LABELS = {
    "recency_days": "Recency",
    "frequency": "Purchase frequency",
    "monetary_value": "Monetary value",
    "average_order_value": "Average order value",
    "quantity": "Quantity purchased",
}


def _find_column(columns, detected, field, aliases):
    if detected.get(field):
        return detected[field]
    normalized = {column: normalize_name(column) for column in columns}
    for alias in aliases:
        match = next((column for column, name in normalized.items() if name == alias), None)
        if match:
            return match
    for alias in aliases:
        match = next((column for column, name in normalized.items() if alias in name), None)
        if match:
            return match
    return None


def _resolve_columns(dataframe):
    detected = detect_columns(dataframe.columns)
    return {
        "customer": _find_column(dataframe.columns, detected, "customer_id", ("customer_id", "customer_name", "customer", "client_id", "client")),
        "date": _find_column(dataframe.columns, detected, "date", ("date", "order_date", "transaction_date", "invoice_date")),
        "amount": _find_column(dataframe.columns, detected, "sales", ("sales", "total_amount", "revenue", "amount", "net_sales", "transaction_value")),
        "price": _find_column(dataframe.columns, detected, "price", ("price", "unit_price")),
        "quantity": _find_column(dataframe.columns, detected, "quantity", ("quantity", "qty", "units")),
        "order": _find_column(dataframe.columns, detected, "order_id", ("order_id", "transaction_id", "invoice_id", "order")),
    }


def _prepare_transactions(dataframe, columns):
    if not columns["customer"]:
        return None, "Customer analytics needs a customer ID or customer name column in the cleaned dataset."
    if not columns["date"]:
        return None, "Customer analytics needs dated customer transactions to calculate recency and churn history."
    if not columns["amount"] and (not columns["price"] or not columns["quantity"]):
        return None, "Customer analytics needs a sales, revenue, or transaction amount column; unit price can be used only when quantity is also available."

    selected = [columns["customer"], columns["date"]]
    for field in ("amount", "price", "quantity", "order"):
        if columns[field] and columns[field] not in selected:
            selected.append(columns[field])
    frame = dataframe[selected].copy()
    frame = frame.rename(columns={columns["customer"]: "customer_id", columns["date"]: "date"})
    frame["customer_id"] = frame["customer_id"].astype("string").str.strip()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["customer_id", "date"])
    frame = frame[frame["customer_id"] != ""]

    if columns["amount"]:
        frame["amount"] = pd.to_numeric(frame[columns["amount"]], errors="coerce")
    else:
        frame["amount"] = pd.to_numeric(frame[columns["price"]], errors="coerce")
        if columns["quantity"]:
            frame["amount"] *= pd.to_numeric(frame[columns["quantity"]], errors="coerce")
    frame = frame.dropna(subset=["amount"])
    frame["quantity_value"] = (
        pd.to_numeric(frame[columns["quantity"]], errors="coerce").fillna(0)
        if columns["quantity"]
        else np.nan
    )
    frame["order_id"] = frame[columns["order"]].astype("string") if columns["order"] else pd.NA
    return frame, None


def _customer_features(transactions, reference_date):
    if transactions.empty:
        return pd.DataFrame(columns=["customer_id", *FEATURE_LABELS])
    grouped = transactions.groupby("customer_id", sort=True)
    result = grouped.agg(last_purchase=("date", "max"), monetary_value=("amount", "sum"))
    result["quantity"] = grouped["quantity_value"].sum(min_count=1)
    if transactions["order_id"].notna().any():
        identified = transactions.dropna(subset=["order_id"])
        order_counts = identified.groupby("customer_id")["order_id"].nunique()
        fallback_counts = transactions[transactions["order_id"].isna()].groupby("customer_id")["date"].nunique()
        result["frequency"] = order_counts.add(fallback_counts, fill_value=0)
    else:
        result["frequency"] = grouped["date"].nunique()
    result["frequency"] = result["frequency"].clip(lower=1)
    result["average_order_value"] = result["monetary_value"] / result["frequency"]
    result["recency_days"] = (pd.Timestamp(reference_date) - result["last_purchase"]).dt.days.clip(lower=0)
    result = result.drop(columns="last_purchase").reset_index()
    return result


def _feature_columns(features):
    return [name for name in FEATURE_LABELS if name in features.columns and features[name].nunique(dropna=True) > 1]


def _cluster_description(medians, overall):
    traits = []
    if medians["recency_days"] <= overall["recency_days"] * 0.8:
        traits.append("more recently active")
    elif medians["recency_days"] >= overall["recency_days"] * 1.2:
        traits.append("less recently active")
    if medians["frequency"] >= overall["frequency"] * 1.2:
        traits.append("more frequent purchasers")
    elif medians["frequency"] <= overall["frequency"] * 0.8:
        traits.append("less frequent purchasers")
    if medians["monetary_value"] >= overall["monetary_value"] * 1.2:
        traits.append("higher-spending customers")
    elif medians["monetary_value"] <= overall["monetary_value"] * 0.8:
        traits.append("lower-spending customers")
    profile = ", ".join(traits) if traits else "close to the overall customer profile"
    return (
        f"Typically {profile}: median recency {medians['recency_days']:.0f} days, "
        f"{medians['frequency']:.1f} purchases, and ${medians['monetary_value']:,.2f} monetary value per customer."
    )


def _segment_customers(transactions):
    if transactions is None:
        return {"available": False, "message": "Customer-level transaction data is unavailable."}
    if transactions.empty:
        return {"available": False, "message": "No valid dated customer transactions were found."}

    reference_date = transactions["date"].max() + pd.Timedelta(days=1)
    features = _customer_features(transactions, reference_date)
    if len(features) < 2:
        return {"available": False, "message": "At least two distinct customers are required for K-Means segmentation.", "customer_count": len(features)}

    feature_names = _feature_columns(features)
    varying_features = [name for name in feature_names if features[name].nunique() > 1]
    if not varying_features:
        return {"available": False, "message": "Customer values do not vary enough to form meaningful segments.", "customer_count": len(features)}

    scaled = StandardScaler().fit_transform(features[varying_features])
    unique_rows = len(np.unique(scaled, axis=0))
    max_clusters = min(5, len(features), unique_rows)
    if max_clusters < 2:
        return {"available": False, "message": "Customer values do not vary enough to form at least two segments.", "customer_count": len(features)}

    best_model = None
    best_score = -np.inf
    for cluster_count in range(2, max_clusters + 1):
        candidate = KMeans(n_clusters=cluster_count, random_state=42, n_init=10).fit(scaled)
        if cluster_count == len(features):
            score = -np.inf
        else:
            try:
                score = silhouette_score(scaled, candidate.labels_)
            except ValueError:
                score = -np.inf
        if best_model is None or score > best_score:
            best_model = candidate
            best_score = score

    features = features.copy()
    features["cluster_index"] = best_model.labels_
    ordering = features.groupby("cluster_index")["monetary_value"].median().sort_values().index.tolist()
    labels = {cluster_index: f"Segment {index + 1}" for index, cluster_index in enumerate(ordering)}
    features["cluster"] = features["cluster_index"].map(labels)
    overall = features[feature_names].median()
    clusters = []
    sizes = []
    for cluster_index in ordering:
        label = labels[cluster_index]
        members = features[features["cluster_index"] == cluster_index]
        medians = members[feature_names].median()
        characteristics = []
        for name in feature_names:
            value = medians[name]
            if name in {"monetary_value", "average_order_value"}:
                formatted = f"${value:,.2f}"
            elif name == "recency_days":
                formatted = f"{value:.0f} days"
            elif name == "quantity":
                formatted = f"{value:,.1f} units"
            else:
                formatted = f"{value:,.1f} purchases"
            characteristics.append({"label": FEATURE_LABELS[name], "value": formatted})
        count = len(members)
        sizes.append({"label": label, "size": count})
        clusters.append({
            "label": label,
            "size": count,
            "share": round(count / len(features) * 100, 1),
            "description": _cluster_description(medians, overall),
            "characteristics": characteristics,
        })

    plotted = features.head(500)
    scatter = [
        {"customer": str(row.customer_id), "cluster": row.cluster, "x": round(float(row.average_order_value), 2), "y": int(row.recency_days)}
        for row in plotted.itertuples(index=False)
    ]
    return {
        "available": True,
        "customer_count": len(features),
        "cluster_count": len(clusters),
        "feature_labels": [FEATURE_LABELS[name] for name in varying_features],
        "cluster_sizes": sizes,
        "clusters": clusters,
        "scatter": scatter,
        "scatter_truncated": len(features) > len(scatter),
    }


def _historical_snapshots(transactions, feature_names):
    first_date = transactions["date"].min().normalize()
    last_date = transactions["date"].max().normalize()
    first_cutoff = first_date + pd.Timedelta(days=CHURN_HORIZON_DAYS)
    last_cutoff = last_date - pd.Timedelta(days=CHURN_HORIZON_DAYS)
    if first_cutoff > last_cutoff:
        return pd.DataFrame(columns=["customer_id", *feature_names, "churned"])

    snapshots = []
    for cutoff in pd.date_range(first_cutoff, last_cutoff, freq="30D"):
        prior = transactions[transactions["date"] < cutoff]
        if prior.empty:
            continue
        customer_features = _customer_features(prior, cutoff)
        future = transactions[
            (transactions["date"] >= cutoff)
            & (transactions["date"] < cutoff + pd.Timedelta(days=CHURN_HORIZON_DAYS))
        ]
        active_customers = set(future["customer_id"])
        customer_features["churned"] = ~customer_features["customer_id"].isin(active_customers)
        snapshots.append(customer_features[["customer_id", *feature_names, "churned"]])
    return pd.concat(snapshots, ignore_index=True) if snapshots else pd.DataFrame(columns=["customer_id", *feature_names, "churned"])


def _risk_level(probability):
    if probability < 1 / 3:
        return "Low"
    if probability < 2 / 3:
        return "Medium"
    return "High"


def _churn_prediction(transactions):
    if transactions is None:
        return {"available": False, "message": "Customer-level transaction data is unavailable."}
    if transactions.empty:
        return {"available": False, "message": "No valid dated customer transactions were found."}

    reference_date = transactions["date"].max() + pd.Timedelta(days=1)
    current = _customer_features(transactions, reference_date)
    feature_names = _feature_columns(current)
    if not feature_names:
        return {"available": False, "message": "Customer values do not vary enough to train churn models."}
    snapshots = _historical_snapshots(transactions, feature_names)
    if len(snapshots) < MIN_CHURN_SNAPSHOTS or snapshots["customer_id"].nunique() < MIN_CHURN_CUSTOMERS:
        return {
            "available": False,
            "message": f"Churn prediction needs at least {MIN_CHURN_SNAPSHOTS} historical customer snapshots across {MIN_CHURN_CUSTOMERS} customers, spanning enough dates to observe a full {CHURN_HORIZON_DAYS}-day inactivity window. This dataset does not meet that threshold.",
            "horizon_days": CHURN_HORIZON_DAYS,
        }
    if snapshots["churned"].nunique() < 2:
        return {
            "available": False,
            "message": f"Historical {CHURN_HORIZON_DAYS}-day inactivity labels contain only one outcome; both active and churned examples are required to train churn models.",
            "horizon_days": CHURN_HORIZON_DAYS,
        }

    train_values = snapshots[feature_names].replace([np.inf, -np.inf], np.nan).fillna(0)
    predict_values = current[feature_names].replace([np.inf, -np.inf], np.nan).fillna(0)
    logistic = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
    )
    forest = RandomForestClassifier(
        n_estimators=200,
        min_samples_leaf=max(1, len(snapshots) // 1000),
        class_weight="balanced_subsample",
        random_state=42,
    )
    labels = snapshots["churned"].astype(int)
    logistic.fit(train_values, labels)
    forest.fit(train_values, labels)
    logistic_probabilities = logistic.predict_proba(predict_values)[:, 1]
    forest_probabilities = forest.predict_proba(predict_values)[:, 1]
    ensemble_probabilities = (logistic_probabilities + forest_probabilities) / 2

    models = []
    for name, probabilities in (("Logistic Regression", logistic_probabilities), ("Random Forest", forest_probabilities)):
        risks = [_risk_level(float(probability)) for probability in probabilities]
        models.append({
            "name": name,
            "risk_counts": {level: risks.count(level) for level in ("Low", "Medium", "High")},
        })
    customers = []
    for index, row in current.iterrows():
        probability = float(ensemble_probabilities[index])
        customers.append({
            "customer": str(row["customer_id"]),
            "risk": _risk_level(probability),
            "probability": round(probability * 100, 1),
            "logistic_probability": round(float(logistic_probabilities[index]) * 100, 1),
            "forest_probability": round(float(forest_probabilities[index]) * 100, 1),
        })
    customers.sort(key=lambda customer: customer["probability"], reverse=True)

    coefficients = logistic.named_steps["logisticregression"].coef_[0]
    raw_importance = (forest.feature_importances_ + np.abs(coefficients) / max(np.abs(coefficients).sum(), 1e-12)) / 2
    total_importance = max(float(raw_importance.sum()), 1e-12)
    factors = [
        {
            "feature": FEATURE_LABELS[name],
            "importance": round(float(raw_importance[index] / total_importance * 100), 1),
            "direction": "higher values are associated with higher churn risk" if coefficients[index] > 0 else "higher values are associated with lower churn risk",
        }
        for index, name in sorted(enumerate(feature_names), key=lambda item: raw_importance[item[0]], reverse=True)
    ]
    risk_counts = {level: sum(customer["risk"] == level for customer in customers) for level in ("Low", "Medium", "High")}
    return {
        "available": True,
        "horizon_days": CHURN_HORIZON_DAYS,
        "snapshot_count": len(snapshots),
        "customer_count": len(current),
        "models": models,
        "risk_counts": risk_counts,
        "factors": factors,
        "customers": customers,
    }


def analyze_customers(dataframe):
    columns = _resolve_columns(dataframe) if dataframe is not None else {}
    transactions, error = _prepare_transactions(dataframe, columns) if dataframe is not None else (None, "Upload and clean a dataset with customer-level transaction data to begin.")
    if error:
        unavailable = {"available": False, "message": error}
        return {"segmentation": unavailable, "churn": unavailable}
    return {
        "segmentation": _segment_customers(transactions),
        "churn": _churn_prediction(transactions),
    }