(function () {
  "use strict";

  const { api, showToast, goToLogin, isAuthError } = window.bookstore;

  const grid = document.getElementById("wishlist-grid");
  const status = document.getElementById("wishlist-status");

  function money(value) {
    return (
      "₹" +
      Number(value).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    );
  }

  async function load() {
    const result = await api("/api/wishlist/");
    if (isAuthError(result.status)) {
      goToLogin();
      return;
    }
    if (!result.ok) {
      status.textContent = "Could not load your wishlist.";
      return;
    }
    render(result.data);
  }

  function render(data) {
    grid.replaceChildren();

    if (data.total === 0) {
      status.textContent =
        "Your wishlist is empty. Open a book and choose \u201cSave for later\u201d to add it here.";
      return;
    }

    status.textContent = data.total + (data.total === 1 ? " saved book" : " saved books");
    data.items.forEach((item) => grid.appendChild(card(item.book)));
  }

  // Text is set with textContent, so book data can never inject HTML.
  function card(book) {
    const item = document.createElement("li");
    item.className = "book-card";

    const cover = document.createElement("div");
    cover.className = "cover";
    if (book.cover) {
      const img = document.createElement("img");
      img.src = book.cover;
      img.alt = "";
      img.loading = "lazy";
      img.addEventListener("error", () => img.remove());
      cover.appendChild(img);
    }

    const title = document.createElement("h2");
    const link = document.createElement("a");
    link.href = "/books/" + book.id + "/";
    link.textContent = book.title;
    title.appendChild(link);

    const author = document.createElement("p");
    author.className = "author";
    author.textContent = book.author;

    const price = document.createElement("p");
    price.className = "price";
    price.textContent = money(book.price);

    const stock = document.createElement("p");
    stock.className = "stock-note";
    stock.textContent = book.in_stock ? "In stock" : "Out of stock";

    const actions = document.createElement("div");
    actions.className = "card-actions";

    const addButton = document.createElement("button");
    addButton.type = "button";
    addButton.className = "btn";
    addButton.textContent = "Add to cart";
    addButton.setAttribute("aria-label", "Add " + book.title + " to cart");
    addButton.disabled = !book.in_stock;
    addButton.addEventListener("click", () => window.addToCart(book.id, addButton));

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "btn btn-secondary";
    removeButton.textContent = "Remove";
    removeButton.setAttribute("aria-label", "Remove " + book.title + " from wishlist");
    removeButton.addEventListener("click", () => remove(book.id));

    actions.append(addButton, removeButton);
    item.append(cover, title, author, price, stock, actions);
    return item;
  }

  async function remove(bookId) {
    const result = await api("/api/wishlist/" + bookId + "/", { method: "DELETE" });
    if (isAuthError(result.status)) {
      goToLogin();
      return;
    }
    if (!result.ok) {
      showToast((result.data && result.data.message) || "Could not remove it.");
      load(); // put the page back in sync with the server
      return;
    }
    showToast("Removed from your wishlist.");
    render(result.data); // the API answers with the updated wishlist
  }

  load();
})();