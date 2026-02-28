import os
from datetime import datetime

import httpx
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
WS_URL = os.getenv("WS_URL", "ws://localhost:8000/ws")

# httpx timeout configuration
# Docs: https://www.python-httpx.org/advanced/timeouts/
_timeout = httpx.Timeout(10.0, connect=5.0)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def api_get(path: str, params: dict | None = None) -> list | dict | None:
    """Call the FastAPI backend and return parsed JSON, or None on error."""
    try:
        response = httpx.get(f"{BACKEND_URL}{path}", params=params, timeout=_timeout)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        app.logger.error("GET %s returned %s: %s", path, exc.response.status_code, exc)
        return None
    except httpx.RequestError as exc:
        app.logger.error("GET %s failed: %s", path, exc)
        return None


def api_post(path: str, data: dict) -> dict | None:
    try:
        response = httpx.post(f"{BACKEND_URL}{path}", json=data, timeout=_timeout)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        app.logger.error("POST %s returned %s: %s", path, exc.response.status_code, exc)
        return None
    except httpx.RequestError as exc:
        app.logger.error("POST %s failed: %s", path, exc)
        return None


def api_put(path: str, data: dict) -> dict | None:
    try:
        response = httpx.put(f"{BACKEND_URL}{path}", json=data, timeout=_timeout)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        app.logger.error("PUT %s returned %s: %s", path, exc.response.status_code, exc)
        return None
    except httpx.RequestError as exc:
        app.logger.error("PUT %s failed: %s", path, exc)
        return None


def api_delete(path: str) -> bool:
    try:
        response = httpx.delete(f"{BACKEND_URL}{path}", timeout=_timeout)
        response.raise_for_status()
        return True
    except httpx.HTTPStatusError as exc:
        app.logger.error(
            "DELETE %s returned %s: %s", path, exc.response.status_code, exc
        )
        return False
    except httpx.RequestError as exc:
        app.logger.error("DELETE %s failed: %s", path, exc)
        return False


# ---------------------------------------------------------------------------
# Template context — make WS_URL available to all templates
# ---------------------------------------------------------------------------


@app.context_processor
def inject_ws_url():
    return dict(ws_url=WS_URL)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@app.route("/")
def dashboard():
    accounts = api_get("/api/accounts/") or []
    recent_transactions = api_get("/api/transactions/", params={"limit": 5}) or []

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
        total_balance=total_balance,
        total_income=total_income,
        total_expense=total_expense,
    )


@app.route("/api/dashboard-data")
def dashboard_data():
    """JSON endpoint used by the WebSocket JS to refresh dashboard numbers."""
    from flask import jsonify

    accounts = api_get("/api/accounts/") or []
    recent_txns = api_get("/api/transactions/", params={"limit": 5}) or []
    total_balance = sum(float(a.get("balance", 0)) for a in accounts)
    total_income = sum(
        float(t["amount"]) for t in recent_txns if t.get("type") == "income"
    )
    total_expense = sum(
        float(t["amount"]) for t in recent_txns if t.get("type") == "expense"
    )
    return jsonify(
        total_balance=f"{total_balance:.2f}",
        total_income=f"{total_income:.2f}",
        total_expense=f"{total_expense:.2f}",
        accounts=accounts,
        recent_transactions=recent_txns,
    )


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------


@app.route("/accounts")
def accounts():
    accounts_list = api_get("/api/accounts/") or []
    return render_template("accounts.html", accounts=accounts_list)


@app.route("/accounts/add", methods=["GET", "POST"])
def add_account():
    if request.method == "POST":
        payload = {
            "name": request.form.get("name", "").strip(),
            "type": request.form.get("type", "checking"),
            "balance": float(request.form.get("balance", 0)),
        }
        result = api_post("/api/accounts/", payload)
        if result:
            flash(f"Account '{result['name']}' created.", "success")
        else:
            flash("Failed to create account.", "danger")
        return redirect(url_for("accounts"))

    return render_template("account_form.html", account=None)


@app.route("/accounts/edit/<int:account_id>", methods=["GET", "POST"])
def edit_account(account_id: int):
    if request.method == "POST":
        payload = {
            "name": request.form.get("name", "").strip(),
            "type": request.form.get("type"),
            "balance": float(request.form.get("balance", 0)),
        }
        result = api_put(f"/api/accounts/{account_id}", payload)
        if result:
            flash(f"Account '{result['name']}' updated.", "success")
        else:
            flash("Failed to update account.", "danger")
        return redirect(url_for("accounts"))

    account = api_get(f"/api/accounts/{account_id}")
    if not account:
        flash("Account not found.", "danger")
        return redirect(url_for("accounts"))
    return render_template("account_form.html", account=account)


@app.route("/accounts/delete/<int:account_id>", methods=["POST"])
def delete_account(account_id: int):
    ok = api_delete(f"/api/accounts/{account_id}")
    if ok:
        flash("Account deleted.", "success")
    else:
        flash("Failed to delete account.", "danger")
    return redirect(url_for("accounts"))


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


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
        flash(f"Category '{result['name']}' created.", "success")
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


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


@app.route("/transactions")
def transactions():
    account_id = request.args.get("account_id")
    params = {"limit": 100}
    if account_id:
        params["account_id"] = account_id

    txns = api_get("/api/transactions/", params=params) or []
    accounts_list = api_get("/api/accounts/") or []

    return render_template(
        "transactions.html",
        transactions=txns,
        accounts=accounts_list,
        selected_account=account_id,
    )


@app.route("/transactions/add", methods=["GET", "POST"])
def add_transaction():
    if request.method == "POST":
        date_str = request.form.get("date") or datetime.utcnow().isoformat()
        try:
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
            flash("Transaction added.", "success")
        else:
            flash("Failed to add transaction.", "danger")
        return redirect(url_for("transactions"))

    # GET — show empty form
    accounts_list = api_get("/api/accounts/") or []
    cats = api_get("/api/categories/") or []
    preselected = request.args.get("account_id")
    return render_template(
        "transaction_form.html",
        transaction=None,
        accounts=accounts_list,
        categories=cats,
        selected_account=preselected,
    )


@app.route("/transactions/edit/<int:transaction_id>", methods=["GET", "POST"])
def edit_transaction(transaction_id: int):
    if request.method == "POST":
        date_str = request.form.get("date") or datetime.utcnow().isoformat()
        try:
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
        result = api_put(f"/api/transactions/{transaction_id}", payload)
        if result:
            flash("Transaction updated.", "success")
        else:
            flash("Failed to update transaction.", "danger")
        return redirect(url_for("transactions"))

    # GET — load existing transaction into form
    txn = api_get(f"/api/transactions/{transaction_id}")
    if not txn:
        flash("Transaction not found.", "danger")
        return redirect(url_for("transactions"))
    accounts_list = api_get("/api/accounts/") or []
    cats = api_get("/api/categories/") or []
    return render_template(
        "transaction_form.html",
        transaction=txn,
        accounts=accounts_list,
        categories=cats,
        selected_account=None,
    )


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
