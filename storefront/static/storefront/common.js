(function () {
  "use strict";

  function getCookie(name) {
    const match = document.cookie.split("; ").find((row) => row.startsWith(name + "="));
    return match ? decodeURIComponent(match.split("=")[1]) : "";
  }

  // Calls our JSON API with the login session cookie and the CSRF token.
  async function api(path, options = {}) {
    const hasBody = options.body !== undefined;
    const headers = { Accept: "application/json", "X-CSRFToken": getCookie("csrftoken") };
    if (hasBody) headers["Content-Type"] = "application/json";

    const response = await fetch(path, {
      method: options.method || "GET",
      headers,
      credentials: "same-origin",
      body: hasBody ? JSON.stringify(options.body) : undefined,
    });

    let data = null;
    try {
      data = await response.json();
    } catch (error) {
      // empty or non-JSON body
    }
    return { ok: response.ok, status: response.status, data };
  }

  function showToast(message) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => toast.classList.remove("show"), 2500);
  }

  // A logged-out visitor gets 401 or 403 from the cart API.
  function isAuthError(status) {
    return status === 401 || status === 403;
  }

  function goToLogin() {
    const next = window.location.pathname + window.location.search;
    window.location.href = "/login/?next=" + encodeURIComponent(next);
  }

  // Used by the "Add to cart" buttons on the book list.
  async function addToCart(bookId, button) {
    if (button) button.disabled = true;
    const result = await api("/api/cart/items/", {
      method: "POST",
      body: { bookId: bookId, quantity: 1 },
    });
    if (button) button.disabled = false;

    if (isAuthError(result.status)) {
      goToLogin();
      return;
    }
    if (result.ok) {
      showToast("Added to your cart.");
    } else {
      showToast((result.data && result.data.message) || "Could not add to cart.");
    }
  }

  window.bookstore = { api, getCookie, showToast, goToLogin, isAuthError };
  window.addToCart = addToCart;
})();