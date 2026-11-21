/**
 * history.js — Transaction history with date filters, customer filter, and pagination.
 * Single-language display (defaults to English, switches cleanly to Hindi).
 */

// ─── State ────────────────────────────────────────────────────────────────────
let currentFilters = {};
let currentPage = 0;
const PAGE_SIZE = 20;
let allLoaded = false;
let isLoading = false;
let loadedTransactions = [];

// ─── On Page Load ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  if (!checkAuth()) return;

  // Date quick-filter buttons
  document.querySelectorAll(".date-filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".date-filter-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const customDate = document.getElementById("custom-date");
      if (customDate) customDate.value = "";
      setDateFilter(btn.getAttribute("data-range"));
    });
  });

  // Custom date picker
  const customDate = document.getElementById("custom-date");
  if (customDate) {
    customDate.addEventListener("change", () => {
      if (!customDate.value) return;
      document.querySelectorAll(".date-filter-btn").forEach((b) => b.classList.remove("active"));
      const d = customDate.value;
      currentFilters = { date_from: d, date_to: d };
      currentPage = 0;
      allLoaded = false;
      fetchAndRenderHistory(true);
    });
  }

  // Customer filter dropdown
  const customerFilter = document.getElementById("customer-filter");
  if (customerFilter) {
    customerFilter.addEventListener("change", () => {
      currentFilters.customer_id = customerFilter.value || undefined;
      currentPage = 0;
      allLoaded = false;
      fetchAndRenderHistory(true);
    });
    await populateCustomerDropdown(customerFilter);
  }

  // Load More button
  const loadMoreBtn = document.getElementById("btn-load-more");
  if (loadMoreBtn) {
    loadMoreBtn.addEventListener("click", loadMore);
  }

  // Check for ?customer=ID URL param
  const urlParams = new URLSearchParams(window.location.search);
  const presetCustomerId = urlParams.get("customer");
  if (presetCustomerId) {
    currentFilters.customer_id = presetCustomerId;
    if (customerFilter) customerFilter.value = presetCustomerId;
  }

  // Listen for language changes and re-render transaction items
  window.addEventListener("languageChanged", () => {
    renderHistoryItems();
  });

  // Default: show today
  setDateFilter("today");
  initNavbar("history");
});

// ─── Date Filter ─────────────────────────────────────────────────────────────
function setDateFilter(range) {
  const now = new Date();
  const yyyy = (d) => d.toISOString().slice(0, 10);

  let date_from, date_to;

  if (range === "today") {
    date_from = date_to = yyyy(now);
  } else if (range === "yesterday") {
    const y = new Date(now);
    y.setDate(y.getDate() - 1);
    date_from = date_to = yyyy(y);
  } else if (range === "week") {
    const start = new Date(now);
    start.setDate(now.getDate() - 6);
    date_from = yyyy(start);
    date_to = yyyy(now);
  } else if (range === "month") {
    const start = new Date(now.getFullYear(), now.getMonth(), 1);
    date_from = yyyy(start);
    date_to = yyyy(now);
  } else {
    date_from = date_to = yyyy(now);
  }

  currentFilters = { ...currentFilters, date_from, date_to };
  currentPage = 0;
  allLoaded = false;
  fetchAndRenderHistory(true);
}

// ─── Fetch & Render ───────────────────────────────────────────────────────────
async function fetchAndRenderHistory(replace = false) {
  if (isLoading) return;
  isLoading = true;

  const container = document.getElementById("history-list");
  const loadMoreBtn = document.getElementById("btn-load-more");

  if (replace && container) {
    container.innerHTML = `
      <div style="text-align: center; padding: 40px 20px; color: #9e9e9e;">
        <div class="spinner" style="margin: 0 auto 12px;"></div>
        <div>${t("loadingTransactions", "Loading transactions...")}</div>
      </div>`;
  }

  if (loadMoreBtn) loadMoreBtn.style.display = "none";

  const res = await getTransactionsFiltered({
    ...currentFilters,
    offset: currentPage * PAGE_SIZE,
    limit: PAGE_SIZE,
  });

  isLoading = false;

  if (!res.ok) {
    if (replace && container) {
      container.innerHTML = `<div style="text-align: center; padding: 32px; color: #c62828;">${res.error || "Failed to load"}</div>`;
    }
    showToast(res.error || "Failed to load transactions", "error");
    return;
  }

  const txns = Array.isArray(res.data) ? res.data : [];

  if (replace) {
    loadedTransactions = txns;
  } else {
    loadedTransactions = loadedTransactions.concat(txns);
  }

  renderHistoryItems();

  if (txns.length < PAGE_SIZE) {
    allLoaded = true;
    if (loadMoreBtn) loadMoreBtn.style.display = "none";
  } else {
    allLoaded = false;
    if (loadMoreBtn) loadMoreBtn.style.display = "block";
  }
}

function renderHistoryItems() {
  const container = document.getElementById("history-list");
  if (!container) return;

  if (loadedTransactions.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 40px 20px; color: #9e9e9e;">
        <div style="font-size: 48px; margin-bottom: 12px;">📋</div>
        <div style="font-size: 17px; font-weight: 600; margin-bottom: 4px;">
          ${t("noHistoryFound", "No transactions found")}
        </div>
        <div style="font-size: 13px; margin-top: 6px;">
          ${t("noHistorySub", "Try a different date or customer filter")}
        </div>
      </div>`;
    return;
  }

  container.innerHTML = "";
  loadedTransactions.forEach((txn) => {
    const el = formatTransaction(txn);
    container.appendChild(el);
  });
}

function loadMore() {
  if (allLoaded || isLoading) return;
  currentPage++;
  fetchAndRenderHistory(false);
}

// ─── Transaction Item ─────────────────────────────────────────────────────────
function formatTransaction(txn) {
  const isCredit = txn.direction === "credit";
  const amount = formatPaise(Math.abs(txn.amount_paise || 0));
  const name = txn.customer_name || "Unknown";
  const initials = name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
  const timeStr = txn.recorded_at ? formatDateTime(txn.recorded_at) : "";

  // Single language labels
  const sourceLabel = txn.source === "voice"
    ? (currentLanguage() === "hi" ? "🎤 आवाज़" : "🎤 Voice")
    : (currentLanguage() === "hi" ? "✍️ हाथ से" : "✍️ Manual");

  const dirLabel = isCredit
    ? t("creditPrefix", "↓ Credit")
    : t("debitPrefix", "↑ Debit");

  const item = document.createElement("div");
  item.className = "txn-item";

  item.innerHTML = `
    <div class="txn-info">
      <div class="txn-avatar">${escapeHtml(initials)}</div>
      <div>
        <div class="txn-name">${escapeHtml(name)}</div>
        <div class="txn-time">
          ${timeStr}
          <span style="display: inline-block; margin-left: 6px; padding: 1px 6px; background: #f5f5f5; border-radius: 10px; font-size: 11px;">
            ${sourceLabel}
          </span>
        </div>
      </div>
    </div>
    <div class="txn-amount ${isCredit ? "credit" : "debit"}">
      <span style="font-size: 13px; font-weight: 600;">${dirLabel}</span><br>
      <span style="font-size: 16px; font-weight: 800;">${isCredit ? "+" : "-"}${amount}</span>
    </div>`;

  return item;
}

// ─── Customer Dropdown ────────────────────────────────────────────────────────
async function populateCustomerDropdown(selectEl) {
  const res = await getCustomers("");
  if (!res.ok || !Array.isArray(res.data)) return;

  res.data.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = c.name;
    selectEl.appendChild(opt);
  });
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function formatDateTime(isoDate) {
  if (!isoDate) return "";
  try {
    const d = new Date(isoDate);
    if (isNaN(d.getTime())) return String(isoDate);
    const dateStr = d.toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
    const timeStr = d.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
    return `${dateStr} • ${timeStr}`;
  } catch (e) {
    return String(isoDate);
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
