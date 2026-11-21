/**
 * auth.js — Login & Registration tab switching, language integration,
 * and form submission for Bolta Khata.
 */

document.addEventListener("DOMContentLoaded", () => {
  // If user is already authenticated, redirect straight to dashboard
  if (typeof getToken === "function" && getToken()) {
    window.location.href = "dashboard.html";
    return;
  }

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
    if (isLoading) {
      btn.disabled = true;
      btn.dataset.originalText = btn.innerHTML;
      btn.innerHTML = `<span class="spinner"></span> <span>${typeof t === "function" ? t("pleaseWait", "Please wait...") : "Please wait..."}</span>`;
    } else {
      btn.disabled = false;
      btn.innerHTML = typeof t === "function" ? t(defaultKey, btn.dataset.originalText) : btn.dataset.originalText;
    }
  }

  // Handle Login submission
  if (formLogin) {
    formLogin.addEventListener("submit", async (e) => {
      e.preventDefault();

      const phone = document.getElementById("login-phone").value.trim();
      const password = document.getElementById("login-password").value.trim();
      const submitBtn = document.getElementById("btn-login-submit");

      // Validate 10-digit phone
      if (!/^[6-9]\d{9}$/.test(phone)) {
        showToast(
          typeof t === "function" && currentLanguage() === "hi"
            ? "कृपया सही 10-अंकों का मोबाइल नंबर दर्ज करें"
            : "Please enter a valid 10-digit mobile number",
          "error"
        );
        return;
      }

      if (!password) {
        showToast(
          typeof t === "function" && currentLanguage() === "hi"
            ? "कृपया पिन या पासवर्ड दर्ज करें"
            : "Please enter PIN or password",
          "error"
        );
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

        showToast(
          typeof t === "function" && currentLanguage() === "hi"
            ? "लॉगिन सफल!"
            : "Login successful!",
          "success"
        );
        setTimeout(() => {
          window.location.href = "dashboard.html";
        }, 500);
      } else {
        const msg = res.error || (currentLanguage() === "hi" ? "लॉगिन विफल रहा" : "Login failed");
        showToast(msg, "error");
      }
    });
  }

  // Handle Register submission
  if (formRegister) {
    formRegister.addEventListener("submit", async (e) => {
      e.preventDefault();

      const shopName = document.getElementById("reg-shop-name").value.trim();
      const ownerName = document.getElementById("reg-owner-name").value.trim();
      const phone = document.getElementById("reg-phone").value.trim();
      const password = document.getElementById("reg-password").value.trim();
      const submitBtn = document.getElementById("btn-register-submit");

      if (!shopName) {
        showToast(
          currentLanguage() === "hi" ? "दुकान का नाम आवश्यक है" : "Shop name is required",
          "error"
        );
        return;
      }

      if (!ownerName) {
        showToast(
          currentLanguage() === "hi" ? "दुकानदार का नाम आवश्यक है" : "Owner name is required",
          "error"
        );
        return;
      }

      if (!/^[6-9]\d{9}$/.test(phone)) {
        showToast(
          currentLanguage() === "hi" ? "कृपया 10-अंकों का मोबाइल नंबर दर्ज करें" : "Please enter a valid 10-digit mobile number",
          "error"
        );
        return;
      }

      if (password.length < 4) {
        showToast(
          currentLanguage() === "hi" ? "पिन कम से कम 4 अंकों का होना चाहिए" : "PIN must be at least 4 digits",
          "error"
        );
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

        showToast(
          currentLanguage() === "hi" ? "खाता बन गया!" : "Account created successfully!",
          "success"
        );
        setTimeout(() => {
          window.location.href = "dashboard.html";
        }, 500);
      } else {
        const msg = res.error || (currentLanguage() === "hi" ? "रजिस्ट्रेशन विफल रहा" : "Registration failed");
        showToast(msg, "error");
      }
    });
  }
});
