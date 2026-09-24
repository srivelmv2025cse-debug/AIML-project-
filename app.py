from pathlib import Path
import sqlite3
from uuid import uuid4

from flask import Flask, g, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from services.data_processing import (
    MAX_UPLOAD_BYTES,
    clean_dataset,
    dataframe_summary,
    detect_columns,
    file_extension,
    read_dataset,
    save_dataset,
    validate_upload,
)

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database" / "sales_forecasting.db"
UPLOADS_DIR = BASE_DIR / "data" / "uploads"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

app = Flask(__name__)
app.config["DATABASE"] = DATABASE_PATH
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
app.config["SECRET_KEY"] = "day-2-local-development-key"


@app.errorhandler(413)
def upload_too_large(_error):
    return render_template(
        "upload_data.html",
        active_page="upload",
        page_title="Upload Data",
        error="The file is too large. The maximum upload size is 10 MB.",
    ), 413

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


@app.route("/upload-data", methods=["GET", "POST"])
def upload_data():
    if request.method == "GET":
        return render_template("upload_data.html", active_page="upload", page_title="Upload Data")

    uploaded_file = request.files.get("dataset")
    try:
        filename = uploaded_file.filename if uploaded_file else ""
        extension = validate_upload(filename, request.content_length)
        safe_name = secure_filename(filename)
        if not safe_name:
            raise ValueError("The file name is not valid.")
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        stored_path = UPLOADS_DIR / f"{uuid4().hex}_{safe_name}"
        uploaded_file.save(stored_path)
        dataframe = read_dataset(stored_path, extension)
        if dataframe.empty and len(dataframe.columns) == 0:
            raise ValueError("The uploaded dataset does not contain any columns.")
        summary = dataframe_summary(dataframe)
        detected = detect_columns(dataframe.columns)
        return render_template(
            "upload_data.html",
            active_page="upload",
            page_title="Upload Data",
            summary=summary,
            detected=detected,
            columns=list(dataframe.columns),
            preview=dataframe.head(15).fillna("").to_html(classes="preview-table", index=False, border=0),
            stored_name=stored_path.name,
            original_name=filename,
        )
    except Exception as error:
        if "stored_path" in locals() and stored_path.exists():
            stored_path.unlink()
        return render_template(
            "upload_data.html",
            active_page="upload",
            page_title="Upload Data",
            error=str(error),
        ), 400


@app.route("/upload-data/process", methods=["POST"])
def process_upload():
    stored_name = request.form.get("stored_name", "")
    if not stored_name or Path(stored_name).name != stored_name:
        return redirect(url_for("upload_data"))

    stored_path = UPLOADS_DIR / stored_name
    try:
        extension = file_extension(stored_name)
        dataframe = read_dataset(stored_path, extension)
        mapping = {field: request.form.get(field, "") for field in (
            "date", "product", "product_id", "category", "quantity", "price", "sales",
            "customer_id", "region", "discount", "inventory",
        )}
        cleaned = clean_dataset(dataframe, mapping)
        output_name = f"cleaned_{Path(stored_name).stem}.csv"
        output_path = PROCESSED_DIR / output_name
        save_dataset(cleaned, output_path)
        return render_template(
            "upload_data.html",
            active_page="upload",
            page_title="Upload Data",
            success=f"{request.form.get('original_name', stored_name)} was cleaned and saved successfully.",
            processed_name=output_name,
            cleaned_summary=dataframe_summary(cleaned),
        )
    except Exception as error:
        return render_template(
            "upload_data.html",
            active_page="upload",
            page_title="Upload Data",
            error=f"The dataset could not be processed: {error}",
        ), 400


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
