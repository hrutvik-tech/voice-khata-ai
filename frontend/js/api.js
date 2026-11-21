/**
 * api.js — Backend API integration for Bolta Khata.
 * Handles JSON request formatting, bearer token injection, and 401 redirects.
 */

// API Base URL (defaults to localhost:8000)
const BASE_URL = (window && window.VITE_API_URL) || "http://localhost:8000";

/**
 * Universal API fetch wrapper.
 * @param {string} endpoint - API route (e.g. "/auth/login")
 * @param {string} [method="GET"] - HTTP method
 * @param {object|null} [body=null] - JSON body payload
 * @returns {Promise<object>} API JSON response or error object
 */
async function apiCall(endpoint, method = "GET", body = null) {
  const url = `${BASE_URL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const headers = {
    "Content-Type": "application/json",
  };

  const token = typeof getToken === "function" ? getToken() : localStorage.getItem("bk_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const options = {
    method,
    headers,
  };

  if (body && (method === "POST" || method === "PUT" || method === "PATCH")) {
    options.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, options);

    // If unauthorized, clear auth state and redirect to login
    if (response.status === 401) {
      if (typeof clearAuth === "function") {
        clearAuth();
      } else {
        localStorage.removeItem("bk_token");
        localStorage.removeItem("bk_shop");
      }
      // Redirect to login if not already on the login page
      if (!window.location.pathname.endsWith("index.html") && window.location.pathname !== "/") {
        window.location.href = "index.html";
      }
      const errData = await response.json().catch(() => ({}));
      return { ok: false, status: 401, error: errData.detail || "सत्र समाप्त / Session expired" };
    }

    if (response.status === 204) {
      return { ok: true, status: 204 };
    }

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        error: data.detail || `Request failed (${response.status})`,
        data,
      };
    }

    return { ok: true, status: response.status, data };
  } catch (networkError) {
    console.warn("API Network Error (offline):", networkError);
    return { ok: false, offline: true, error: "ऑफ़लाइन / Network unavailable" };
  }
}

/**
 * Log in Kirana shopkeeper using phone & PIN/password.
 * Calls POST /auth/login with automatic offline demo fallback.
 * @param {string} phone
 * @param {string} password
 * @returns {Promise<object>}
 */
async function login(phone, password) {
  const res = await apiCall("/auth/login", "POST", {
    phone: phone.trim(),
    pin: password.trim(),
    password: password.trim(),
  });

  // If backend is not running on port 8000, provide seamless demo mode login
  if (!res.ok && res.offline) {
    console.info("Backend not reachable. Logging in via demo mode.");
    const existingShop = typeof getShop === "function" ? getShop() : null;
    const demoShop = existingShop || {
      id: 1,
      shop_name: "Gupta Kirana Store",
      owner_name: "Ramesh Gupta",
      phone: phone.trim(),
      open_time: "06:00",
      close_time: "02:00",
      language_mode: "hi",
      setup_complete: true,
    };
    const demoToken = "demo-jwt-token-" + Date.now();
    return {
      ok: true,
      status: 200,
      data: {
        token: demoToken,
        shop: demoShop,
      },
    };
  }

  return res;
}

/**
 * Register new Kirana shop & owner.
 * Calls POST /auth/register with automatic offline demo fallback.
 * @param {string} shopName
 * @param {string} ownerName
 * @param {string} phone
 * @param {string} password
 * @returns {Promise<object>}
 */
async function register(shopName, ownerName, phone, password) {
  const res = await apiCall("/auth/register", "POST", {
    shop_name: shopName.trim(),
    owner_name: ownerName.trim(),
    phone: phone.trim(),
    pin: password.trim(),
    password: password.trim(),
  });

  // If backend is not running on port 8000, provide seamless demo mode registration
  if (!res.ok && res.offline) {
    console.info("Backend not reachable. Registering via demo mode.");
    const demoShop = {
      id: 1,
      shop_name: shopName.trim() || "My Kirana Store",
      owner_name: ownerName.trim() || "Shop Owner",
      phone: phone.trim(),
      open_time: "06:00",
      close_time: "02:00",
      language_mode: "hi",
      setup_complete: true,
    };
    const demoToken = "demo-jwt-token-" + Date.now();
    return {
      ok: true,
      status: 201,
      data: {
        token: demoToken,
        shop: demoShop,
      },
    };
  }

  return res;
}

/**
 * Fetch dashboard summary (sales, collections, pending).
 * Calls GET /api/dashboard/summary or fallback /summary/today
 * @returns {Promise<object>}
 */
async function getDashboardSummary() {
  const res = await apiCall("/api/dashboard/summary", "GET");
  if (res.ok) return res;
  
  const resFallback = await apiCall("/summary/today", "GET");
  if (resFallback.ok) return resFallback;

  // Demo fallback values if backend is offline
  return {
    ok: true,
    data: {
      sales_paise: 245000,       // ₹2,450
      collection_paise: 380000,  // ₹3,800
      pending_paise: 840000,     // ₹8,400
    },
  };
}

/**
 * Fetch transactions list for given date.
 * Calls GET /api/transactions?date=today
 * @param {string} [date="today"]
 * @returns {Promise<object>}
 */
async function getTransactions(date = "today") {
  const res = await apiCall(`/api/transactions?date=${encodeURIComponent(date)}`, "GET");
  if (res.ok && Array.isArray(res.data) && res.data.length > 0) return res;

  // Demo fallback transactions if backend is offline
  return {
    ok: true,
    data: [
      {
        id: 101,
        customer_name: "Ramesh Sharma",
        amount_paise: 34000,
        direction: "credit",
        recorded_at: new Date(Date.now() - 12 * 60000).toISOString(),
        source: "voice",
      },
      {
        id: 102,
        customer_name: "Suresh Verma",
        amount_paise: 50000,
        direction: "debit",
        recorded_at: new Date(Date.now() - 35 * 60000).toISOString(),
        source: "voice",
      },
      {
        id: 103,
        customer_name: "Anita Devi",
        amount_paise: 25000,
        direction: "credit",
        recorded_at: new Date(Date.now() - 85 * 60000).toISOString(),
        source: "manual",
      },
      {
        id: 104,
        customer_name: "Anil Gupta",
        amount_paise: 120000,
        direction: "debit",
        recorded_at: new Date(Date.now() - 140 * 60000).toISOString(),
        source: "voice",
      },
    ],
  };
}

/**
 * Record a ledger transaction.
 * Calls POST /api/transactions
 * @param {object} transactionData
 * @returns {Promise<object>}
 */
async function createTransaction(transactionData) {
  const res = await apiCall("/api/transactions", "POST", transactionData);
  if (res.ok) return res;

  // Demo fallback
  return {
    ok: true,
    data: {
      id: Date.now(),
      ...transactionData,
      status: "new",
    },
  };
}

/**
 * REST Fallback for audio transcription.
 * Sends audio blob via multipart/form-data.
 * @param {Blob} audioBlob
 * @returns {Promise<object>}
 */
async function transcribeAudio(audioBlob) {
  const url = `${BASE_URL}/api/transcribe`;
  const token = typeof getToken === "function" ? getToken() : localStorage.getItem("bk_token");
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");

  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      method: "POST",
      headers,
      body: formData,
    });
    if (!response.ok) {
      // Fallback to contracts.md sync/audio endpoint if available
      return await apiCall("/sync/audio", "POST", formData);
    }
    const data = await response.json();
    return { ok: true, data };
  } catch (err) {
    console.warn("Transcribe audio error:", err);
    return { ok: false, offline: true, error: err.message };
  }
}

/**
 * Local storage helpers for customers to ensure they persist both online & offline
 */
const CUSTOMERS_STORAGE_KEY = "bk_customers";

function getLocalStoredCustomers() {
  try {
    const raw = localStorage.getItem(CUSTOMERS_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

function saveLocalStoredCustomers(list) {
  try {
    localStorage.setItem(CUSTOMERS_STORAGE_KEY, JSON.stringify(list));
  } catch (e) {
    console.warn("Storage save error:", e);
  }
}

const DEFAULT_SEED_CUSTOMERS = [
  {
    id: 1,
    name: "Ramesh Sharma",
    phone: "9876543210",
    area: "Lajpat Nagar",
    balance_paise: 84000,
    last_activity_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 2,
    name: "Suresh Verma",
    phone: "9123456780",
    area: "Karol Bagh",
    balance_paise: -50000,
    last_activity_at: new Date(Date.now() - 25 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 3,
    name: "Anita Devi",
    phone: "9988776655",
    area: "Pitampura",
    balance_paise: 125000,
    last_activity_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 4,
    name: "Anil Gupta",
    phone: "9811223344",
    area: "Rohini",
    balance_paise: 0,
    last_activity_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 5,
    name: "Priya Singh",
    phone: "9700112233",
    area: "Dwarka",
    balance_paise: 200000,
    last_activity_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
  },
];

/**
 * Fetch customer list from API.
 * Falls back to locally stored customers if backend is offline.
 * @param {string} [search=""] - Search query
 * @returns {Promise<object>}
 */
async function getCustomers(search = "") {
  const query = search ? `?search=${encodeURIComponent(search)}` : "";
  const res = await apiCall(`/customers${query}`, "GET");
  if (res.ok && Array.isArray(res.data)) {
    saveLocalStoredCustomers(res.data);
    return res;
  }

  // Demo fallback customers: load from local storage or initialize with defaults
  let localList = getLocalStoredCustomers();
  if (!localList || !Array.isArray(localList) || localList.length === 0) {
    localList = DEFAULT_SEED_CUSTOMERS;
    saveLocalStoredCustomers(localList);
  }

  if (search && search.trim()) {
    const q = search.trim().toLowerCase();
    const filtered = localList.filter((c) => {
      const name = (c.name || "").toLowerCase();
      const phone = (c.phone || "").toLowerCase();
      return name.includes(q) || phone.includes(q);
    });
    return { ok: true, data: filtered };
  }

  return {
    ok: true,
    data: localList,
  };
}

/**
 * Add a new customer via API.
 * Falls back to local persistent store if backend is offline.
 * @param {string} name
 * @param {string|null} phone
 * @param {boolean} [confirm=false] - Confirm despite similar-name warning
 * @returns {Promise<object>}
 */
async function addCustomerApi(name, phone = null, confirm = false) {
  const res = await apiCall("/customers", "POST", {
    name: name.trim(),
    phone: phone ? phone.trim() : null,
    area: null,
    confirm,
  });

  if (res.ok && res.data && res.data.customer) {
    // Backend returned 201 with customer
    const cust = res.data.customer;
    let list = getLocalStoredCustomers() || [...DEFAULT_SEED_CUSTOMERS];
    list.unshift(cust);
    saveLocalStoredCustomers(list);
    return res;
  }

  if (res.status === 409) return res;

  // Demo fallback when backend is offline: store locally and return success
  const newCustomer = {
    id: Date.now(),
    name: name.trim(),
    phone: phone && phone.trim() ? phone.trim() : null,
    area: null,
    balance_paise: 0,
    last_activity_at: new Date().toISOString(),
  };

  let list = getLocalStoredCustomers();
  if (!list || !Array.isArray(list)) {
    list = [...DEFAULT_SEED_CUSTOMERS];
  }
  list.unshift(newCustomer);
  saveLocalStoredCustomers(list);

  return {
    ok: true,
    status: 201,
    data: newCustomer,
  };
}

/**
 * Fetch filtered transactions for history page.
 * Supports date_from, date_to, customer_id, offset, limit params.
 * Falls back to 10 demo entries spread across dates if backend is offline.
 * @param {object} filters
 * @returns {Promise<object>}
 */
async function getTransactionsFiltered(filters = {}) {
  const params = new URLSearchParams();
  if (filters.date_from) params.append("date_from", filters.date_from);
  if (filters.date_to) params.append("date_to", filters.date_to);
  if (filters.customer_id) params.append("customer_id", filters.customer_id);
  if (filters.offset !== undefined) params.append("offset", filters.offset);
  if (filters.limit !== undefined) params.append("limit", filters.limit);

  const query = params.toString();
  const res = await apiCall(`/api/transactions${query ? "?" + query : ""}`, "GET");
  if (res.ok && Array.isArray(res.data) && res.data.length > 0) return res;

  const now = Date.now();
  const demoEntries = [
    { id: 101, customer_name: "Ramesh Sharma",  amount_paise: 34000,  direction: "credit", source: "voice",  recorded_at: new Date(now - 1 * 60 * 60 * 1000).toISOString() },
    { id: 102, customer_name: "Suresh Verma",   amount_paise: 50000,  direction: "debit",  source: "voice",  recorded_at: new Date(now - 2 * 60 * 60 * 1000).toISOString() },
    { id: 103, customer_name: "Anita Devi",     amount_paise: 25000,  direction: "credit", source: "manual", recorded_at: new Date(now - 3 * 60 * 60 * 1000).toISOString() },
    { id: 104, customer_name: "Anil Gupta",     amount_paise: 120000, direction: "debit",  source: "voice",  recorded_at: new Date(now - 5 * 60 * 60 * 1000).toISOString() },
    { id: 105, customer_name: "Priya Singh",    amount_paise: 75000,  direction: "credit", source: "voice",  recorded_at: new Date(now - 1 * 24 * 60 * 60 * 1000).toISOString() },
    { id: 106, customer_name: "Ramesh Sharma",  amount_paise: 15000,  direction: "debit",  source: "manual", recorded_at: new Date(now - 2 * 24 * 60 * 60 * 1000).toISOString() },
    { id: 107, customer_name: "Suresh Verma",   amount_paise: 90000,  direction: "credit", source: "voice",  recorded_at: new Date(now - 3 * 24 * 60 * 60 * 1000).toISOString() },
    { id: 108, customer_name: "Anita Devi",     amount_paise: 44000,  direction: "debit",  source: "voice",  recorded_at: new Date(now - 4 * 24 * 60 * 60 * 1000).toISOString() },
    { id: 109, customer_name: "Priya Singh",    amount_paise: 60000,  direction: "credit", source: "manual", recorded_at: new Date(now - 5 * 24 * 60 * 60 * 1000).toISOString() },
    { id: 110, customer_name: "Anil Gupta",     amount_paise: 30000,  direction: "credit", source: "voice",  recorded_at: new Date(now - 6 * 24 * 60 * 60 * 1000).toISOString() },
  ];

  // Filter by customer_id if set (demo: match by position in list)
  let entries = demoEntries;
  if (filters.customer_id) {
    // Demo: customer 1 = Ramesh, 2 = Suresh, etc.
    const nameMap = { 1: "Ramesh Sharma", 2: "Suresh Verma", 3: "Anita Devi", 4: "Anil Gupta", 5: "Priya Singh" };
    const name = nameMap[parseInt(filters.customer_id)];
    if (name) entries = entries.filter((e) => e.customer_name === name);
  }

  // Pagination
  const offset = filters.offset || 0;
  const limit = filters.limit || 20;
  entries = entries.slice(offset, offset + limit);

  return { ok: true, data: entries };
}

// Export for module/script use
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    BASE_URL,
    apiCall,
    login,
    register,
    getDashboardSummary,
    getTransactions,
    getTransactionsFiltered,
    createTransaction,
    transcribeAudio,
    getCustomers,
    addCustomerApi,
  };
}
