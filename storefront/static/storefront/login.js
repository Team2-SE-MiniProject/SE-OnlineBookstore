(function () {
  "use strict";

  const form = document.getElementById("login-form");
  const errorBox = document.getElementById("form-error");
  const button = form.querySelector("button[type=submit]");

  // Only allow redirects to pages on this site.
  function safeNext() {
    const next = new URLSearchParams(window.location.search).get("next") || "/";
    return next.startsWith("/") && !next.startsWith("//") ? next : "/";
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.textContent = "";
    button.disabled = true;

    try {
      // The existing login endpoint expects a normal form post (not JSON).
      const response = await fetch(form.action, {
        method: "POST",
        body: new URLSearchParams(new FormData(form)),
        credentials: "same-origin",
      });

      let data = {};
      try {
        data = await response.json();
      } catch (error) {
        // not JSON
      }

      if (response.ok) {
        window.location.href = safeNext();
        return;
      }
      // The login endpoint answers {"error": ...}; other endpoints use {"message": ...}.
      errorBox.textContent = data.error || data.message || "Could not log in. Please try again.";
    } catch (error) {
      errorBox.textContent = "Could not reach the server. Please try again.";
    } finally {
      button.disabled = false;
    }
  });
})();