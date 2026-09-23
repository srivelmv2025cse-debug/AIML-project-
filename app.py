from pathlib import Path
import sqlite3

from flask import Flask, g, render_template

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database" / "sales_forecasting.db"

app = Flask(__name__)
app.config["DATABASE"] = DATABASE_PATH

PAGES = {
    "home": {"label": "Home", "endpoint": "home", "icon": "house"},
    "dashboard": {"label": "Dashboard", "endpoint": "dashboard", "icon": "grid"},
    "upload": {"label": "Upload Data", "endpoint": "upload_data", "icon": "upload"},
    "forecasting": {"label": "Forecasting", "endpoint": "forecasting", "icon": "trend-up"},
    "analytics": {"label": "Analytics", "endpoint": "analytics", "icon": "bar-chart"},
    "customers": {"label": "Customers", "endpoint": "customers", "icon": "users"},
    "products": {"label": "Products", "endpoint": "products", "icon": "box"},
    "documents": {"label": "Documents", "endpoint": "documents", "icon": "file-text"},
    "ai_insights": {"label": "AI Insights", "endpoint": "ai_insights", "icon": "sparkles"},
    "alerts": {"label": "Alerts", "endpoint": "alerts", "icon": "bell"},
    "reports": {"label": "Reports", "endpoint": "reports", "icon": "file-bar-chart"},
    "settings": {"label": "Settings", "endpoint": "settings", "icon": "settings"},
}


def get_db():
    if "db" not in g:
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS app_metadata (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            project_name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        "INSERT OR IGNORE INTO app_metadata (id, project_name) VALUES (1, ?)",
        ("AI-Powered Sales Forecasting and Business Analytics",),
    )
    db.commit()


@app.context_processor
def inject_navigation():
    return {"pages": PAGES}


@app.route("/")
def home():
    return render_template("home.html", active_page="home", page_title="Sales intelligence, ready for what comes next")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", active_page="dashboard", page_title="Dashboard")


@app.route("/upload-data")
def upload_data():
    return render_template("page.html", active_page="upload", page_title="Upload Data", description="Prepare your sales data workspace for a future import workflow.")


@app.route("/forecasting")
def forecasting():
    return render_template("page.html", active_page="forecasting", page_title="Forecasting", description="Forecasting tools will be introduced in a later development phase.")


@app.route("/analytics")
def analytics():
    return render_template("page.html", active_page="analytics", page_title="Analytics", description="Your future analytics workspace is ready for data-driven views.")


@app.route("/customers")
def customers():
    return render_template("page.html", active_page="customers", page_title="Customers", description="Customer records and segmentation views will be added in a later phase.")


@app.route("/products")
def products():
    return render_template("page.html", active_page="products", page_title="Products", description="Product performance views will be added after the initial setup phase.")


@app.route("/documents")
def documents():
    return render_template("page.html", active_page="documents", page_title="Documents", description="A central place for project documents is ready to be connected.")


@app.route("/ai-insights")
def ai_insights():
    return render_template("page.html", active_page="ai_insights", page_title="AI Insights", description="AI-generated business insights are intentionally reserved for a later day.")


@app.route("/alerts")
def alerts():
    return render_template("page.html", active_page="alerts", page_title="Alerts", description="Alert rules and notifications will be configured in a future phase.")


@app.route("/reports")
def reports():
    return render_template("page.html", active_page="reports", page_title="Reports", description="Report building and exports will be introduced after the foundation is complete.")


@app.route("/settings")
def settings():
    return render_template("page.html", active_page="settings", page_title="Settings", description="Application preferences will be connected as the project grows.")


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
