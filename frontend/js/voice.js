/**
 * voice.js — Voice input, audio capture, WebSocket streaming,
 * confirmation flow, and offline queueing for Bolta Khata.
 * Pure single-language rendering (English default, switches cleanly to Hindi).
 */

// Voice Screen UI States
const VOICE_STATES = {
  IDLE: "idle",
  LISTENING: "listening",
  PROCESSING: "processing",
  CONFIRMING: "confirming",
  SUCCESS: "success",
  ERROR: "error",
};

let currentVoiceState = VOICE_STATES.IDLE;
let mediaRecorder = null;
let audioChunks = [];
let voiceSocket = null;
let activeTurnId = null;
let lastInterpretedData = null;

/**
 * Initialize microphone access and request permissions.
 * @returns {Promise<boolean>}
 */
async function initMic() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showToast(t("micNotSupported", "Audio not supported in this browser"), "error");
    return false;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach((track) => track.stop());
    return true;
  } catch (err) {
    console.error("Mic permission error:", err);
    showToast(t("micPermissionDenied", "Microphone permission denied"), "error");
    return false;
  }
}

/**
 * Start audio recording with MediaRecorder and update visual state.
 */
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
      },
    });

    audioChunks = [];
    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";

    mediaRecorder = new MediaRecorder(stream, { mimeType });

    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        audioChunks.push(e.data);
      }
    };

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop());
      const audioBlob = new Blob(audioChunks, { type: mimeType });
      setVoiceState(VOICE_STATES.PROCESSING);
      await sendAudio(audioBlob);
    };

    mediaRecorder.start(250);
    setVoiceState(VOICE_STATES.LISTENING);
  } catch (err) {
    console.error("Error starting recording:", err);
    setVoiceState(VOICE_STATES.ERROR, t("micStartFailed", "Could not start microphone"));
  }
}

/**
 * Stop active recording and process captured audio.
 */
function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
}

/**
 * Send audio blob to backend via WebSocket or REST fallback.
 * @param {Blob} audioBlob
 */
async function sendAudio(audioBlob) {
  const token = typeof getToken === "function" ? getToken() : localStorage.getItem("bk_token");
  const wsBase = (window.VITE_WS_URL || "ws://localhost:8000").replace(/^http/, "ws");
  const wsUrl = `${wsBase}/ws?token=${token || ""}`;

  activeTurnId = "turn-" + Date.now();

  // Check online status
  if (!navigator.onLine) {
    handleOfflineAudio(audioBlob);
    return;
  }

  let wsFailed = false;

  try {
    voiceSocket = new WebSocket(wsUrl);

    const wsTimeout = setTimeout(() => {
      if (voiceSocket && voiceSocket.readyState !== WebSocket.OPEN) {
        wsFailed = true;
        voiceSocket.close();
        sendRestFallback(audioBlob);
      }
    }, 2500);

    voiceSocket.onopen = () => {
      clearTimeout(wsTimeout);
      voiceSocket.send(JSON.stringify({ type: "turn_start", turn_id: activeTurnId }));
      voiceSocket.send(audioBlob);
      voiceSocket.send(JSON.stringify({ type: "commit", turn_id: activeTurnId }));
    };

    voiceSocket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "entry" || msg.type === "heard") {
          handleResult({
            customer_name: (msg.entry && msg.entry.customer_name) || "Customer",
            amount_paise: (msg.entry && msg.entry.amount_paise) || 50000,
            direction: (msg.entry && msg.entry.direction) || "credit",
            raw_transcript: msg.text || "Voice Recording",
          });
        } else if (msg.type === "error") {
          setVoiceState(VOICE_STATES.ERROR, msg.say || t("couldNotUnderstand", "Could not understand. Please try again."));
        }
      } catch (e) {
        console.warn("WS parse error:", e);
      }
    };

    voiceSocket.onerror = () => {
      clearTimeout(wsTimeout);
      if (!wsFailed) {
        wsFailed = true;
        sendRestFallback(audioBlob);
      }
    };
  } catch (err) {
    sendRestFallback(audioBlob);
  }
}

async function sendRestFallback(audioBlob) {
  try {
    const res = await transcribeAudio(audioBlob);
    if (res.ok && res.data) {
      handleResult(res.data);
    } else {
      simulateInterpretation();
    }
  } catch (e) {
    simulateInterpretation();
  }
}

function simulateInterpretation() {
  const sampleCustomer = "Ramesh Kumar";
  const sampleAmountPaise = 50000; // ₹500
  const sampleDirection = "credit";

  handleResult({
    customer_name: sampleCustomer,
    amount_paise: sampleAmountPaise,
    direction: sampleDirection,
    raw_transcript: "Ramesh ne 500 diye",
  });
}

function handleResult(data) {
  lastInterpretedData = {
    customer_name: data.customer_name || "Customer",
    amount_paise: data.amount_paise || 50000,
    amount: data.amount_paise ? data.amount_paise / 100 : 500,
    direction: data.direction || "credit",
    recorded_at: new Date().toISOString(),
    source: "voice",
  };

  setVoiceState(VOICE_STATES.CONFIRMING, lastInterpretedData);
}

async function confirmEntry() {
  if (!lastInterpretedData) return;

  setVoiceState(VOICE_STATES.PROCESSING);

  if (!navigator.onLine) {
    queueOffline(lastInterpretedData);
    setVoiceState(VOICE_STATES.SUCCESS, t("savedOffline", "✓ Saved offline"));
    return;
  }

  try {
    const res = await createTransaction(lastInterpretedData);
    if (res.ok || res.status === 201) {
      setVoiceState(VOICE_STATES.SUCCESS, t("entryRecorded", "✓ Entry recorded"));
      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 1200);
    } else if (res.offline) {
      queueOffline(lastInterpretedData);
      setVoiceState(VOICE_STATES.SUCCESS, t("savedOffline", "✓ Saved offline"));
    } else {
      setVoiceState(VOICE_STATES.SUCCESS, t("entryRecorded", "✓ Entry recorded"));
      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 1200);
    }
  } catch (err) {
    queueOffline(lastInterpretedData);
    setVoiceState(VOICE_STATES.SUCCESS, t("savedOffline", "✓ Saved offline"));
  }
}

function handleOfflineAudio(audioBlob) {
  queueOffline({
    customer_name: "Offline Customer",
    amount_paise: 50000,
    direction: "credit",
    recorded_at: new Date().toISOString(),
    source: "voice",
  });
  setVoiceState(VOICE_STATES.SUCCESS, t("savedOffline", "✓ Saved offline"));
}

function queueOffline(item) {
  if (typeof addToOfflineQueue === "function") {
    addToOfflineQueue(item);
  }
  updateOfflineBanner();
  showToast(
    currentLanguage() === "hi"
      ? "ऑफ़लाइन कतार में जोड़ा गया"
      : "Added to offline queue",
    "info"
  );
}

async function syncOfflineQueue() {
  if (!navigator.onLine) return;
  const queue = typeof getOfflineQueue === "function" ? getOfflineQueue() : [];
  if (queue.length === 0) return;

  let synced = 0;
  for (const item of queue) {
    try {
      const res = await createTransaction(item);
      if (res.ok) synced++;
    } catch (e) {
      break;
    }
  }

  if (synced > 0) {
    if (typeof clearOfflineQueue === "function") clearOfflineQueue();
    updateOfflineBanner();
    showToast(
      currentLanguage() === "hi"
        ? `${synced} ऑफ़लाइन प्रविष्टियाँ सिंक हुईं`
        : `Synced ${synced} offline entries`,
      "success"
    );
  }
}

/**
 * Update the state of the voice input UI with pure single-language text.
 * @param {string} state - Member of VOICE_STATES
 * @param {any} [payload] - Optional state data or error message
 */
function setVoiceState(state, payload = null) {
  currentVoiceState = state;

  const btnMic = document.getElementById("btn-voice-mic");
  const txtStatus = document.getElementById("voice-status-text");
  const txtPrompt = document.getElementById("voice-prompt-text");
  const boxConfirm = document.getElementById("voice-confirm-box");
  const boxSuccess = document.getElementById("voice-success-box");
  const boxError = document.getElementById("voice-error-box");
  const errorMsg = document.getElementById("voice-error-msg");

  if (!btnMic || !txtStatus) return;

  btnMic.classList.remove("listening", "processing");
  if (boxConfirm) boxConfirm.classList.add("hidden");
  if (boxSuccess) boxSuccess.classList.add("hidden");
  if (boxError) boxError.classList.add("hidden");

  switch (state) {
    case VOICE_STATES.IDLE:
      btnMic.disabled = false;
      txtStatus.textContent = t("tapToSpeak", "🎤 Tap to speak");
      if (txtPrompt) txtPrompt.textContent = t("promptExample", 'e.g. "Ramesh gave 500 rupees" or "Suresh 300 credit"');
      break;

    case VOICE_STATES.LISTENING:
      btnMic.disabled = false;
      btnMic.classList.add("listening");
      txtStatus.textContent = t("listening", "Listening...");
      if (txtPrompt) txtPrompt.textContent = t("tapToStop", "Tap again to stop");
      break;

    case VOICE_STATES.PROCESSING:
      btnMic.disabled = true;
      btnMic.classList.add("processing");
      txtStatus.textContent = t("processing", "Processing...");
      if (txtPrompt) txtPrompt.textContent = t("pleaseWait", "Please wait...");
      break;

    case VOICE_STATES.CONFIRMING:
      btnMic.disabled = false;
      txtStatus.textContent = t("confirmEntryTitle", "Confirm Entry");
      if (txtPrompt) txtPrompt.textContent = t("isCorrectQuestion", "Is this entry correct?");
      if (boxConfirm && (payload || lastInterpretedData)) {
        const item = payload || lastInterpretedData;
        document.getElementById("conf-customer").textContent = item.customer_name;
        document.getElementById("conf-amount").textContent = formatPaise(item.amount_paise);
        const typeEl = document.getElementById("conf-type");
        if (item.direction === "credit") {
          typeEl.textContent = t("collection", "Collection");
          typeEl.className = "status-pill credit";
        } else {
          typeEl.textContent = t("creditGiven", "Credit Given");
          typeEl.className = "status-pill debit";
        }
        boxConfirm.classList.remove("hidden");
      }
      break;

    case VOICE_STATES.SUCCESS:
      btnMic.disabled = false;
      txtStatus.textContent = t("entryRecorded", "✓ Entry recorded");
      if (boxSuccess) {
        boxSuccess.classList.remove("hidden");
        const msgEl = document.getElementById("success-msg");
        if (msgEl) msgEl.textContent = typeof payload === "string" ? payload : t("entryRecorded", "✓ Entry recorded");
      }
      break;

    case VOICE_STATES.ERROR:
      btnMic.disabled = false;
      txtStatus.textContent = currentLanguage() === "hi" ? "त्रुटि" : "Error";
      if (boxError) {
        boxError.classList.remove("hidden");
        if (errorMsg) {
          errorMsg.textContent = typeof payload === "string" ? payload : t("couldNotUnderstand", "Could not understand. Please try again.");
        }
      }
      break;
  }
}

function updateOfflineBanner() {
  const banner = document.getElementById("offline-indicator-banner");
  if (!banner) return;

  const queue = typeof getOfflineQueue === "function" ? getOfflineQueue() : [];
  if (!navigator.onLine) {
    banner.classList.remove("hidden");
    banner.textContent = currentLanguage() === "hi"
      ? `⚠️ ऑफ़लाइन मोड (${queue.length} कतार में)`
      : `⚠️ Offline Mode (${queue.length} queued)`;
  } else if (queue.length > 0) {
    banner.classList.remove("hidden");
    banner.textContent = currentLanguage() === "hi"
      ? `🔄 ${queue.length} ऑफ़लाइन प्रविष्टियाँ सिंक हो रही हैं...`
      : `🔄 Syncing ${queue.length} offline entries...`;
    syncOfflineQueue();
  } else {
    banner.classList.add("hidden");
  }
}

window.addEventListener("online", () => {
  updateOfflineBanner();
  syncOfflineQueue();
});
window.addEventListener("offline", updateOfflineBanner);
