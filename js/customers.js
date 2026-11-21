/**
 * customers.js — Customer list, search, add, and history navigation for Bolta Khata.
 */

// ─── State ────────────────────────────────────────────────────────────────────
let allCustomers = [];   // full list fetched from API
let isAddingCustomer = false; // prevent double-submit

// ─── On Page Load ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  if (!checkAuth()) return;

  // Load shop name in header
  const shop = typeof getShop === "function" ? getShop() : null;
  const shopEl = document.getElementById("shop-name");
  if (shopEl && shop) shopEl.textContent = shop.shop_name || "My Store";

  // Language toggle
  const langBtn = document.getElementById("lang-toggle");
  if (langBtn) {
    const currentLang = typeof getLang === "function" ? getLang() : "en";
    langBtn.textContent = currentLang === "en" ? "हिं" : "EN";
    langBtn.addEventListener("click", () => {
      const lang = typeof getLang === "function" ? getLang() : "en";
      const next = lang === "en" ? "hi" : "en";
      if (typeof setLang === "function") setLang(next);
      langBtn.textContent = next === "en" ? "हिं" : "EN";
    });
  }

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

  // Load customer list
  loadCustomers();
  initNavbar("customers");
});

// ─── Load Customers ───────────────────────────────────────────────────────────
/**
 * Fetch all customers from API and render them.
 * Falls back to demo data if backend is offline.
 */
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
/**
 * Filter the already-loaded customer list locally by name/phone.
 * @param {string} query
 */
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
/**
 * Build and display customer cards.
 * @param {Array} list - Array of customer objects
 */
function renderCustomers(list) {
  const container = document.getElementById("customer-list");
  if (!container) return;

  if (!list || list.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding:40px 20px; color:#9e9e9e;">
        <div style="font-size:48px; margin-bottom:12px;">👤</div>
        <div style="font-size:17px; font-weight:600; margin-bottom:4px;">कोई ग्राहक नहीं</div>
        <div style="font-size:14px;">No customers yet</div>
        <div style="font-size:13px; margin-top:8px;">Add your first customer using the + button above</div>
      </div>`;
    return;
  }

  container.innerHTML = "";
  list.forEach((c) => {
    const card = buildCustomerCard(c);
    container.appendChild(card);
  });
}

/**
 * Build a single customer card DOM element.
 * @param {object} customer
 * @returns {HTMLElement}
 */
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

  const lastDate = customer.last_activity_at
    ? formatDate(customer.last_activity_at)
    : "No activity";

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
        <div class="txn-time">Last: ${lastDate}${customer.phone ? " • " + customer.phone : ""}</div>
      </div>
    </div>
    <div style="text-align:right; min-width:90px;">
      <div style="font-size:12px; font-weight:600; color:${isCredit ? "#2E7D32" : "#c62828"}; margin-bottom:2px;">
        ${isCredit ? "वसूलना है" : "देना है"}<br>
        <span style="font-size:11px; font-weight:400;">${isCredit ? "To collect" : "To pay"}</span>
      </div>
      <div style="font-size:17px; font-weight:800; color:${isCredit ? "#2E7D32" : "#c62828"};">
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
/**
 * Navigate to history.html pre-filtered for a customer.
 * @param {number|string} customerId
 */
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

/**
 * Handle add-customer form submission.
 * Deals with 409 "similar exists" confirmation flow.
 */
async function handleAddCustomer() {
  if (isAddingCustomer) return;

  const nameInput = document.getElementById("customer-name-input");
  const phoneInput = document.getElementById("customer-phone-input");
  const confirmCheckbox = document.getElementById("confirm-similar");

  const name = nameInput.value.trim();
  const phone = phoneInput.value.trim();

  if (!name) {
    showToast("Please enter customer name / नाम डालें", "error");
    nameInput.focus();
    return;
  }

  isAddingCustomer = true;
  setSaveBtnLoading(true);

  const confirm = confirmCheckbox && confirmCheckbox.checked;
  const res = await addCustomerApi(name, phone, confirm);

  setSaveBtnLoading(false);

  // 409 — similar customer exists, ask for confirmation
  if (!res.ok && res.status === 409 && res.data && res.data.similar_exists) {
    isAddingCustomer = false;
    const confirmRow = document.getElementById("similar-confirm-row");
    if (confirmRow) {
      const existing = res.data.similar_name || "a similar customer";
      document.getElementById("similar-name-text").textContent = existing;
      confirmRow.style.display = "block";
    }
    showToast(`Similar customer found: ${res.data.similar_name || ""}`, "error");
    return;
  }

  isAddingCustomer = false;

  if (res.ok) {
    showToast("✓ Customer added / ग्राहक जोड़ा गया", "success");
    closeAddModal();
    loadCustomers(); // refresh list
  } else {
    showToast(res.error || "Failed to add customer", "error");
  }
}

// ─── UI Helpers ───────────────────────────────────────────────────────────────
function setSaveBtnLoading(loading) {
  const btn = document.getElementById("btn-save-customer");
  if (!btn) return;
  btn.disabled = loading;
  btn.textContent = loading ? "Saving…" : "Save / सहेजें";
}

function showListLoading(show) {
  const container = document.getElementById("customer-list");
  if (!container) return;
  if (show) {
    container.innerHTML = `
      <div style="text-align:center; padding:40px 20px; color:#9e9e9e;">
        <div class="spinner" style="margin:0 auto 12px;"></div>
        <div>Loading customers…</div>
      </div>`;
  }
}

/**
 * Escape HTML special characters to prevent XSS.
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
