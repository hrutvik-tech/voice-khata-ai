/**
 * customers.js — Customer list, search, add, and history navigation for Bolta Khata.
 * Ensures single-language display (English by default, switches cleanly to Hindi).
 */

// ─── State ────────────────────────────────────────────────────────────────────
let allCustomers = [];
let isAddingCustomer = false;

// ─── On Page Load ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  if (!checkAuth()) return;

  // Search input live filtering
  const searchInput = document.getElementById("search-input");
  if (searchInput) {
    searchInput.addEventListener("input", () => searchCustomers(searchInput.value));
  }

  // Add customer button (opens modal)
  const addBtn = document.getElementById("btn-add-customer");
  if (addBtn) addBtn.addEventListener("click", openAddModal);

  // Modal close button
  const closeBtn = document.getElementById("modal-close");
  if (closeBtn) closeBtn.addEventListener("click", closeAddModal);

  // Modal backdrop click closes modal
  const modalOverlay = document.getElementById("add-customer-modal");
  if (modalOverlay) {
    modalOverlay.addEventListener("click", (e) => {
      if (e.target === modalOverlay) closeAddModal();
    });
  }

  // Add customer form submit
  const saveBtn = document.getElementById("btn-save-customer");
  if (saveBtn) saveBtn.addEventListener("click", handleAddCustomer);

  // Listen for language changes and re-render list
  window.addEventListener("languageChanged", () => {
    if (allCustomers.length > 0) {
      const query = (document.getElementById("search-input")?.value || "").trim();
      searchCustomers(query);
    }
  });

  // Load customer list
  loadCustomers();
  initNavbar("customers");
});

// ─── Load Customers ───────────────────────────────────────────────────────────
async function loadCustomers() {
  showListLoading(true);
  const res = await getCustomers("");
  showListLoading(false);

  if (res.ok && Array.isArray(res.data)) {
    allCustomers = res.data;
  } else {
    allCustomers = [];
    if (res.error) showToast(res.error, "error");
  }

  renderCustomers(allCustomers);
}

// ─── Search ───────────────────────────────────────────────────────────────────
function searchCustomers(query) {
  if (!query || !query.trim()) {
    renderCustomers(allCustomers);
    return;
  }
  const q = query.trim().toLowerCase();
  const filtered = allCustomers.filter((c) => {
    const name = (c.name || "").toLowerCase();
    const phone = (c.phone || "").toLowerCase();
    return name.includes(q) || phone.includes(q);
  });
  renderCustomers(filtered);
}

// ─── Render ───────────────────────────────────────────────────────────────────
function renderCustomers(list) {
  const container = document.getElementById("customer-list");
  const countEl = document.getElementById("customer-count");
  if (!container) return;

  if (countEl) {
    if (list && list.length > 0) {
      const isSingle = list.length === 1;
      const label = isSingle
        ? t("customerCountSingle", "1 customer")
        : `${list.length} ${t("customerCountPlural", "customers")}`;
      countEl.textContent = label;
    } else {
      countEl.textContent = "";
    }
  }

  if (!list || list.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 40px 20px; color: #9e9e9e;">
        <div style="font-size: 48px; margin-bottom: 12px;">👤</div>
        <div style="font-size: 17px; font-weight: 600; margin-bottom: 4px;">
          ${t("noCustomersYet", "No customers yet")}
        </div>
        <div style="font-size: 13px; margin-top: 6px;">
          ${t("noCustomersSub", "Add your first customer using the + button above")}
        </div>
      </div>`;
    return;
  }

  container.innerHTML = "";
  list.forEach((c) => {
    const card = buildCustomerCard(c);
    container.appendChild(card);
  });
}

function buildCustomerCard(customer) {
  const balance = customer.balance_paise || 0;
  const isCredit = balance >= 0;
  const absBalance = Math.abs(balance);

  const initials = (customer.name || "?")
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();

  const lastPrefix = t("customerLast", "Last");
  const lastDate = customer.last_activity_at
    ? `${lastPrefix}: ${formatDate(customer.last_activity_at)}`
    : "";

  const balanceLabel = isCredit ? t("toCollect", "To collect") : t("toPay", "To pay");
  const color = isCredit ? "#2E7D32" : "#c62828";

  const card = document.createElement("div");
  card.className = "txn-item";
  card.style.cursor = "pointer";
  card.setAttribute("role", "button");
  card.setAttribute("tabindex", "0");
  card.setAttribute("aria-label", `View ${customer.name}'s transactions`);

  card.innerHTML = `
    <div class="txn-info">
      <div class="txn-avatar">${initials}</div>
      <div>
        <div class="txn-name">${escapeHtml(customer.name || "Unknown")}</div>
        <div class="txn-time">${lastDate}${customer.phone ? " • " + customer.phone : ""}</div>
      </div>
    </div>
    <div style="text-align: right; min-width: 90px;">
      <div style="font-size: 12px; font-weight: 600; color: ${color}; margin-bottom: 2px;">
        ${balanceLabel}
      </div>
      <div style="font-size: 17px; font-weight: 800; color: ${color};">
        ${formatPaise(absBalance)}
      </div>
    </div>`;

  card.addEventListener("click", () => viewCustomerHistory(customer.id));
  card.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") viewCustomerHistory(customer.id);
  });

  return card;
}

// ─── Navigation ───────────────────────────────────────────────────────────────
function viewCustomerHistory(customerId) {
  window.location.href = `history.html?customer=${encodeURIComponent(customerId)}`;
}

// ─── Add Customer Modal ───────────────────────────────────────────────────────
function openAddModal() {
  const modal = document.getElementById("add-customer-modal");
  if (modal) {
    modal.style.display = "flex";
    document.getElementById("customer-name-input").focus();
  }
}

function closeAddModal() {
  const modal = document.getElementById("add-customer-modal");
  if (modal) modal.style.display = "none";
  document.getElementById("customer-name-input").value = "";
  document.getElementById("customer-phone-input").value = "";
  const confirmRow = document.getElementById("similar-confirm-row");
  if (confirmRow) confirmRow.style.display = "none";
  isAddingCustomer = false;
  setSaveBtnLoading(false);
}

async function handleAddCustomer() {
  if (isAddingCustomer) return;

  const nameInput = document.getElementById("customer-name-input");
  const phoneInput = document.getElementById("customer-phone-input");
  const confirmCheckbox = document.getElementById("confirm-similar");

  const name = nameInput.value.trim();
  const phone = phoneInput.value.trim();

  if (!name) {
    showToast(t("pleaseEnterName", "Please enter customer name"), "error");
    nameInput.focus();
    return;
  }

  isAddingCustomer = true;
  setSaveBtnLoading(true);

  const confirm = confirmCheckbox && confirmCheckbox.checked;
  const res = await addCustomerApi(name, phone, confirm);

  setSaveBtnLoading(false);

  if (!res.ok && res.status === 409 && res.data && res.data.similar_exists) {
    isAddingCustomer = false;
    const confirmRow = document.getElementById("similar-confirm-row");
    if (confirmRow) {
      const existing = res.data.similar_name || "a similar customer";
      document.getElementById("similar-name-text").textContent = existing;
      confirmRow.style.display = "block";
    }
    showToast(`${t("similarFound", "Similar customer found:")} ${res.data.similar_name || ""}`, "error");
    return;
  }

  isAddingCustomer = false;

  if (res.ok) {
    showToast(t("customerAddedSuccess", "✓ Customer added successfully"), "success");
    closeAddModal();
    loadCustomers();
  } else {
    showToast(res.error || "Failed to add customer", "error");
  }
}

// ─── UI Helpers ───────────────────────────────────────────────────────────────
function setSaveBtnLoading(loading) {
  const btn = document.getElementById("btn-save-customer");
  if (!btn) return;
  btn.disabled = loading;
  btn.textContent = loading ? t("savingBtn", "Saving...") : t("saveBtn", "Save");
}

function showListLoading(show) {
  const container = document.getElementById("customer-list");
  if (!container) return;
  if (show) {
    container.innerHTML = `
      <div style="text-align: center; padding: 40px 20px; color: #9e9e9e;">
        <div class="spinner" style="margin: 0 auto 12px;"></div>
        <div>${t("loadingCustomers", "Loading customers...")}</div>
      </div>`;
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
