/**
 * lang.js — Unified language and translation system for Bolta Khata.
 * Ensures the app displays in ONLY ONE language at a time (English default).
 * Provides instantaneous switching between English and Hindi across all pages.
 */

const TRANSLATIONS = {
  en: {
    // App & Branding
    appTitle: "Bolta Khata",
    appSub: "Voice Digital Ledger",
    tagline: "Voice-first digital ledger for Kirana shops",
    footerText: "Secure & simple digital voice ledger for Indian retail",

    // Auth & Navigation
    loginTab: "Log In",
    registerTab: "Register",
    phoneLabel: "Mobile Number",
    phonePlaceholder: "10-digit mobile number",
    pinLabel: "PIN or Password",
    pinPlaceholder: "4 or 6-digit PIN",
    loginBtn: "Log In",
    shopNameLabel: "Shop Name",
    shopNamePlaceholder: "e.g. Gupta General Store",
    ownerNameLabel: "Owner Name",
    ownerNamePlaceholder: "e.g. Ramesh Kumar",
    regPinLabel: "Set PIN",
    regPinPlaceholder: "4-digit secret PIN",
    registerBtn: "Create Account",
    navHome: "Home",
    navCustomers: "Customers",
    navVoice: "Voice",
    navHistory: "History",
    navLogout: "Logout",

    // Dashboard
    todaySales: "Today's Sales",
    todayCollection: "Today's Collection",
    totalPending: "Total Pending",
    bannerTitle: "Speak & Record",
    bannerSub: 'e.g. "Ramesh gave 500"',
    recentTransactions: "Recent Transactions",
    refresh: "🔄 Refresh",
    loadingTransactions: "Loading transactions...",
    noTransactionsYet: "No transactions yet",
    noTransactionsSub: "Tap the center mic button to record an entry",
    txnDetails: "Transaction Details",
    dateTime: "Date & Time",
    source: "Source",
    close: "Close",
    collection: "Collection",
    sale: "Sale",
    creditGiven: "Credit Given",
    voiceInput: "Voice Input",
    manualInput: "Manual",
    refreshing: "Refreshing...",

    // Customers
    customersTitle: "Customers",
    searchCustomerPlaceholder: "Search customer",
    addCustomerBtn: "Add Customer",
    loadingCustomers: "Loading customers...",
    noCustomersYet: "No customers yet",
    noCustomersSub: "Add your first customer using the button above",
    toCollect: "To collect",
    toPay: "To pay",
    customerLast: "Last",
    addCustomerModalTitle: "Add Customer",
    nameLabel: "Customer Name",
    namePlaceholder: "e.g. Ramesh Sharma",
    phoneOptionalLabel: "Phone (optional)",
    amountLabel: "Amount (₹)",
    amountPlaceholder: "e.g. 500",
    creditOption: "↓ Credit (Received)",
    debitOption: "↑ Debit (Given)",
    dateTimeLabel: "Date & Time",
    similarFound: "Similar customer found:",
    addAnyway: "Add anyway",
    saveBtn: "Save",
    savingBtn: "Saving...",
    pleaseEnterName: "Please enter customer name",
    customerAddedSuccess: "✓ Customer added successfully",
    customerCountSingle: "1 customer",
    customerCountPlural: "customers",

    // Voice Screen
    voiceScreenTitle: "Voice Input",
    voiceScreenSubtitle: "Speak in Hindi or English",
    offlineMode: "⚠️ Offline Mode",
    tapToSpeak: "🎤 Tap to speak",
    promptExample: 'e.g. "Ramesh gave 500 rupees" or "Suresh 300 credit"',
    listening: "Listening...",
    tapToStop: "Tap again to stop",
    processing: "Processing...",
    pleaseWait: "Please wait...",
    confirmEntryTitle: "Confirm Entry",
    isCorrectQuestion: "Is this entry correct?",
    customerLabel: "Customer",
    amountLabel: "Amount",
    typeLabel: "Type",
    btnChange: "✗ Change",
    btnConfirm: "✓ Confirm",
    entryRecorded: "✓ Entry recorded",
    couldNotUnderstand: "Could not understand. Please try again.",
    btnRetry: "Retry",
    editEntryTitle: "Edit Entry",
    changeDirectionLabel: "Change Type:",
    btnSpeakAgain: "🎙️ Speak Again",
    savedOffline: "✓ Saved offline",
    micNotSupported: "Audio not supported in this browser",
    micPermissionDenied: "Microphone permission denied",
    micStartFailed: "Could not start microphone",

    // History Screen
    transactionsTitle: "Transactions",
    filterToday: "Today",
    filterYesterday: "Yesterday",
    filterThisWeek: "This Week",
    filterThisMonth: "This Month",
    allCustomersOption: "All customers",
    noHistoryFound: "No transactions found",
    noHistorySub: "Try a different date or customer filter",
    btnLoadMore: "Load More",
    creditPrefix: "↓ Credit",
    debitPrefix: "↑ Debit",

    // Connection / Offline banner messages
    bannerOfflineWithQueue: "⚠️ Internet nahi hai — {count} entr{plural} wait kar rahi hain",
    bannerOfflineNoQueue:   "⚠️ Internet nahi hai — bolte rahiye, entry baad mein jud jayegi",
    bannerReconnecting:     "🔄 Dobara jud raha hai…",
    bannerSyncing:          "⏳ Entry sync ho rahi hain…",
    bannerSynced:           "✅ Sab entry jud gayi",

    // Not-saved entry card
    notSavedPrefix:  "⚠️ Offline entry save nahi hui:",
    notSavedSuffix:  "— dobara boliye",
    totalLending:    "Total Lending",
  },

  hi: {
    // App & Branding
    appTitle: "बोलता खाता",
    appSub: "वॉइस डिजिटल बही-खाता",
    tagline: "किराना दुकानों का आवाज़ से चलने वाला खाता",
    footerText: "भारतीय खुदरा व्यापारियों के लिए सुरक्षित डिजिटल बही-खाता",

    // Auth & Navigation
    loginTab: "लॉग इन",
    registerTab: "रजिस्टर",
    phoneLabel: "मोबाइल नंबर",
    phonePlaceholder: "10 अंकों का मोबाइल नंबर",
    pinLabel: "पिन या पासवर्ड",
    pinPlaceholder: "4 या 6 अंकों का पिन",
    loginBtn: "लॉग इन करें",
    shopNameLabel: "दुकान का नाम",
    shopNamePlaceholder: "उदा. गुप्ता जनरल स्टोर",
    ownerNameLabel: "दुकानदार का नाम",
    ownerNamePlaceholder: "उदा. रमेश कुमार",
    regPinLabel: "पिन सेट करें",
    regPinPlaceholder: "4 अंकों का गुप्त पिन",
    registerBtn: "खाता बनाएं",
    navHome: "होम",
    navCustomers: "ग्राहक",
    navVoice: "बोलें",
    navHistory: "इतिहास",
    navLogout: "लॉग आउट",

    // Dashboard
    todaySales: "आज की बिक्री",
    todayCollection: "आज की वसूली",
    totalPending: "कुल बकाया",
    bannerTitle: "बोलकर लिखें",
    bannerSub: 'उदा. "रमेश ने 500 दिए"',
    recentTransactions: "हाल के लेन-देन",
    refresh: "🔄 ताज़ा करें",
    loadingTransactions: "लेन-देन लोड हो रहे हैं...",
    noTransactionsYet: "कोई लेन-देन नहीं",
    noTransactionsSub: "एंट्री दर्ज करने के लिए बीच का माइक दबाएं",
    txnDetails: "लेन-देन विवरण",
    dateTime: "दिनांक व समय",
    source: "माध्यम",
    close: "बंद करें",
    collection: "जमा",
    sale: "उधार",
    creditGiven: "उधार दिया",
    voiceInput: "आवाज़ द्वारा",
    manualInput: "हाथ से",
    refreshing: "ताज़ा हो रहा है...",

    // Customers
    customersTitle: "ग्राहक सूची",
    searchCustomerPlaceholder: "ग्राहक खोजें",
    addCustomerBtn: "नया ग्राहक",
    loadingCustomers: "ग्राहक लोड हो रहे हैं...",
    noCustomersYet: "कोई ग्राहक नहीं",
    noCustomersSub: "नया ग्राहक जोड़ने के लिए ऊपर बटन दबाएं",
    toCollect: "वसूलना है",
    toPay: "देना है",
    customerLast: "अंतिम",
    addCustomerModalTitle: "नया ग्राहक जोड़ें",
    nameLabel: "ग्राहक का नाम",
    namePlaceholder: "उदा. रमेश शर्मा",
    phoneOptionalLabel: "फ़ोन (वैकल्पिक)",
    amountLabel: "राशि (₹)",
    amountPlaceholder: "उदा. 500",
    creditOption: "↓ जमा (मिला)",
    debitOption: "↑ उधार (दिया)",
    dateTimeLabel: "दिनांक व समय",
    similarFound: "मिलता-जुलता ग्राहक मिला:",
    addAnyway: "फिर भी जोड़ें",
    saveBtn: "सहेजें",
    savingBtn: "सहेज रहे हैं...",
    pleaseEnterName: "कृपया ग्राहक का नाम दर्ज करें",
    customerAddedSuccess: "✓ ग्राहक सफलतापूर्वक जोड़ा गया",
    customerCountSingle: "1 ग्राहक",
    customerCountPlural: "ग्राहक",

    // Voice Screen
    voiceScreenTitle: "वॉइस खाता",
    voiceScreenSubtitle: "हिंदी या अंग्रेज़ी में बोलें",
    offlineMode: "⚠️ ऑफ़लाइन मोड",
    tapToSpeak: "🎤 बोलिए",
    promptExample: 'उदा. "रमेश ने 500 रुपये दिए" या "सुरेश का 300 उधार"',
    listening: "सुन रहे हैं...",
    tapToStop: "रोकने के लिए दोबारा दबाएं",
    processing: "समझ रहे हैं...",
    pleaseWait: "कृपया प्रतीक्षा करें...",
    confirmEntryTitle: "पुष्टि करें",
    isCorrectQuestion: "क्या यह जानकारी सही है?",
    customerLabel: "ग्राहक",
    amountLabel: "राशि",
    typeLabel: "प्रकार",
    btnChange: "✗ बदलें",
    btnConfirm: "✓ सही है",
    entryRecorded: "✓ दर्ज हो गया",
    couldNotUnderstand: "समझ नहीं आया, दोबारा बोलिए।",
    btnRetry: "दोबारा कोशिश करें",
    editEntryTitle: "बदलाव करें",
    changeDirectionLabel: "प्रकार बदलें:",
    btnSpeakAgain: "🎙️ दोबारा बोलें",
    savedOffline: "✓ ऑफ़लाइन सहेजा गया",
    micNotSupported: "ब्राउज़र में ऑडियो सपोर्ट नहीं है",
    micPermissionDenied: "माइक्रोफ़ोन अनुमति अस्वीकृत",
    micStartFailed: "माइक शुरू नहीं हो सका",

    // History Screen
    transactionsTitle: "लेन-देन",
    filterToday: "आज",
    filterYesterday: "कल",
    filterThisWeek: "इस हफ़्ते",
    filterThisMonth: "इस महीने",
    allCustomersOption: "सभी ग्राहक",
    noHistoryFound: "कोई लेन-देन नहीं मिला",
    noHistorySub: "कोई अन्य तारीख या ग्राहक चुनें",
    btnLoadMore: "और दिखाएं",
    creditPrefix: "↓ जमा",
    debitPrefix: "↑ उधार",

    // Connection / Offline banner messages (Hindi matches English text as requested)
    bannerOfflineWithQueue: "⚠️ Internet nahi hai — {count} entr{plural} wait kar rahi hain",
    bannerOfflineNoQueue:   "⚠️ Internet nahi hai — bolte rahiye, entry baad mein jud jayegi",
    bannerReconnecting:     "🔄 Dobara jud raha hai…",
    bannerSyncing:          "⏳ Entry sync ho rahi hain…",
    bannerSynced:           "✅ Sab entry jud gayi",

    // Not-saved entry card
    notSavedPrefix:  "⚠️ Offline entry save nahi hui:",
    notSavedSuffix:  "— dobara boliye",
    totalLending:    "कुल उधार",
  },
};

/**
 * Returns active language code ('en' or 'hi'). Defaults strictly to 'en'.
 */
function currentLanguage() {
  try {
    const saved = localStorage.getItem("bk_lang");
    return saved === "hi" ? "hi" : "en";
  } catch (e) {
    return "en";
  }
}

/**
 * Helper to fetch a translated string by key in current language.
 */
function t(key, fallback = "") {
  const lang = currentLanguage();
  return (TRANSLATIONS[lang] && TRANSLATIONS[lang][key]) ||
         (TRANSLATIONS.en && TRANSLATIONS.en[key]) ||
         fallback;
}

/**
 * Set and apply the active language.
 * Updates DOM elements, buttons, attributes, and fires 'languageChanged' event.
 */
function setAppLanguage(lang) {
  const chosen = lang === "hi" ? "hi" : "en";
  try {
    localStorage.setItem("bk_lang", chosen);
  } catch (e) {
    console.warn("Storage error saving lang:", e);
  }

  document.documentElement.lang = chosen;

  // 1. Update elements with data-i18n
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    const val = t(key);
    if (val) el.textContent = val;
  });

  // 2. Update elements with data-i18n-placeholder
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    const val = t(key);
    if (val) el.placeholder = val;
  });

  // 3. Backward compatibility with data-en / data-hi
  document.querySelectorAll("[data-en]").forEach((el) => {
    const text = chosen === "hi" ? el.getAttribute("data-hi") : el.getAttribute("data-en");
    if (text !== null) el.textContent = text;
  });
  document.querySelectorAll("[data-en-placeholder]").forEach((el) => {
    const ph = chosen === "hi" ? el.getAttribute("data-hi-placeholder") : el.getAttribute("data-en-placeholder");
    if (ph !== null) el.placeholder = ph;
  });

  // 4. Update the language switch buttons at the top
  const btnEn = document.getElementById("lang-btn-en");
  const btnHi = document.getElementById("lang-btn-hi");
  if (btnEn && btnHi) {
    if (chosen === "hi") {
      btnHi.classList.add("active");
      btnEn.classList.remove("active");
    } else {
      btnEn.classList.add("active");
      btnHi.classList.remove("active");
    }
  }

  // 5. Update single lang-toggle button if present
  // In English mode: displays "🌐 हिंदी" to clearly invite switching to Hindi
  // In Hindi mode: displays "🌐 English" to clearly invite switching to English
  const langToggle = document.getElementById("lang-toggle");
  if (langToggle) {
    langToggle.textContent = chosen === "en" ? "🌐 हिंदी" : "🌐 English";
    langToggle.setAttribute("title", chosen === "en" ? "हिंदी में बदलें" : "Switch to English");
  }

  // 6. Broadcast event so active views re-render dynamic elements
  window.dispatchEvent(new CustomEvent("languageChanged", { detail: { lang: chosen } }));
}

/**
 * Initializes language listeners on page load.
 */
function initLang() {
  const current = currentLanguage();
  setAppLanguage(current);

  // Wire up segmented switch buttons if present
  const btnEn = document.getElementById("lang-btn-en");
  const btnHi = document.getElementById("lang-btn-hi");
  if (btnEn) {
    btnEn.addEventListener("click", () => setAppLanguage("en"));
  }
  if (btnHi) {
    btnHi.addEventListener("click", () => setAppLanguage("hi"));
  }

  // Wire up single toggle button if present
  const toggleBtn = document.getElementById("lang-toggle");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const active = currentLanguage();
      setAppLanguage(active === "en" ? "hi" : "en");
    });
  }
}

// ─── Global Customer Name Translation ─────────────────────────────────────────
const GLOBAL_NAME_MAP_EN_TO_HI = {
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

const GLOBAL_NAME_MAP_HI_TO_EN = {
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

function getLocalizedCustomerName(customerOrName, targetLang) {
  const lang = targetLang || currentLanguage();
  const rawName = typeof customerOrName === "object" && customerOrName
    ? (customerOrName.name || "")
    : String(customerOrName || "");

  const trimmed = rawName.trim();
  if (!trimmed) return lang === "hi" ? "ग्राहक" : "Customer";

  if (lang === "hi") {
    if (typeof customerOrName === "object" && customerOrName && customerOrName.name_hi) {
      return customerOrName.name_hi;
    }
    const lower = trimmed.toLowerCase();
    if (GLOBAL_NAME_MAP_EN_TO_HI[lower]) return GLOBAL_NAME_MAP_EN_TO_HI[lower];
    const parts = lower.split(/\s+/);
    const translated = parts.map((p) => GLOBAL_NAME_MAP_EN_TO_HI[p] || p);
    if (translated.some((p) => /[\u0900-\u097F]/.test(p))) {
      return translated.join(" ");
    }
    return trimmed;
  } else {
    if (typeof customerOrName === "object" && customerOrName && customerOrName.name_en) {
      return customerOrName.name_en;
    }
    if (GLOBAL_NAME_MAP_HI_TO_EN[trimmed]) return GLOBAL_NAME_MAP_HI_TO_EN[trimmed];
    const parts = trimmed.split(/\s+/);
    const translated = parts.map((p) => GLOBAL_NAME_MAP_HI_TO_EN[p] || p);
    if (translated.some((p) => /^[A-Za-z]/.test(p))) {
      return translated.join(" ");
    }
    return trimmed;
  }
}

if (typeof window !== "undefined") {
  window.getLocalizedCustomerName = getLocalizedCustomerName;
}

// Auto-init when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initLang);
} else {
  initLang();
}
