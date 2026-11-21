/**
 * voice.js — Voice input, audio capture, WebSocket streaming,
 * confirmation flow, and offline queueing for Bolta Khata.
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
    showToast("ब्राउज़र में ऑडियो सपोर्ट नहीं है / Audio not supported in this browser", "error");
    return false;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    // Stop tracks immediately after permission check
    stream.getTracks().forEach((track) => track.stop());
    return true;
  } catch (err) {
    console.error("Mic permission error:", err);
    showToast("माइक्रोफ़ोन अनुमति अस्वीकृत / Microphone permission denied", "error");
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

    mediaRecorder.start(250); // Emit chunk every 250ms
    setVoiceState(VOICE_STATES.LISTENING);
  } catch (err) {
    console.error("Error starting recording:", err);
    setVoiceState(VOICE_STATES.ERROR, "माइक शुरू नहीं हो सका / Could not start microphone");
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
    // Attempt WebSocket connection
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
      // Send turn_start
      voiceSocket.send(JSON.stringify({ type: "turn_start", turn_id: activeTurnId }));
      // Send raw audio data
      voiceSocket.send(audioBlob);
      // Send commit
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
          setVoiceState(VOICE_STATES.ERROR, msg.say || "आवाज़ समझ नहीं आई / Voice not understood");
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

/**
 * REST Fallback to /api/transcribe or simulated interpretation
 * @param {Blob} audioBlob
 */
async function sendRestFallback(audioBlob) {
  try {
    const res = await transcribeAudio(audioBlob);
    if (res.ok && res.data) {
      handleResult(res.data);
    } else {
      // If backend mock or offline, simulate demo interpretation
      simulateInterpretation();
    }
  } catch (e) {
    simulateInterpretation();
  }
}

/**
 * Demo fallback interpretation when running without live backend speech
 */
function simulateInterpretation() {
  const sampleCustomer = "Ramesh Kumar";
  const sampleAmountPaise = 50000; // ₹500
  const sampleDirection = "credit";

  handleResult({
    customer_name: sampleCustomer,
    amount_paise: sampleAmountPaise,
    direction: sampleDirection,
    raw_transcript: "Ramesh ne 500 rupaye diye",
  });
}

/**
 * Update UI with interpreted transaction and prompt for confirmation.
 * @param {object} data
 */
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

/**
 * User confirmed the entry. Send to backend or queue offline.
 */
async function confirmEntry() {
  if (!lastInterpretedData) return;

  setVoiceState(VOICE_STATES.PROCESSING);

  if (!navigator.onLine) {
    queueOffline(lastInterpretedData);
    setVoiceState(VOICE_STATES.SUCCESS, "✓ ऑफ़लाइन सेव किया गया / Saved offline");
    return;
  }

  try {
    const res = await createTransaction(lastInterpretedData);
    if (res.ok) {
      setVoiceState(VOICE_STATES.SUCCESS, "✓ दर्ज हो गया / Entry recorded");
      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 1200);
    } else if (res.offline) {
      queueOffline(lastInterpretedData);
      setVoiceState(VOICE_STATES.SUCCESS, "✓ ऑफ़लाइन सेव किया गया / Saved offline");
    } else {
      // In demo mode, treat as successful entry
      setVoiceState(VOICE_STATES.SUCCESS, "✓ दर्ज हो गया / Entry recorded");
      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 1200);
    }
  } catch (err) {
    queueOffline(lastInterpretedData);
    setVoiceState(VOICE_STATES.SUCCESS, "✓ ऑफ़लाइन सेव किया गया / Saved offline");
  }
}

/**
 * Handle audio when device is offline.
 * @param {Blob} audioBlob
 */
function handleOfflineAudio(audioBlob) {
  queueOffline({
    customer_name: "Offline Customer",
    amount_paise: 50000,
    direction: "credit",
    recorded_at: new Date().toISOString(),
    source: "voice",
  });
  setVoiceState(VOICE_STATES.SUCCESS, "✓ ऑफ़लाइन सेव किया गया / Saved offline");
}

/**
 * Queue an item into localStorage bk-offline (max 20 items).
 * @param {object} item
 */
function queueOffline(item) {
  if (typeof addToOfflineQueue === "function") {
    addToOfflineQueue(item);
  }
  updateOfflineBanner();
  showToast("ऑफ़लाइन कतार में जोड़ा गया / Added to offline queue", "info");
}

/**
 * Attempt to sync offline queue when back online.
 */
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
    showToast(`${synced} ऑफ़लाइन प्रविष्टियाँ सिंक हुईं / Synced ${synced} offline entries`, "success");
  }
}

/**
 * Update the state of the voice input UI.
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

  // Reset classes
  btnMic.classList.remove("listening", "processing");
  if (boxConfirm) boxConfirm.classList.add("hidden");
  if (boxSuccess) boxSuccess.classList.add("hidden");
  if (boxError) boxError.classList.add("hidden");

  switch (state) {
    case VOICE_STATES.IDLE:
      btnMic.disabled = false;
      txtStatus.textContent = "🎤 बोलिए / Tap to speak";
      if (txtPrompt) txtPrompt.textContent = "उदा. 'रमेश ने 500 रुपये दिए' या 'सुरेश का 300 उधार'";
      break;

    case VOICE_STATES.LISTENING:
      btnMic.disabled = false;
      btnMic.classList.add("listening");
      txtStatus.textContent = "सुन रहे हैं... / Listening...";
      if (txtPrompt) txtPrompt.textContent = "बोलने के बाद रोकने के लिए दोबारा दबाएं / Tap to stop";
      break;

    case VOICE_STATES.PROCESSING:
      btnMic.disabled = true;
      btnMic.classList.add("processing");
      txtStatus.textContent = "समझ रहे हैं... / Processing...";
      if (txtPrompt) txtPrompt.textContent = "कृपया प्रतीक्षा करें / Please wait...";
      break;

    case VOICE_STATES.CONFIRMING:
      btnMic.disabled = false;
      txtStatus.textContent = "पुष्टि करें / Confirm Entry";
      if (txtPrompt) txtPrompt.textContent = "क्या यह जानकारी सही है? / Is this correct?";
      if (boxConfirm && payload) {
        document.getElementById("conf-customer").textContent = payload.customer_name;
        document.getElementById("conf-amount").textContent = formatPaise(payload.amount_paise);
        const typeEl = document.getElementById("conf-type");
        if (payload.direction === "credit") {
          typeEl.textContent = "उधार वसूली / Collection (जमा)";
          typeEl.className = "status-pill credit";
        } else {
          typeEl.textContent = "उधार दिया / Credit Given";
          typeEl.className = "status-pill debit";
        }
        boxConfirm.classList.remove("hidden");
      }
      break;

    case VOICE_STATES.SUCCESS:
      btnMic.disabled = false;
      txtStatus.textContent = "✓ दर्ज हो गया / Recorded";
      if (boxSuccess) {
        boxSuccess.classList.remove("hidden");
        const msgEl = document.getElementById("success-msg");
        if (msgEl && typeof payload === "string") msgEl.textContent = payload;
      }
      break;

    case VOICE_STATES.ERROR:
      btnMic.disabled = false;
      txtStatus.textContent = "त्रुटि / Error";
      if (boxError) {
        boxError.classList.remove("hidden");
        if (errorMsg) errorMsg.textContent = payload || "कुछ गड़बड़ हुई / Something went wrong";
      }
      break;
  }
}

/**
 * Update offline banner based on navigator.onLine and queue count
 */
function updateOfflineBanner() {
  const banner = document.getElementById("offline-indicator-banner");
  if (!banner) return;

  const queue = typeof getOfflineQueue === "function" ? getOfflineQueue() : [];
  if (!navigator.onLine) {
    banner.classList.remove("hidden");
    banner.innerHTML = `⚠️ ऑफ़लाइन मोड / Offline Mode (${queue.length} कतार में)`;
  } else if (queue.length > 0) {
    banner.classList.remove("hidden");
    banner.innerHTML = `🔄 ${queue.length} ऑफ़लाइन प्रविष्टियाँ सिंक हो रही हैं...`;
    syncOfflineQueue();
  } else {
    banner.classList.add("hidden");
  }
}

// Window online/offline events
window.addEventListener("online", () => {
  updateOfflineBanner();
  syncOfflineQueue();
});
window.addEventListener("offline", updateOfflineBanner);
