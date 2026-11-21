/**
 * auth.js — Login & Registration tab switching and form submission for Bolta Khata.
 */

document.addEventListener("DOMContentLoaded", () => {
  // If user is already authenticated, redirect straight to dashboard
  if (typeof getToken === "function" && getToken()) {
    window.location.href = "dashboard.html";
    return;
  }

  // Elements
  const tabLogin = document.getElementById("tab-login");
  const tabRegister = document.getElementById("tab-register");
  const formLogin = document.getElementById("form-login");
  const formRegister = document.getElementById("form-register");

  // Tab switching
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
  function setLoading(btn, isLoading, defaultText) {
    if (isLoading) {
      btn.disabled = true;
      btn.dataset.originalText = btn.innerHTML;
      btn.innerHTML = `<span class="spinner"></span> <span>कृपया प्रतीक्षा करें / Please wait...</span>`;
    } else {
      btn.disabled = false;
      btn.innerHTML = btn.dataset.originalText || defaultText;
    }
  }

  // Handle Login submission
  if (formLogin) {
    formLogin.addEventListener("submit", async (e) => {
      e.preventDefault();

      const phone = document.getElementById("login-phone").value.trim();
      const password = document.getElementById("login-password").value.trim();
      const submitBtn = formLogin.querySelector("button[type='submit']");

      // Validate 10-digit phone
      if (!/^[6-9]\d{9}$/.test(phone)) {
        showToast("कृपया सही 10-अंकों का मोबाइल नंबर डालें / Enter valid 10-digit mobile number", "error");
        return;
      }

      if (!password) {
        showToast("कृपया पिन या पासवर्ड डालें / Enter PIN or password", "error");
        return;
      }

      setLoading(submitBtn, true, "लॉगिन करें / Log In");

      const res = await login(phone, password);
      setLoading(submitBtn, false, "लॉगिन करें / Log In");

      if (res.ok && res.data) {
        const token = res.data.token;
        const shop = res.data.shop;

        setToken(token);
        if (shop) setShop(shop);

        showToast("लॉगिन सफल! / Login successful!", "success");
        setTimeout(() => {
          window.location.href = "dashboard.html";
        }, 500);
      } else {
        const msg = res.error || "लॉगिन विफल रहा / Login failed. Please check credentials.";
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
      const submitBtn = formRegister.querySelector("button[type='submit']");

      if (!shopName) {
        showToast("दुकान का नाम आवश्यक है / Shop name is required", "error");
        return;
      }

      if (!ownerName) {
        showToast("दुकानदार का नाम आवश्यक है / Owner name is required", "error");
        return;
      }

      if (!/^[6-9]\d{9}$/.test(phone)) {
        showToast("कृपया सही 10-अंकों का मोबाइल नंबर डालें / Enter valid 10-digit mobile number", "error");
        return;
      }

      if (password.length < 4) {
        showToast("पिन कम से कम 4 अंकों का होना चाहिए / PIN must be at least 4 digits", "error");
        return;
      }

      setLoading(submitBtn, true, "रजिस्टर करें / Register");

      const res = await register(shopName, ownerName, phone, password);
      setLoading(submitBtn, false, "रजिस्टर करें / Register");

      if (res.ok && res.data) {
        const token = res.data.token;
        const shop = res.data.shop;

        setToken(token);
        if (shop) setShop(shop);

        showToast("खाता बन गया! / Registration successful!", "success");
        setTimeout(() => {
          window.location.href = "dashboard.html";
        }, 500);
      } else {
        const msg = res.error || "रजिस्ट्रेशन विफल रहा / Registration failed.";
        showToast(msg, "error");
      }
    });
  }
});
