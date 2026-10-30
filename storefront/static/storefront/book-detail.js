(function () {
  "use strict";

  const { api, showToast, goToLogin, isAuthError } = window.bookstore;

  const root = document.querySelector(".book-detail");
  const bookId = root.dataset.bookId;
  const reviewsUrl = "/api/books/" + bookId + "/reviews/";

  const list = document.getElementById("review-list");
  const summary = document.getElementById("rating-summary");
  const status = document.getElementById("reviews-status");
  const moreButton = document.getElementById("more-reviews");
  const addButton = document.getElementById("add-to-cart");
  const form = document.getElementById("review-form"); // missing when logged out

  let page = 1;

  // ---- helpers ----
  function stars(value) {
    const full = Math.max(0, Math.min(5, Math.round(Number(value) || 0)));
    return "★".repeat(full) + "☆".repeat(5 - full);
  }

  function reviewerName(review) {
    const user = review.user;
    if (typeof user === "string" && user) return user;
    if (user && typeof user === "object") return user.username || user.name || "A reader";
    return review.username || review.reviewer || review.user_name || "A reader";
  }

  function dateText(review) {
    if (!review.created_at) return "";
    const date = new Date(review.created_at);
    if (isNaN(date)) return "";
    return " · " + date.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
  }

  function updateSummary(average, total) {
    if (!total) {
      summary.textContent = "No reviews yet.";
      return;
    }
    summary.textContent =
      stars(average) + " " + Number(average).toFixed(1) + " out of 5 (" +
      total + (total === 1 ? " review)" : " reviews)");
  }

  // ---- reviews list (text is set with textContent, so reviews can never inject HTML) ----
  function reviewItem(review) {
    const item = document.createElement("li");
    item.className = "review";

    const head = document.createElement("p");
    head.className = "review-head";

    const rating = document.createElement("span");
    rating.className = "stars";
    rating.setAttribute("aria-hidden", "true");
    rating.textContent = stars(review.rating);

    const ratingText = document.createElement("span");
    ratingText.className = "visually-hidden";
    ratingText.textContent = "Rated " + review.rating + " out of 5. ";

    const who = document.createElement("span");
    who.textContent = " " + reviewerName(review) + dateText(review);

    head.append(rating, ratingText, who);
    item.appendChild(head);

    if (review.comment) {
      const comment = document.createElement("p");
      comment.className = "review-comment";
      comment.textContent = review.comment;
      item.appendChild(comment);
    }
    return item;
  }

  async function loadReviews(reset) {
    if (reset) {
      page = 1;
      list.replaceChildren();
    }

    const result = await api(reviewsUrl + "?page=" + page);
    if (!result.ok) {
      status.textContent = "Could not load reviews.";
      return;
    }

    const data = result.data;
    updateSummary(data.average_rating, data.total);
    data.results.forEach((review) => list.appendChild(reviewItem(review)));

    status.textContent =
      list.children.length === 0 ? "No reviews yet. Be the first to write one." : "";
    moreButton.hidden = list.children.length >= data.total;
  }

  moreButton.addEventListener("click", () => {
    page += 1;
    loadReviews(false);
  });

  // ---- add to cart (addToCart comes from common.js) ----
  addButton.addEventListener("click", () => {
    window.addToCart(Number(bookId), addButton);
  });

  // ---- write a review ----
  if (form) {
    const errorBox = document.getElementById("review-error");
    const submit = form.querySelector("button[type=submit]");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      errorBox.textContent = "";

      const rating = form.elements.rating.value;
      if (!rating) {
        errorBox.textContent = "Please choose a rating from 1 to 5.";
        return;
      }

      submit.disabled = true;
      const result = await api(reviewsUrl, {
        method: "POST",
        body: { rating: Number(rating), comment: form.elements.comment.value },
      });
      submit.disabled = false;

      const code = result.data && result.data.code;
      if (isAuthError(result.status) && (result.status === 401 || code === "forbidden")) {
        goToLogin(); // the session ran out
        return;
      }
      if (!result.ok) {
        errorBox.textContent =
          (result.data && result.data.message) || "Could not save your review. Please try again.";
        return;
      }

      form.reset();
      showToast("Thanks, your review is saved.");
      loadReviews(true);
    });
  }

  loadReviews(true);
})();