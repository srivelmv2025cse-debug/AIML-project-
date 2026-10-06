import unittest
from pathlib import Path

import pandas as pd

from services.customer_analytics import analyze_customers


def sample_customer_transactions():
    rows = []
    dates = pd.date_range("2024-01-01", "2025-10-01", freq="MS")
    for customer_number in range(24):
        customer_id = f"C{customer_number + 1:03d}"
        last_month = 4 if customer_number >= 12 else len(dates) - 1
        for month_index, purchase_date in enumerate(dates[:last_month + 1]):
            rows.append({
                "customer_id": customer_id,
                "order_id": f"{customer_id}-{month_index:02d}",
                "order_date": purchase_date,
                "total_amount": 35 + customer_number * 7 + month_index * (customer_number % 4 + 1),
                "quantity": 1 + customer_number % 5,
            })
    return pd.DataFrame(rows)


class CustomerAnalyticsTests(unittest.TestCase):
    def test_segments_customers_and_trains_both_churn_models(self):
        result = analyze_customers(sample_customer_transactions())

        self.assertTrue(result["segmentation"]["available"])
        self.assertGreaterEqual(result["segmentation"]["cluster_count"], 2)
        self.assertEqual(result["segmentation"]["customer_count"], 24)
        self.assertTrue(all(cluster["description"] for cluster in result["segmentation"]["clusters"]))
        self.assertTrue(result["churn"]["available"], result["churn"].get("message"))
        self.assertEqual(
            [model["name"] for model in result["churn"]["models"]],
            ["Logistic Regression", "Random Forest"],
        )
        self.assertEqual(sum(result["churn"]["risk_counts"].values()), 24)
        self.assertTrue(result["churn"]["factors"])

    def test_missing_customer_data_returns_clear_message(self):
        result = analyze_customers(pd.DataFrame({"order_date": ["2026-01-01"], "total_amount": [10]}))

        self.assertFalse(result["segmentation"]["available"])
        self.assertIn("customer", result["segmentation"]["message"].lower())
        self.assertFalse(result["churn"]["available"])

    def test_bundled_sales_sample_segments_customers_but_withholds_churn(self):
        sample_path = Path(__file__).resolve().parents[1] / "data" / "sample" / "sample_sales.csv"

        result = analyze_customers(pd.read_csv(sample_path))

        self.assertTrue(result["segmentation"]["available"])
        self.assertEqual(result["segmentation"]["customer_count"], 4)
        self.assertFalse(result["churn"]["available"])
        self.assertIn("90-day", result["churn"]["message"])

    def test_quantity_is_not_reported_when_the_source_has_no_quantity(self):
        transactions = sample_customer_transactions().drop(columns="quantity")

        result = analyze_customers(transactions)

        self.assertNotIn("Quantity purchased", result["segmentation"]["feature_labels"])
        self.assertNotIn("Quantity purchased", [factor["feature"] for factor in result["churn"]["factors"]])

    def test_unit_price_without_quantity_is_not_treated_as_monetary_value(self):
        transactions = pd.DataFrame({
            "customer_id": ["C1", "C2"],
            "order_date": ["2026-01-01", "2026-01-02"],
            "unit_price": [10, 20],
        })

        segmentation = analyze_customers(transactions)["segmentation"]

        self.assertFalse(segmentation["available"])
        self.assertIn("quantity", segmentation["message"].lower())

    def test_short_history_does_not_create_churn_scores(self):
        transactions = sample_customer_transactions()
        transactions["order_date"] = pd.Timestamp("2026-01-01") + pd.to_timedelta(transactions.index % 60, unit="D")

        churn = analyze_customers(transactions)["churn"]

        self.assertFalse(churn["available"])
        self.assertIn("90-day", churn["message"])


if __name__ == "__main__":
    unittest.main()