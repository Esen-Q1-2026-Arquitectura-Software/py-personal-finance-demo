/**
 * WebSocket client for real-time notifications & dashboard updates.
 *
 * Connects to the FastAPI /ws endpoint. On each event it:
 *  1. Shows a toast notification (auto-dismisses after 5 s).
 *  2. If the user is on the dashboard, refreshes the summary cards and
 *     recent-transactions table via /api/dashboard-data.
 *
 * Auto-reconnects with exponential back-off up to 30 s.
 */
(function () {
  "use strict";

  var wsUrl = document.body.dataset.wsUrl;
  if (!wsUrl) return;

  var toastBox = document.getElementById("toast-container");
  var ws;
  var reconnectDelay = 1000;

  /* ---- Toast helper ---- */

  function showToast(message, alertType) {
    if (!toastBox) return;
    var el = document.createElement("div");
    el.className = "alert alert-" + (alertType || "info") + " shadow-sm mb-2";
    el.style.transition = "opacity 0.4s";
    el.textContent = message;
    toastBox.appendChild(el);
    setTimeout(function () {
      el.style.opacity = "0";
      setTimeout(function () {
        el.remove();
      }, 400);
    }, 5000);
  }

  /* ---- Dashboard live-refresh ---- */

  function refreshDashboard() {
    var balanceEl = document.getElementById("dashboard-balance");
    if (!balanceEl) return; // not on the dashboard page

    fetch("/api/dashboard-data")
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        balanceEl.textContent = "$" + d.total_balance;
        var incEl = document.getElementById("dashboard-income");
        if (incEl) incEl.textContent = "$" + d.total_income;
        var expEl = document.getElementById("dashboard-expense");
        if (expEl) expEl.textContent = "$" + d.total_expense;

        /* Rebuild accounts list */
        var accList = document.getElementById("dashboard-accounts");
        if (accList && d.accounts) {
          accList.innerHTML = "";
          if (d.accounts.length === 0) {
            accList.innerHTML =
              '<li class="list-group-item text-muted">No accounts yet.</li>';
          } else {
            d.accounts.forEach(function (acc) {
              var li = document.createElement("li");
              li.className = "list-group-item d-flex justify-content-between";
              li.innerHTML =
                "<span>" +
                '<span class="badge bg-secondary me-2">' +
                acc.type +
                "</span>" +
                acc.name +
                "</span>" +
                "<strong>$" +
                parseFloat(acc.balance).toFixed(2) +
                "</strong>";
              accList.appendChild(li);
            });
          }
        }

        /* Rebuild recent-transactions tbody */
        var tbody = document.getElementById("dashboard-txn-body");
        if (tbody && d.recent_transactions) {
          tbody.innerHTML = "";
          d.recent_transactions.forEach(function (txn) {
            var cls =
              txn.type === "income"
                ? "text-success"
                : txn.type === "expense"
                  ? "text-danger"
                  : "text-secondary";
            var prefix =
              txn.type === "income" ? "+" : txn.type === "expense" ? "-" : "";
            var tr = document.createElement("tr");
            tr.innerHTML =
              "<td>" +
              txn.date.substring(0, 10) +
              "</td>" +
              "<td>" +
              (txn.description || "\u2014") +
              "</td>" +
              "<td>" +
              (txn.category ? txn.category.name : "\u2014") +
              "</td>" +
              '<td class="text-end fw-semibold ' +
              cls +
              '">' +
              prefix +
              "$" +
              parseFloat(txn.amount).toFixed(2) +
              "</td>";
            tbody.appendChild(tr);
          });
        }
      })
      .catch(function () {
        /* silently ignore fetch errors */
      });
  }

  /* ---- WebSocket connection ---- */

  function connect() {
    ws = new WebSocket(wsUrl);

    ws.onopen = function () {
      reconnectDelay = 1000;
      console.log("[ws] connected to", wsUrl);
    };

    ws.onmessage = function (e) {
      try {
        var event = JSON.parse(e.data);
        showToast(event.message || "Update received", event.alert || "info");
        refreshDashboard();
      } catch (_) {
        /* ignore malformed messages */
      }
    };

    ws.onclose = function () {
      console.log("[ws] disconnected – reconnecting in", reconnectDelay, "ms");
      setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, 30000);
    };

    ws.onerror = function () {
      ws.close();
    };
  }

  connect();
})();
