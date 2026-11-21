/**
 * app.js — Shared utilities, auth checking, navbar management,
 * offline sync initialization, and service worker registration for Bolta Khata.
 */

/**
 * Check if the user is authenticated.
 * If not authenticated and not already on the login page, redirects to index.html.
 * @returns {boolean}
 */
function checkAuth() {
  const isLoginPage = window.location.pathname.endsWith("index.html") || window.location.pathname === "/";
  const token = typeof getToken === "function" ? getToken() : localStorage.getItem("bk_token");

  if (!token) {
    if (!isLoginPage) {
      window.location.href = "index.html";
    }
    return false;
  }
  return true;
}

/**
 * Display a floating toast notification.
 * @param {string} message - Text to display
 * @param {"success"|"error"|"info"} [type="info"] - Toast styling type
 */
function showToast(message, type = "info") {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;

  container.appendChild(toast);

  // Trigger animation
  requestAnimationFrame(() => {
    toast.classList.add("show");
  });

  // Auto remove after 3.5s
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 3500);
}

/**
 * Convert integer paise to Indian Rupee formatted string.
 * Example: 150000 -> "₹1,500", 10000000 -> "₹1,00,000"
 * @param {number} paise
 * @returns {string}
 */
function formatPaise(paise) {
  if (paise === null || paise === undefined || isNaN(paise)) {
    return "₹0";
  }
  const rupees = Math.round(paise / 100);
  return `₹${rupees.toLocaleString("en-IN")}`;
}

/**
 * Format an ISO date string into readable Indian format.
 * Example: "2026-11-21T10:00:00" -> "21 Nov 2026"
 * @param {string|Date} isoDate
 * @returns {string}
 */
function formatDate(isoDate) {
  if (!isoDate) return "";
  try {
    const d = new Date(isoDate);
    if (isNaN(d.getTime())) return String(isoDate);
    return d.toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch (e) {
    return String(isoDate);
  }
}

/**
 * Highlight the active tab in the bottom navigation bar.
 * @param {"home"|"customers"|"voice"|"history"} [activeTab]
 */
function initNavbar(activeTab) {
  const isLoginPage = window.location.pathname.endsWith("index.html") || window.location.pathname === "/";
  const navbar = document.querySelector(".navbar");

  // Login page should not show bottom navigation bar
  if (isLoginPage) {
    if (navbar) navbar.style.display = "none";
    return;
  }

  if (navbar) navbar.style.display = "flex";

  const currentPath = window.location.pathname.toLowerCase();
  const navItems = document.querySelectorAll(".nav-item");

  navItems.forEach((item) => {
    const tabName = item.getAttribute("data-tab");
    if (activeTab && tabName === activeTab) {
      item.classList.add("active");
    } else if (!activeTab && item.getAttribute("href") && currentPath.includes(item.getAttribute("href").toLowerCase())) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Update voice badge count on navbar if offline manager is present
  if (typeof updateVoiceBadge === "function") {
    updateVoiceBadge();
  }
}

/**
 * Initialize offline manager and check network connectivity.
 */
function initOffline() {
  if (typeof initOfflineManager === "function") {
    initOfflineManager();
  } else if (typeof updateVoiceBadge === "function") {
    updateVoiceBadge();
    if (typeof detectOnline === "function") {
      if (!detectOnline() && typeof showOfflineBanner === "function") {
        showOfflineBanner();
      } else if (typeof syncQueue === "function") {
        syncQueue();
      }
    }
  }
}

/**
 * Register Progressive Web App Service Worker.
 */
function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker
        .register("./sw.js")
        .then((reg) => {
          console.log("Bolta Khata Service Worker registered:", reg.scope);
        })
        .catch((err) => {
          console.warn("Service Worker registration failed:", err);
        });
    });
  }
}

// Global page initialization
function onAppInit() {
  const isLoginPage = window.location.pathname.endsWith("index.html") || window.location.pathname === "/";
  if (!isLoginPage) {
    checkAuth();
  }
  initNavbar();
  initOffline();
  registerServiceWorker();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", onAppInit);
} else {
  onAppInit();
}
