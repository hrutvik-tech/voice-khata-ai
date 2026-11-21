/**
 * offline.js — Offline sync manager for Bolta Khata.
 * Handles online/offline detection, UI banners, queued offline transactions,
 * automatic background sync, and voice tab badges.
 */

/**
 * Check current network connectivity.
 * @returns {boolean}
 */
function detectOnline() {
  return navigator.onLine;
}

/**
 * Show yellow "ऑफ़लाइन मोड / Offline Mode" banner at the top of the page.
 */
function showOfflineBanner() {
  let banner = document.getElementById("offline-indicator-banner");
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "offline-indicator-banner";
    banner.className = "offline-banner";
    const container = document.querySelector(".app-container") || document.body;
    container.insertBefore(banner, container.firstChild);
  }
  banner.textContent = "⚠️ ऑफ़लाइन मोड / Offline Mode";
  banner.classList.remove("hidden");
  banner.style.display = "flex";
}

/**
 * Hide the offline banner when back online.
 */
function hideOfflineBanner() {
  const banner = document.getElementById("offline-indicator-banner");
  if (banner) {
    banner.classList.add("hidden");
    banner.style.display = "none";
  }
}

/**
 * Update the badge count on the Voice navigation tab.
 * Shows the number of queued offline transactions.
 */
function updateVoiceBadge() {
  const queue = typeof getOfflineQueue === "function" ? getOfflineQueue() : [];
  const count = queue.length;

  const micButtons = document.querySelectorAll(".nav-mic-btn, [data-tab='voice']");
  micButtons.forEach((btn) => {
    let badge = btn.querySelector(".voice-badge");
    if (count > 0) {
      if (!badge) {
        badge = document.createElement("span");
        badge.className = "voice-badge";
        btn.appendChild(badge);
      }
      badge.textContent = count > 99 ? "99+" : count;
      badge.style.display = "flex";
    } else if (badge) {
      badge.style.display = "none";
    }
  });
}

/**
 * Sync queued transactions with the backend one by one.
 * On success: removes item from queue, shows toast with count.
 * On failure: keeps item in queue to retry later.
 */
async function syncQueue() {
  if (!detectOnline()) {
    showOfflineBanner();
    return;
  }

  const queue = typeof getOfflineQueue === "function" ? getOfflineQueue() : [];
  if (!queue || queue.length === 0) {
    updateVoiceBadge();
    return;
  }

  let syncedCount = 0;
  const remaining = [...queue];

  while (remaining.length > 0) {
    const item = remaining[0];
    try {
      if (typeof createTransaction === "function") {
        const res = await createTransaction(item);
        if (res && (res.ok || res.status === 201 || res.status === 200)) {
          // Successfully synced, remove from queue
          remaining.shift();
          syncedCount++;
          if (typeof setOfflineQueue === "function") {
            setOfflineQueue(remaining);
          } else {
            localStorage.setItem("bk-offline", JSON.stringify(remaining));
          }
          updateVoiceBadge();
          continue;
        }
      }
      // If response not ok or request failed, stop and retry later
      break;
    } catch (err) {
      console.warn("Sync queue item failed:", err);
      break;
    }
  }

  if (syncedCount > 0) {
    const msg = `${syncedCount} लेन-देन sync हो गए / ${syncedCount} transactions synced`;
    if (typeof showToast === "function") {
      showToast(msg, "success");
    } else {
      console.log(msg);
    }
  }

  updateVoiceBadge();
}

/**
 * Initialize offline manager: checks status, binds events, and auto-syncs.
 */
function initOffline() {
  if (detectOnline()) {
    hideOfflineBanner();
    syncQueue();
  } else {
    showOfflineBanner();
  }
  updateVoiceBadge();
}

// Global connectivity event listeners
window.addEventListener("online", () => {
  hideOfflineBanner();
  if (typeof showToast === "function") {
    showToast("इंटरनेट वापस आ गया / Online", "info");
  }
  syncQueue();
});

window.addEventListener("offline", () => {
  showOfflineBanner();
  updateVoiceBadge();
  if (typeof showToast === "function") {
    showToast("ऑफ़लाइन मोड / Offline Mode", "info");
  }
});

// Auto-run when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initOffline);
} else {
  initOffline();
}

// Export for module systems
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    detectOnline,
    showOfflineBanner,
    hideOfflineBanner,
    syncQueue,
    updateVoiceBadge,
    initOffline,
  };
}
