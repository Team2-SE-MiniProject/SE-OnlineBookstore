(function () {
  "use strict";

  const PAGE_SIZE = 20; // keep in sync with PAGE_SIZE in catalog/views.py
  const FIELDS = ["q", "genre", "min_price", "max_price", "sort"];

  const form = document.getElementById("filters");
  const grid = document.getElementById("book-grid");
  const pager = document.getElementById("pager");
  const status = document.getElementById("status");

  let page = 1;
  let timer;

  // ---- keep the filters in the address bar so refresh and Back keep working ----
  function readUrl() {
    const params = new URLSearchParams(window.location.search);
    FIELDS.forEach((name) => {
      if (params.has(name)) form.elements[name].value = params.get(name);
    });
    page = parseInt(params.get("page"), 10) || 1;
  }

  function buildParams() {
    const params = new URLSearchParams();
    FIELDS.forEach((name) => {
      const value = form.elements[name].value.trim();
      if (value) params.set(name, value);
    });
    if (page > 1) params.set("page", page);
    return params;
  }

  // ---- loading ----
  async function load() {
    const params = buildParams();
    const query = params.toString();
    history.replaceState(null, "", query ? "?" + query : window.location.pathname);
    status.textContent = "Loading books…";

    try {
      const response = await fetch("/api/books/?" + query);
      const data = await response.json();
      if (!response.ok) {
        showMessage(data.message || "Could not load books.");
        return;
      }
      render(data);
    } catch (error) {
      showMessage("Could not reach the server. Please try again.");
    }
  }

  function showMessage(text) {
    status.textContent = text;
    grid.replaceChildren();
    pager.replaceChildren();
  }

  // ---- rendering (textContent only, so book data can never inject HTML) ----
  function render(data) {
    if (data.results.length === 0 && data.total > 0 && page > 1) {
      page = 1; // asked for a page that no longer exists
      load();
      return;
    }
    if (data.results.length === 0) {
      showMessage("No books match your search.");
      return;
    }

    const pages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
    status.textContent = data.total + (data.total === 1 ? " book found" : " books found");
    grid.replaceChildren(...data.results.map(card));
    renderPager(data.page, pages);
  }

  function card(book) {
    const item = document.createElement("li");
    item.className = "book-card";

    const cover = document.createElement("div");
    cover.className = "cover";
    if (book.cover) {
      const img = document.createElement("img");
      img.src = book.cover;
      img.alt = ""; // the title is right below, so don't read it twice
      img.loading = "lazy";
      img.addEventListener("error", () => img.remove()); // offline? leave the grey box
      cover.appendChild(img);
    }

    const title = document.createElement("h2");
    title.textContent = book.title;

    const author = document.createElement("p");
    author.className = "author";
    author.textContent = book.author;

    const price = document.createElement("p");
    price.className = "price";
    price.textContent =
      "₹" +
      Number(book.price).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });

    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn";
    button.textContent = "Add to cart";
    button.setAttribute("aria-label", "Add " + book.title + " to cart");
    // The cart is connected in the next step by defining window.addToCart(id, button).
    if (typeof window.addToCart === "function") {
      button.addEventListener("click", () => window.addToCart(book.id, button));
    } else {
      button.disabled = true;
      button.title = "Cart not connected yet";
    }

    item.append(cover, title, author, price, button);
    return item;
  }

  function renderPager(current, pages) {
    pager.replaceChildren();
    if (pages <= 1) return;

    const label = document.createElement("span");
    label.textContent = "Page " + current + " of " + pages;
    pager.append(
      pageButton("Previous", current - 1, current <= 1),
      label,
      pageButton("Next", current + 1, current >= pages)
    );
  }

  function pageButton(text, target, disabled) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-secondary";
    button.textContent = text;
    button.disabled = disabled;
    button.addEventListener("click", () => {
      page = target;
      load();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    return button;
  }

  // ---- events ----
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    page = 1;
    load();
  });

  form.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      page = 1;
      load();
    }, 300); // wait until typing pauses
  });

  readUrl();
  load();
})();