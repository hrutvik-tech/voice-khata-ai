/**
 * app.js — Shared utilities, auth checking, and navbar management for Bolta Khata.
 */

/**
 * Check if the user is authenticated.
 * If not authenticated, redirects to index.html.
 */
function checkAuth() {
  const token = typeof getToken === "function" ? getToken() : localStorage.getItem("bk_token");
  if (!token) {
    if (!window.location.pathname.endsWith("index.html") && window.location.pathname !== "/") {
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
  const currentPath = window.location.pathname.toLowerCase();
  const navItems = document.querySelectorAll(".nav-item");

  navItems.forEach((item) => {
    const tabName = item.getAttribute("data-tab");
    if (activeTab && tabName === activeTab) {
      item.classList.add("active");
    } else if (!activeTab && currentPath.includes(item.getAttribute("href").toLowerCase())) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });
}

// Auto-run navbar highlight if DOM is already loaded
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => initNavbar());
} else {
  initNavbar();
}
