/**
 * storage.js — LocalStorage helpers for Bolta Khata.
 * Keys:
 * - bk_token: JWT auth token
 * - bk_shop: Shop JSON details
 * - bk-offline: Offline turns queue (max 20 items)
 */

const TOKEN_KEY = "bk_token";
const SHOP_KEY = "bk_shop";
const LANG_KEY = "bk_lang";
const OFFLINE_KEY = "bk-offline";
const OFFLINE_QUEUE_MAX = 20;

/**
 * Get JWT auth token.
 * @returns {string|null}
 */
function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch (e) {
    console.error("Storage access error:", e);
    return null;
  }
}

/**
 * Save JWT auth token.
 * @param {string} token
 */
function setToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch (e) {
    console.error("Storage write error:", e);
  }
}

/**
 * Read and parse active shop metadata.
 * @returns {object|null}
 */
function getShop() {
  try {
    const raw = localStorage.getItem(SHOP_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    console.error("Shop parse error:", e);
    return null;
  }
}

/**
 * Store shop metadata.
 * @param {object} shop
 */
function setShop(shop) {
  try {
    if (shop) {
      localStorage.setItem(SHOP_KEY, JSON.stringify(shop));
    } else {
      localStorage.removeItem(SHOP_KEY);
    }
  } catch (e) {
    console.error("Shop write error:", e);
  }
}

/**
 * Get preferred UI language ('en' by default).
 * @returns {string}
 */
function getLang() {
  try {
    return localStorage.getItem(LANG_KEY) || "en";
  } catch (e) {
    return "en";
  }
}

/**
 * Save preferred UI language ('en' | 'hi').
 * @param {string} lang
 */
function setLang(lang) {
  try {
    localStorage.setItem(LANG_KEY, lang || "en");
  } catch (e) {
    console.error("Language write error:", e);
  }
}

/**
 * Clear authentication state (token and shop).
 */
function clearAuth() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(SHOP_KEY);
  } catch (e) {
    console.error("Clear auth error:", e);
  }
}

/**
 * Read queued offline voice turns.
 * @returns {Array}
 */
function getOfflineQueue() {
  try {
    const raw = localStorage.getItem(OFFLINE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    console.error("Offline queue read error:", e);
    return [];
  }
}

/**
 * Append an item to the offline turn queue (retaining at most OFFLINE_QUEUE_MAX).
 * @param {object} item
 */
function addToOfflineQueue(item) {
  try {
    const queue = getOfflineQueue();
    queue.push(item);
    // Keep max 20 items (drop oldest if exceeded)
    while (queue.length > OFFLINE_QUEUE_MAX) {
      queue.shift();
    }
    localStorage.setItem(OFFLINE_KEY, JSON.stringify(queue));
  } catch (e) {
    console.error("Offline queue write error:", e);
  }
}

/**
 * Clear the offline queue.
 */
function clearOfflineQueue() {
  try {
    localStorage.removeItem(OFFLINE_KEY);
  } catch (e) {
    console.error("Clear offline queue error:", e);
  }
}

// Export for module/script use
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    getToken,
    setToken,
    getShop,
    setShop,
    clearAuth,
    getOfflineQueue,
    addToOfflineQueue,
    clearOfflineQueue,
    OFFLINE_QUEUE_MAX,
  };
}
