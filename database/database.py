from pathlib import Path
import sqlite3

DATABASE_PATH = Path(__file__).resolve().parent / "sales_forecasting.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection
