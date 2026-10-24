(function () {
  "use strict";

  const { api } = window.bookstore;

  const form = document.getElementById("register-form");
  const errorBox = document.getElementById("form-error");
  const done = document.getElementById("register-done");
  const button = form.querySelector("button[type=submit]");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.textContent = "";

    const username = form.elements.username.value.trim();
    const email = form.elements.email.value.trim();
    const password = form.elements.password.value;
    const confirm = form.elements.password2.value;

    if (!username || !email || !password) {
      errorBox.textContent = "Please fill in your username, email and password.";
      return;
    }
    if (password !== confirm) {
      errorBox.textContent = "The two passwords do not match.";
      return;
    }

    button.disabled = true;
    try {
      // /accounts/register/ answers {code, message}; the message is written for people.
      const result = await api("/accounts/register/", {
        method: "POST",
        body: { username: username, email: email, password: password },
      });

      if (result.ok) {
        showDone(result.data);
        return;
      }
      errorBox.textContent =
        (result.data && (result.data.message || result.data.error)) ||
        "Could not register. Please try again.";
    } catch (error) {
      errorBox.textContent = "Could not reach the server. Please try again.";
    } finally {
      button.disabled = false;
    }
  });

  function showDone(data) {
    form.hidden = true;
    document.getElementById("done-message").textContent =
      (data && data.message) || "Registration successful. Check your email to verify your account.";
    done.hidden = false;
    done.focus();
  }
})();