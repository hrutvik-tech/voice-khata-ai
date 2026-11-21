/**
 * auth.js — Login & Registration tab switching, bilingual language toggle,
 * and form submission for Bolta Khata.
 */

// Bilingual translations dictionary
const I18N = {
  en: {
    appTitle: "Bolta Khata",
    appSub: "बोलता खाता AI",
    tagline: "Voice-first digital ledger for Kirana shops",
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
    footerText: "Secure & simple digital voice ledger for Indian retail",
    enterValidPhone: "Please enter a valid 10-digit mobile number",
    enterPin: "Please enter PIN or password",
    shopRequired: "Shop name is required",
    ownerRequired: "Owner name is required",
    pinLength: "PIN must be at least 4 digits",
    loginSuccess: "Login successful!",
    loginFailed: "Login failed. Please check credentials.",
    regSuccess: "Account created successfully!",
    regFailed: "Registration failed.",
    waitMsg: "Please wait...",
  },
  hi: {
    appTitle: "बोलता खाता",
    appSub: "Bolta Khata AI",
    tagline: "किराना दुकानों का वॉइस डिजिटल बही-खाता",
    loginTab: "लॉगिन",
    registerTab: "नया खाता",
    phoneLabel: "मोबाइल नंबर",
    phonePlaceholder: "10 अंकों का मोबाइल नंबर",
    pinLabel: "पिन या पासवर्ड",
    pinPlaceholder: "4 या 6 अंकों का पिन",
    loginBtn: "लॉगिन करें",
    shopNameLabel: "दुकान का नाम",
    shopNamePlaceholder: "उदा. गुप्ता जनरल स्टोर",
    ownerNameLabel: "दुकानदार का नाम",
    ownerNamePlaceholder: "उदा. रमेश कुमार",
    regPinLabel: "पिन सेट करें",
    regPinPlaceholder: "4 अंकों का गुप्त पिन",
    registerBtn: "नया खाता बनाएं",
    footerText: "सुरक्षित और आसान वॉइस डिजिटल बही-खाता",
    enterValidPhone: "कृपया सही 10-अंकों का मोबाइल नंबर डालें",
    enterPin: "कृपया पिन या पासवर्ड डालें",
    shopRequired: "दुकान का नाम आवश्यक है",
    ownerRequired: "दुकानदार का नाम आवश्यक है",
    pinLength: "पिन कम से कम 4 अंकों का होना चाहिए",
    loginSuccess: "लॉगिन सफल!",
    loginFailed: "लॉगिन विफल रहा। कृपया विवरण जांचें।",
    regSuccess: "खाता बन गया!",
    regFailed: "रजिस्ट्रेशन विफल रहा।",
    waitMsg: "कृपया प्रतीक्षा करें...",
  },
};

/**
 * Apply the selected language to all page text and form controls.
 * @param {"en"|"hi"} lang
 */
function applyLanguage(lang) {
  const currentLang = lang === "hi" ? "hi" : "en";
  if (typeof setLang === "function") {
    setLang(currentLang);
  } else {
    localStorage.setItem("bk_lang", currentLang);
  }

  const strings = I18N[currentLang];

  // Language buttons active state
  const btnEn = document.getElementById("lang-btn-en");
  const btnHi = document.getElementById("lang-btn-hi");
  if (btnEn && btnHi) {
    if (currentLang === "en") {
      btnEn.classList.add("active");
      btnHi.classList.remove("active");
    } else {
      btnHi.classList.add("active");
      btnEn.classList.remove("active");
    }
  }

  // Header & branding
  const elTitle = document.getElementById("i18n-app-title");
  if (elTitle) elTitle.textContent = strings.appTitle;

  const elSub = document.getElementById("i18n-app-sub");
  if (elSub) elSub.textContent = strings.appSub;

  const elTagline = document.getElementById("i18n-tagline");
  if (elTagline) elTagline.textContent = strings.tagline;

  // Tabs
  const tabLogin = document.getElementById("tab-login");
  if (tabLogin) tabLogin.textContent = strings.loginTab;

  const tabRegister = document.getElementById("tab-register");
  if (tabRegister) tabRegister.textContent = strings.registerTab;

  // Login form labels & placeholders
  const lblLoginPhone = document.getElementById("lbl-login-phone");
  if (lblLoginPhone) lblLoginPhone.textContent = strings.phoneLabel;

  const inputLoginPhone = document.getElementById("login-phone");
  if (inputLoginPhone) inputLoginPhone.placeholder = strings.phonePlaceholder;

  const lblLoginPass = document.getElementById("lbl-login-password");
  if (lblLoginPass) lblLoginPass.textContent = strings.pinLabel;

  const inputLoginPass = document.getElementById("login-password");
  if (inputLoginPass) inputLoginPass.placeholder = strings.pinPlaceholder;

  const btnLoginSubmit = document.getElementById("btn-login-submit");
  if (btnLoginSubmit && !btnLoginSubmit.disabled) btnLoginSubmit.textContent = strings.loginBtn;

  // Register form labels & placeholders
  const lblRegShop = document.getElementById("lbl-reg-shop-name");
  if (lblRegShop) lblRegShop.textContent = strings.shopNameLabel;

  const inputRegShop = document.getElementById("reg-shop-name");
  if (inputRegShop) inputRegShop.placeholder = strings.shopNamePlaceholder;

  const lblRegOwner = document.getElementById("lbl-reg-owner-name");
  if (lblRegOwner) lblRegOwner.textContent = strings.ownerNameLabel;

  const inputRegOwner = document.getElementById("reg-owner-name");
  if (inputRegOwner) inputRegOwner.placeholder = strings.ownerNamePlaceholder;

  const lblRegPhone = document.getElementById("lbl-reg-phone");
  if (lblRegPhone) lblRegPhone.textContent = strings.phoneLabel;

  const inputRegPhone = document.getElementById("reg-phone");
  if (inputRegPhone) inputRegPhone.placeholder = strings.phonePlaceholder;

  const lblRegPass = document.getElementById("lbl-reg-password");
  if (lblRegPass) lblRegPass.textContent = strings.regPinLabel;

  const inputRegPass = document.getElementById("reg-password");
  if (inputRegPass) inputRegPass.placeholder = strings.regPinPlaceholder;

  const btnRegSubmit = document.getElementById("btn-register-submit");
  if (btnRegSubmit && !btnRegSubmit.disabled) btnRegSubmit.textContent = strings.registerBtn;

  // Footer
  const elFooter = document.getElementById("i18n-footer");
  if (elFooter) elFooter.textContent = strings.footerText;
}

document.addEventListener("DOMContentLoaded", () => {
  // If user is already authenticated, redirect straight to dashboard
  if (typeof getToken === "function" && getToken()) {
    window.location.href = "dashboard.html";
    return;
  }

  // Load saved language preference (default 'en')
  const initialLang = (typeof getLang === "function" ? getLang() : localStorage.getItem("bk_lang")) || "en";
  applyLanguage(initialLang);

  // Setup language button listeners
  const btnEn = document.getElementById("lang-btn-en");
  const btnHi = document.getElementById("lang-btn-hi");
  if (btnEn) btnEn.addEventListener("click", () => applyLanguage("en"));
  if (btnHi) btnHi.addEventListener("click", () => applyLanguage("hi"));

  // Tab switching
  const tabLogin = document.getElementById("tab-login");
  const tabRegister = document.getElementById("tab-register");
  const formLogin = document.getElementById("form-login");
  const formRegister = document.getElementById("form-register");

  if (tabLogin && tabRegister) {
    tabLogin.addEventListener("click", () => {
      tabLogin.classList.add("active");
      tabRegister.classList.remove("active");
      formLogin.classList.remove("hidden");
      formRegister.classList.add("hidden");
    });

    tabRegister.addEventListener("click", () => {
      tabRegister.classList.add("active");
      tabLogin.classList.remove("active");
      formRegister.classList.remove("hidden");
      formLogin.classList.add("hidden");
    });
  }

  // Helper: Toggle button loading state
  function setLoading(btn, isLoading, defaultKey) {
    const activeLang = (typeof getLang === "function" ? getLang() : localStorage.getItem("bk_lang")) || "en";
    const strings = I18N[activeLang];

    if (isLoading) {
      btn.disabled = true;
      btn.dataset.originalText = btn.innerHTML;
      btn.innerHTML = `<span class="spinner"></span> <span>${strings.waitMsg}</span>`;
    } else {
      btn.disabled = false;
      btn.innerHTML = strings[defaultKey] || btn.dataset.originalText;
    }
  }

  // Handle Login submission
  if (formLogin) {
    formLogin.addEventListener("submit", async (e) => {
      e.preventDefault();

      const activeLang = (typeof getLang === "function" ? getLang() : localStorage.getItem("bk_lang")) || "en";
      const strings = I18N[activeLang];

      const phone = document.getElementById("login-phone").value.trim();
      const password = document.getElementById("login-password").value.trim();
      const submitBtn = document.getElementById("btn-login-submit");

      // Validate 10-digit phone
      if (!/^[6-9]\d{9}$/.test(phone)) {
        showToast(strings.enterValidPhone, "error");
        return;
      }

      if (!password) {
        showToast(strings.enterPin, "error");
        return;
      }

      setLoading(submitBtn, true, "loginBtn");

      const res = await login(phone, password);
      setLoading(submitBtn, false, "loginBtn");

      if (res.ok && res.data) {
        const token = res.data.token;
        const shop = res.data.shop;

        setToken(token);
        if (shop) setShop(shop);

        showToast(strings.loginSuccess, "success");
        setTimeout(() => {
          window.location.href = "dashboard.html";
        }, 500);
      } else {
        const msg = res.error || strings.loginFailed;
        showToast(msg, "error");
      }
    });
  }

  // Handle Register submission
  if (formRegister) {
    formRegister.addEventListener("submit", async (e) => {
      e.preventDefault();

      const activeLang = (typeof getLang === "function" ? getLang() : localStorage.getItem("bk_lang")) || "en";
      const strings = I18N[activeLang];

      const shopName = document.getElementById("reg-shop-name").value.trim();
      const ownerName = document.getElementById("reg-owner-name").value.trim();
      const phone = document.getElementById("reg-phone").value.trim();
      const password = document.getElementById("reg-password").value.trim();
      const submitBtn = document.getElementById("btn-register-submit");

      if (!shopName) {
        showToast(strings.shopRequired, "error");
        return;
      }

      if (!ownerName) {
        showToast(strings.ownerRequired, "error");
        return;
      }

      if (!/^[6-9]\d{9}$/.test(phone)) {
        showToast(strings.enterValidPhone, "error");
        return;
      }

      if (password.length < 4) {
        showToast(strings.pinLength, "error");
        return;
      }

      setLoading(submitBtn, true, "registerBtn");

      const res = await register(shopName, ownerName, phone, password);
      setLoading(submitBtn, false, "registerBtn");

      if (res.ok && res.data) {
        const token = res.data.token;
        const shop = res.data.shop;

        setToken(token);
        if (shop) setShop(shop);

        showToast(strings.regSuccess, "success");
        setTimeout(() => {
          window.location.href = "dashboard.html";
        }, 500);
      } else {
        const msg = res.error || strings.regFailed;
        showToast(msg, "error");
      }
    });
  }
});
