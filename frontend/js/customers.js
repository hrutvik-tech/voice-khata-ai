/**
 * customers.js — Customer list, search, add, and history navigation for Bolta Khata.
 * Ensures single-language display (English by default, switches cleanly to Hindi),
 * with complete bilingual translation of names, counts, cards, and modals.
 */

// ─── Bilingual Name Dictionary ──────────────────────────────────────────────
const NAME_MAP_EN_TO_HI = {
  "ramesh sharma": "रमेश शर्मा",
  "ramesh kumar": "रमेश कुमार",
  "ramesh": "रमेश",
  "suresh verma": "सुरेश वर्मा",
  "suresh": "सुरेश",
  "anita devi": "अनिता देवी",
  "anita": "अनिता",
  "anil gupta": "अनिल गुप्ता",
  "anil": "अनिल",
  "priya singh": "प्रिया सिंह",
  "priya": "प्रिया",
  "sunil kumar": "सुनील कुमार",
  "sunil": "सुनील",
  "rahul": "राहुल",
  "amit": "अमित",
  "rohit": "रोहित",
  "deepak": "दीपक",
  "manoj": "मनोज",
  "vikas": "विकास",
  "pooja": "पूजा",
  "neha": "नेहा",
  "rekha": "रेखा",
  "sunita": "सुनीता",
  "geeta": "गीता",
  "sharma": "शर्मा",
  "verma": "वर्मा",
  "singh": "सिंह",
  "gupta": "गुप्ता",
  "devi": "देवी",
  "kumar": "कुमार",
  "customer": "ग्राहक",
  "offline customer": "ऑफ़लाइन ग्राहक",
};

const NAME_MAP_HI_TO_EN = {
  "रमेश शर्मा": "Ramesh Sharma",
  "रमेश कुमार": "Ramesh Kumar",
  "रमेश": "Ramesh",
  "सुरेश वर्मा": "Suresh Verma",
  "सुरेश": "Suresh",
  "अनिता देवी": "Anita Devi",
  "अनिता": "Anita",
  "अनिल गुप्ता": "Anil Gupta",
  "अनिल": "Anil",
  "प्रिया सिंह": "Priya Singh",
  "प्रिया": "Priya",
  "सुनील कुमार": "Sunil Kumar",
  "सुनील": "Sunil",
  "राहुल": "Rahul",
  "अमित": "Amit",
  "रोहित": "Rohit",
  "दीपक": "Deepak",
  "मनोज": "Manoj",
  "विकास": "Vikas",
  "पूजा": "Pooja",
  "नेहा": "Neha",
  "रेखा": "Rekha",
  "सुनीता": "Sunita",
  "गीता": "Geeta",
  "शर्मा": "Sharma",
  "वर्मा": "Verma",
  "सिंह": "Singh",
  "गुप्ता": "Gupta",
  "देवी": "Devi",
  "कुमार": "Kumar",
  "ग्राहक": "Customer",
  "ऑफ़लाइन ग्राहक": "Offline Customer",
};

/**
 * Returns localized customer name based on active language.
 */
function getLocalizedCustomerName(customer, lang) {
  if (!customer) return "Unknown";
  const rawName = (customer.name || "").trim();
  if (!rawName) return "Customer";

  if (lang === "hi") {
    if (customer.name_hi) return customer.name_hi;
    const lower = rawName.toLowerCase();
    if (NAME_MAP_EN_TO_HI[lower]) return NAME_MAP_EN_TO_HI[lower];

    const parts = lower.split(/\s+/);
    const translated = parts.map((p) => NAME_MAP_EN_TO_HI[p] || p);
    if (translated.some((p) => /[\u0900-\u097F]/.test(p))) {
      return translated.join(" ");
    }
    return rawName;
  } else {
    // English
    if (customer.name_en) return customer.name_en;
    if (NAME_MAP_HI_TO_EN[rawName]) return NAME_MAP_HI_TO_EN[rawName];

    const parts = rawName.split(/\s+/);
    const translated = parts.map((p) => NAME_MAP_HI_TO_EN[p] || p);
    if (translated.some((p) => /^[A-Za-z]/.test(p))) {
      return translated.join(" ");
    }
    return rawName;
  }
}

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
  if (addBtn) {
    addBtn.addEventListener("click", (e) => {
      e.preventDefault();
      openAddModal();
    });
  }

  // Modal close button
  const closeBtn = document.getElementById("modal-close");
  if (closeBtn) {
    closeBtn.addEventListener("click", (e) => {
      e.preventDefault();
      closeAddModal();
    });
  }

  // Modal backdrop click closes modal
  const modalOverlay = document.getElementById("add-customer-modal");
  if (modalOverlay) {
    modalOverlay.addEventListener("click", (e) => {
      if (e.target === modalOverlay) closeAddModal();
    });
  }

  // Add customer form submit
  const saveBtn = document.getElementById("btn-save-customer");
  if (saveBtn) {
    saveBtn.addEventListener("click", (e) => {
      e.preventDefault();
      handleAddCustomer();
    });
  }

  // Allow pressing Enter in customer name/phone inputs to save
  const nameInput = document.getElementById("customer-name-input");
  const phoneInput = document.getElementById("customer-phone-input");
  [nameInput, phoneInput].forEach((inp) => {
    if (inp) {
      inp.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          handleAddCustomer();
        }
      });
    }
  });

  // Listen for language changes and re-render list + translations
  window.addEventListener("languageChanged", () => {
    const query = (document.getElementById("search-input")?.value || "").trim();
    searchCustomers(query);
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
  const currentLang = typeof currentLanguage === "function" ? currentLanguage() : "en";

  const filtered = allCustomers.filter((c) => {
    const nameOrig = (c.name || "").toLowerCase();
    const nameLoc = getLocalizedCustomerName(c, currentLang).toLowerCase();
    const phone = (c.phone || "").toLowerCase();
    return nameOrig.includes(q) || nameLoc.includes(q) || phone.includes(q);
  });
  renderCustomers(filtered);
}

// ─── Render ───────────────────────────────────────────────────────────────────
function renderCustomers(list) {
  const container = document.getElementById("customer-list");
  const countTextEl = document.getElementById("customer-count-text");
  if (!container) return;

  const currentLang = typeof currentLanguage === "function" ? currentLanguage() : "en";

  // Update customer count badge
  if (countTextEl) {
    const count = list ? list.length : 0;
    if (count > 0) {
      const isSingle = count === 1;
      const label = isSingle
        ? t("customerCountSingle", "1 customer")
        : `${count} ${t("customerCountPlural", "customers")}`;
      countTextEl.textContent = label;
    } else {
      countTextEl.textContent = `0 ${t("customerCountPlural", "customers")}`;
    }
  }

  // Empty state
  if (!list || list.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 48px 20px; color: #9e9e9e;">
        <div style="font-size: 54px; margin-bottom: 12px;">👤</div>
        <div style="font-size: 18px; font-weight: 700; color: #424242; margin-bottom: 6px;">
          ${t("noCustomersYet", "No customers yet")}
        </div>
        <div style="font-size: 14px; color: #757575; max-width: 280px; margin: 0 auto;">
          ${t("noCustomersSub", "Add your first customer using the + button above")}
        </div>
      </div>`;
    return;
  }

  container.innerHTML = "";
  list.forEach((c) => {
    const card = buildCustomerCard(c, currentLang);
    container.appendChild(card);
  });
}

function buildCustomerCard(customer, currentLang) {
  const balance = customer.balance_paise || 0;
  const isCredit = balance >= 0;
  const absBalance = Math.abs(balance);

  const locName = getLocalizedCustomerName(customer, currentLang);

  // Avatar initial
  const initial = locName.charAt(0).toUpperCase() || "?";

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
  card.setAttribute("aria-label", `View ${locName}'s transactions`);

  card.innerHTML = `
    <div class="txn-info">
      <div class="txn-avatar" style="font-size: 18px; font-weight: 800; background: #E8F5E9; color: #2E7D32;">${initial}</div>
      <div>
        <div class="txn-name" style="font-size: 16px; font-weight: 700; color: #1F2937;">${escapeHtml(locName)}</div>
        <div class="txn-time" style="font-size: 12px; color: #757575;">${lastDate}${customer.phone ? " • " + customer.phone : ""}</div>
      </div>
    </div>
    <div style="text-align: right; min-width: 90px;">
      <div style="font-size: 12px; font-weight: 700; color: ${color}; margin-bottom: 2px;">
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
    modal.classList.add("open");

    const nameInput = document.getElementById("customer-name-input");
    if (nameInput) {
      nameInput.value = "";
      setTimeout(() => nameInput.focus(), 60);
    }
    const phoneInput = document.getElementById("customer-phone-input");
    if (phoneInput) phoneInput.value = "";
    const confirmRow = document.getElementById("similar-confirm-row");
    if (confirmRow) confirmRow.style.display = "none";
  }
}

function closeAddModal() {
  const modal = document.getElementById("add-customer-modal");
  if (modal) {
    modal.classList.remove("open");
    modal.style.display = "none";
  }
  const nameInput = document.getElementById("customer-name-input");
  if (nameInput) nameInput.value = "";
  const phoneInput = document.getElementById("customer-phone-input");
  if (phoneInput) phoneInput.value = "";
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

  const name = (nameInput?.value || "").trim();
  const phone = (phoneInput?.value || "").trim();

  if (!name) {
    showToast(t("pleaseEnterName", "Please enter customer name"), "error");
    if (nameInput) nameInput.focus();
    return;
  }

  isAddingCustomer = true;
  setSaveBtnLoading(true);

  const confirm = confirmCheckbox && confirmCheckbox.checked;
  const res = await addCustomerApi(name, phone, confirm);

  setSaveBtnLoading(false);
  isAddingCustomer = false;

  if (!res.ok && res.status === 409 && res.data && res.data.similar_exists) {
    const confirmRow = document.getElementById("similar-confirm-row");
    if (confirmRow) {
      const existing = res.data.similar_name || "a similar customer";
      document.getElementById("similar-name-text").textContent = existing;
      confirmRow.style.display = "block";
    }
    showToast(`${t("similarFound", "Similar customer found:")} ${res.data.similar_name || ""}`, "error");
    return;
  }

  if (res.ok) {
    showToast(t("customerAddedSuccess", "✓ Customer added successfully"), "success");
    closeAddModal();
    await loadCustomers();
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
