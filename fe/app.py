import os
from datetime import datetime

import requests
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def api_get(path: str, params: dict | None = None) -> list | dict | None:
    """Call the FastAPI backend and return parsed JSON, or None on error."""
    try:
        response = requests.get(f"{BACKEND_URL}{path}", params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        app.logger.error("GET %s failed: %s", path, exc)
        return None


def api_post(path: str, data: dict) -> dict | None:
    try:
        response = requests.post(f"{BACKEND_URL}{path}", json=data, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        app.logger.error("POST %s failed: %s", path, exc)
        return None


def api_delete(path: str) -> bool:
    try:
        response = requests.delete(f"{BACKEND_URL}{path}", timeout=5)
        response.raise_for_status()
        return True
    except requests.RequestException as exc:
        app.logger.error("DELETE %s failed: %s", path, exc)
        return False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def dashboard():
    accounts = api_get("/api/accounts/") or []
    recent_transactions = api_get("/api/transactions/", params={"limit": 5}) or []
    categories = api_get("/api/categories/") or []

    total_balance = sum(float(a.get("balance", 0)) for a in accounts)
    total_income = sum(
        float(t["amount"]) for t in recent_transactions if t.get("type") == "income"
    )
    total_expense = sum(
        float(t["amount"]) for t in recent_transactions if t.get("type") == "expense"
    )

    return render_template(
        "index.html",
        accounts=accounts,
        recent_transactions=recent_transactions,
        categories=categories,
        total_balance=total_balance,
        total_income=total_income,
        total_expense=total_expense,
    )


# ---- Accounts -----


@app.route("/accounts")
def accounts():
    accounts = api_get("/api/accounts/") or []
    return render_template("accounts.html", accounts=accounts)


@app.route("/accounts/add", methods=["POST"])
def add_account():
    payload = {
        "name": request.form.get("name", "").strip(),
        "type": request.form.get("type", "checking"),
        "balance": float(request.form.get("balance", 0)),
    }
    result = api_post("/api/accounts/", payload)
    if result:
        flash(f"Account '{result['name']}' created successfully.", "success")
    else:
        flash("Failed to create account. Please try again.", "danger")
    return redirect(url_for("accounts"))


@app.route("/accounts/delete/<int:account_id>", methods=["POST"])
def delete_account(account_id: int):
    ok = api_delete(f"/api/accounts/{account_id}")
    if ok:
        flash("Account deleted.", "success")
    else:
        flash("Failed to delete account.", "danger")
    return redirect(url_for("accounts"))


# ---- Categories ----


@app.route("/categories")
def categories():
    cats = api_get("/api/categories/") or []
    return render_template("categories.html", categories=cats)


@app.route("/categories/add", methods=["POST"])
def add_category():
    payload = {
        "name": request.form.get("name", "").strip(),
        "type": request.form.get("type", "expense"),
    }
    result = api_post("/api/categories/", payload)
    if result:
        flash(f"Category '{result['name']}' created successfully.", "success")
    else:
        flash("Failed to create category. It may already exist.", "danger")
    return redirect(url_for("categories"))


@app.route("/categories/delete/<int:category_id>", methods=["POST"])
def delete_category(category_id: int):
    ok = api_delete(f"/api/categories/{category_id}")
    if ok:
        flash("Category deleted.", "success")
    else:
        flash("Failed to delete category.", "danger")
    return redirect(url_for("categories"))


# ---- Transactions ----


@app.route("/transactions")
def transactions():
    account_id = request.args.get("account_id")
    params = {"limit": 100}
    if account_id:
        params["account_id"] = account_id

    txns = api_get("/api/transactions/", params=params) or []
    accounts = api_get("/api/accounts/") or []
    cats = api_get("/api/categories/") or []

    return render_template(
        "transactions.html",
        transactions=txns,
        accounts=accounts,
        categories=cats,
        selected_account=account_id,
    )


@app.route("/transactions/add", methods=["POST"])
def add_transaction():
    date_str = request.form.get("date") or datetime.utcnow().isoformat()
    try:
        # Accept 'YYYY-MM-DDTHH:MM' from datetime-local input
        date_iso = datetime.fromisoformat(date_str).isoformat()
    except ValueError:
        date_iso = datetime.utcnow().isoformat()

    category_id = request.form.get("category_id") or None
    payload = {
        "account_id": int(request.form.get("account_id")),
        "category_id": int(category_id) if category_id else None,
        "amount": float(request.form.get("amount", 0)),
        "description": request.form.get("description", "").strip() or None,
        "type": request.form.get("type", "expense"),
        "date": date_iso,
    }
    result = api_post("/api/transactions/", payload)
    if result:
        flash("Transaction added successfully.", "success")
    else:
        flash("Failed to add transaction.", "danger")
    return redirect(url_for("transactions"))


@app.route("/transactions/delete/<int:transaction_id>", methods=["POST"])
def delete_transaction(transaction_id: int):
    ok = api_delete(f"/api/transactions/{transaction_id}")
    if ok:
        flash("Transaction deleted.", "success")
    else:
        flash("Failed to delete transaction.", "danger")
    return redirect(url_for("transactions"))


# ---------------------------------------------------------------------------
# Entry point (for local dev without Docker)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
