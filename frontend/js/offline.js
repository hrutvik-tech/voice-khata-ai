/**
 * offline.js — Offline sync manager for Bolta Khata.
 *
 * State machine for connection:
 *   "online"       → no banner
 *   "offline"      → yellow banner with queue count message
 *   "reconnecting" → blue banner "Dobara jud raha hai…"
 *   syncing        → banner "Entry sync ho rahi hain…"
 *   synced         → green banner "Sab entry jud gayi" for 3 s then hide
 *
 * notSaved[] — entries that failed to save (shown as dismissible cards on Home).
 * dismissNotSaved(turn_id) — removes a notSaved entry.
 */

// ─── Internal state ───────────────────────────────────────────────────────────
let _connectionState = "online";   // "online" | "offline" | "reconnecting"
let _isSyncing       = false;
let _notSaved        = [];         // [{turn_id, text}, …]
let _syncedTimer     = null;

// ─── Helpers ─────────────────────────────────────────────────────────────────

function detectOnline() {
  return navigator.onLine;
}

function _queuedCount() {
  return (typeof getOfflineQueue === "function" ? getOfflineQueue() : []).length;
}

// ─── Banner ───────────────────────────────────────────────────────────────────

/**
 * Update (or create) the banner based on current state.
 * @param {"offline"|"reconnecting"|"syncing"|"synced"|"hide"} state
 */
function _setBannerState(state) {
  // Find or create the banner inside every .app-container on the page
  document.querySelectorAll(".app-container").forEach((container) => {
    let banner = container.querySelector(".bk-conn-banner");
    if (!banner) {
      banner = document.createElement("div");
      banner.className = "bk-conn-banner";
      // Insert after header if present, else first child
      const header = container.querySelector(".page-header");
      if (header && header.nextSibling) {
        container.insertBefore(banner, header.nextSibling);
      } else {
        container.insertBefore(banner, container.firstChild);
      }
    }

    if (state === "hide") {
      banner.style.display = "none";
      banner.textContent = "";
      return;
    }

    banner.style.display = "flex";

    const qc = _queuedCount();

    switch (state) {
      case "offline": {
        banner.className = "bk-conn-banner bk-conn-banner--offline";
        if (qc > 0) {
          banner.textContent = `⚠️ Internet nahi hai — ${qc} entr${qc === 1 ? "y" : "ies"} wait kar rahi hain`;
        } else {
          banner.textContent = "⚠️ Internet nahi hai — bolte rahiye, entry baad mein jud jayegi";
        }
        break;
      }
      case "reconnecting": {
        banner.className = "bk-conn-banner bk-conn-banner--reconnecting";
        banner.textContent = "🔄 Dobara jud raha hai…";
        break;
      }
      case "syncing": {
        banner.className = "bk-conn-banner bk-conn-banner--syncing";
        banner.textContent = "⏳ Entry sync ho rahi hain…";
        break;
      }
      case "synced": {
        banner.className = "bk-conn-banner bk-conn-banner--synced";
        banner.textContent = "✅ Sab entry jud gayi";
        break;
      }
    }
  });
}

// Legacy alias kept so existing code still works
function showOfflineBanner() { _setBannerState("offline"); }
function hideOfflineBanner() { _setBannerState("hide"); }

// ─── notSaved cards ───────────────────────────────────────────────────────────

/**
 * Dismiss a not-saved entry card by its turn_id.
 * Removes from internal list and re-renders.
 * @param {string} turn_id
 */
function dismissNotSaved(turn_id) {
  _notSaved = _notSaved.filter((e) => e.turn_id !== turn_id);
  _renderNotSavedCards();
}

/**
 * Add an entry to the notSaved list (called when a voice entry fails to save).
 * @param {{turn_id: string, text: string}} entry
 */
function addNotSaved(entry) {
  if (!_notSaved.find((e) => e.turn_id === entry.turn_id)) {
    _notSaved.push(entry);
  }
  _renderNotSavedCards();
}

/**
 * Render dismissible not-saved cards into #not-saved-container (Home only).
 */
function _renderNotSavedCards() {
  const container = document.getElementById("not-saved-container");
  if (!container) return;

  container.innerHTML = "";
  _notSaved.forEach((entry) => {
    const card = document.createElement("div");
    card.className = "not-saved-card";
    card.dataset.turnId = entry.turn_id;

    const msg = document.createElement("span");
    msg.className = "not-saved-msg";
    // Truncate long text
    const preview = entry.text && entry.text.length > 60
      ? entry.text.slice(0, 57) + "…"
      : (entry.text || "");
    msg.textContent = `⚠️ Offline entry save nahi hui: "${preview}" — dobara boliye`;

    const closeBtn = document.createElement("button");
    closeBtn.className = "not-saved-close";
    closeBtn.setAttribute("aria-label", "Dismiss");
    closeBtn.textContent = "✕";
    closeBtn.addEventListener("click", () => dismissNotSaved(entry.turn_id));

    card.appendChild(msg);
    card.appendChild(closeBtn);
    container.appendChild(card);
  });
}

// ─── Voice tab badge ──────────────────────────────────────────────────────────

function updateVoiceBadge() {
  const count = _queuedCount();
  document.querySelectorAll(".nav-mic-btn, [data-tab='voice']").forEach((btn) => {
    let badge = btn.querySelector(".voice-badge");
    if (count > 0) {
      if (!badge) {
        badge = document.createElement("span");
        badge.className = "voice-badge";
        btn.style.position = "relative";
        btn.appendChild(badge);
      }
      badge.textContent = count > 99 ? "99+" : String(count);
      badge.style.display = "flex";
    } else if (badge) {
      badge.style.display = "none";
    }
  });
}

// ─── Error Toast ──────────────────────────────────────────────────────────────
// (Used by every page for REST failures — showToast() already lives in app.js)
// This wrapper makes intent explicit:
function showRestError(message) {
  if (typeof showToast === "function") {
    showToast(message || "Network error — please try again", "error");
  }
}

// ─── Sync ─────────────────────────────────────────────────────────────────────

async function syncQueue() {
  if (!detectOnline()) {
    _setBannerState("offline");
    return;
  }

  const queue = typeof getOfflineQueue === "function" ? getOfflineQueue() : [];
  if (!queue || queue.length === 0) {
    updateVoiceBadge();
    return;
  }

  // Show syncing banner
  _isSyncing = true;
  _setBannerState("syncing");

  let syncedCount = 0;
  const remaining = [...queue];

  while (remaining.length > 0) {
    const item = remaining[0];
    try {
      if (typeof createTransaction === "function") {
        const res = await createTransaction(item);
        if (res && (res.ok || res.status === 201 || res.status === 200)) {
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
      break;
    } catch (err) {
      console.warn("Sync queue item failed:", err);
      break;
    }
  }

  _isSyncing = false;

  if (syncedCount > 0 && _queuedCount() === 0) {
    // All synced — show green confirmation for 3 s
    _setBannerState("synced");
    if (_syncedTimer) clearTimeout(_syncedTimer);
    _syncedTimer = setTimeout(() => _setBannerState("hide"), 3000);
  } else if (_queuedCount() > 0) {
    _setBannerState("offline");
  } else {
    _setBannerState("hide");
  }

  updateVoiceBadge();
}

// ─── Init ─────────────────────────────────────────────────────────────────────

function initOffline() {
  if (detectOnline()) {
    _setBannerState("hide");
    syncQueue();
  } else {
    _connectionState = "offline";
    _setBannerState("offline");
  }
  updateVoiceBadge();
  _renderNotSavedCards();
}

// ─── Global browser events ────────────────────────────────────────────────────

window.addEventListener("online", () => {
  _connectionState = "reconnecting";
  _setBannerState("reconnecting");
  if (typeof showToast === "function") {
    showToast("Internet wapas aa gaya!", "info");
  }
  // Small delay so OS can fully re-establish connection before syncing
  setTimeout(() => {
    _connectionState = "online";
    syncQueue();
  }, 1200);
});

window.addEventListener("offline", () => {
  _connectionState = "offline";
  _setBannerState("offline");
  updateVoiceBadge();
});

// Auto-run when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initOffline);
} else {
  initOffline();
}

// ─── Exports ──────────────────────────────────────────────────────────────────

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    detectOnline,
    showOfflineBanner,
    hideOfflineBanner,
    syncQueue,
    updateVoiceBadge,
    initOffline,
    dismissNotSaved,
    addNotSaved,
    showRestError,
    _setBannerState,
    _queuedCount,
    // expose state for tests
    _getState: () => ({ connectionState: _connectionState, isSyncing: _isSyncing, notSaved: [..._notSaved] }),
  };
}
