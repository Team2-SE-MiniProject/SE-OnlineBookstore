(function () {
  "use strict";

  const { api, showToast, goToLogin, isAuthError } = window.bookstore;

  const list = document.getElementById("cart-items");
  const summary = document.getElementById("cart-summary");
  const status = document.getElementById("cart-status");

  function money(value) {
    return (
      "₹" +
      Number(value).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    );
  }

  async function loadCart() {
    const result = await api("/api/cart/");
    if (isAuthError(result.status)) {
      goToLogin();
      return;
    }
    if (!result.ok) {
      status.textContent = "Could not load your cart.";
      return;
    }
    render(result.data);
  }

  // Runs a change (PATCH or DELETE). The API answers with the whole updated cart.
  async function change(path, options, successMessage) {
    const result = await api(path, options);
    if (isAuthError(result.status)) {
      goToLogin();
      return;
    }
    if (!result.ok) {
      showToast((result.data && result.data.message) || "Something went wrong.");
      await loadCart(); // put the page back in sync with the server
      return;
    }
    if (successMessage) showToast(successMessage);
    render(result.data);
  }

  function render(cart) {
    list.replaceChildren();

    if (cart.items.length === 0) {
      status.textContent = "Your cart is empty. Use the Books link above to find something to read.";
      summary.hidden = true;
      return;
    }

    status.textContent = "";
    cart.items.forEach((item) => list.appendChild(row(item)));
    document.getElementById("cart-count").textContent = cart.total_items;
    document.getElementById("cart-subtotal").textContent = money(cart.subtotal);
    summary.hidden = false;
  }

  function row(item) {
    const li = document.createElement("li");
    li.className = "cart-row";

    const cover = document.createElement("div");
    cover.className = "cart-cover";
    if (item.book.cover) {
      const img = document.createElement("img");
      img.src = item.book.cover;
      img.alt = "";
      img.addEventListener("error", () => img.remove());
      cover.appendChild(img);
    }

    const info = document.createElement("div");
    info.className = "cart-info";
    const title = document.createElement("h2");
    title.textContent = item.book.title;
    const author = document.createElement("p");
    author.className = "author";
    author.textContent = item.book.author;
    const price = document.createElement("p");
    price.textContent = money(item.book.price) + " each";
    info.append(title, author, price);

    const controls = document.createElement("div");
    controls.className = "cart-controls";

    const inputId = "qty-" + item.id;
    const label = document.createElement("label");
    label.htmlFor = inputId;
    label.textContent = "Quantity";

    const input = document.createElement("input");
    input.id = inputId;
    input.type = "number";
    input.min = "1";
    input.max = String(item.book.stock);
    input.value = item.quantity;
    input.addEventListener("change", () => {
      const quantity = parseInt(input.value, 10);
      if (!quantity || quantity < 1) {
        input.value = item.quantity;
        return;
      }
      change("/api/cart/items/" + item.id + "/", { method: "PATCH", body: { quantity: quantity } });
    });

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "btn btn-secondary";
    remove.textContent = "Remove";
    remove.setAttribute("aria-label", "Remove " + item.book.title + " from cart");
    remove.addEventListener("click", () =>
      change("/api/cart/items/" + item.id + "/", { method: "DELETE" }, "Removed from your cart.")
    );

    controls.append(label, input, remove);

    const lineTotal = document.createElement("p");
    lineTotal.className = "line-total";
    lineTotal.textContent = money(item.line_total);

    li.append(cover, info, controls, lineTotal);
    return li;
  }

  loadCart();
})();