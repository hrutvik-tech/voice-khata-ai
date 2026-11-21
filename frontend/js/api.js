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
 * Calls POST /auth/login
 * @param {string} phone
 * @param {string} password
 * @returns {Promise<object>}
 */
async function login(phone, password) {
  return await apiCall("/auth/login", "POST", {
    phone: phone.trim(),
    pin: password.trim(),
    password: password.trim(),
  });
}

/**
 * Register new Kirana shop & owner.
 * Calls POST /auth/register
 * @param {string} shopName
 * @param {string} ownerName
 * @param {string} phone
 * @param {string} password
 * @returns {Promise<object>}
 */
async function register(shopName, ownerName, phone, password) {
  return await apiCall("/auth/register", "POST", {
    shop_name: shopName.trim(),
    owner_name: ownerName.trim(),
    phone: phone.trim(),
    pin: password.trim(),
    password: password.trim(),
  });
}

// Export for module/script use
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    BASE_URL,
    apiCall,
    login,
    register,
  };
}
