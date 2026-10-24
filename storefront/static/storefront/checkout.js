(function () {
  "use strict";

  const { api, showToast, goToLogin, isAuthError } = window.bookstore;

  const statusBox = document.getElementById("checkout-status");
  const main = document.getElementById("checkout-main");
  const summaryItems = document.getElementById("summary-items");
  const addressList = document.getElementById("address-list");
  const addressForm = document.getElementById("address-form");
  const addressError = document.getElementById("address-error");
  const toggleButton = document.getElementById("toggle-address");
  const couponInput = document.getElementById("coupon");
  const orderError = document.getElementById("order-error");
  const placeButton = document.getElementById("place-order");
  const confirmation = document.getElementById("confirmation");

  let cart = null;
  let addresses = [];
  let selectedAddressId = null;

  function money(value) {
    return (
      "₹" +
      Number(value).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    );
  }

  // Turns an API error into one readable sentence.
  function describeError(data) {
    if (!data) return "Something went wrong. Please try again.";
    if (data.details && typeof data.details === "object") {
      return Object.entries(data.details)
        .map(([field, problems]) => field.replace(/_/g, " ") + ": " + [].concat(problems).join(" "))
        .join(" ");
    }
    return data.message || data.error || "Something went wrong. Please try again.";
  }

  // ---- start-up ----
  async function init() {
    const [cartResult, addressResult] = await Promise.all([
      api("/api/cart/"),
      api("/api/addresses/"),
    ]);

    if (isAuthError(cartResult.status) || isAuthError(addressResult.status)) {
      goToLogin();
      return;
    }
    if (!cartResult.ok || !addressResult.ok) {
      statusBox.textContent = "Could not load checkout. Please try again.";
      return;
    }

    cart = cartResult.data;
    addresses = addressResult.data;

    if (cart.items.length === 0) {
      statusBox.textContent = "Your cart is empty, so there is nothing to check out.";
      return;
    }

    statusBox.textContent = "";
    renderSummary();
    renderAddresses();
    main.hidden = false;
  }

  // ---- order summary ----
  function renderSummary() {
    summaryItems.replaceChildren();
    cart.items.forEach((item) => {
      const li = document.createElement("li");
      const name = document.createElement("span");
      name.textContent = item.book.title + " × " + item.quantity;
      const price = document.createElement("span");
      price.textContent = money(item.line_total);
      li.append(name, price);
      summaryItems.appendChild(li);
    });
    document.getElementById("summary-subtotal").textContent = money(cart.subtotal);
  }

  // ---- addresses ----
  function showAddressForm(show) {
    addressForm.hidden = !show;
    toggleButton.hidden = show && addresses.length === 0;
    toggleButton.textContent = show ? "Cancel" : "Add a new address";
  }

  function renderAddresses() {
    addressList.replaceChildren();

    if (addresses.length === 0) {
      selectedAddressId = null;
      showAddressForm(true);
      return;
    }

    if (!addresses.some((a) => a.id === selectedAddressId)) {
      const preferred = addresses.find((a) => a.is_default) || addresses[0];
      selectedAddressId = preferred.id;
    }
    addresses.forEach((address) => addressList.appendChild(addressOption(address)));
    showAddressForm(false);
  }

  function addressOption(address) {
    const label = document.createElement("label");
    label.className = "address-option";

    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "address";
    radio.value = address.id;
    radio.checked = address.id === selectedAddressId;
    radio.addEventListener("change", () => {
      selectedAddressId = address.id;
    });

    const text = document.createElement("span");
    text.textContent = [
      address.recipient_name,
      address.line1,
      address.line2,
      address.city + ", " + address.state + " " + address.postal_code,
      address.country,
    ]
      .filter(Boolean)
      .join(", ");

    label.append(radio, text);
    return label;
  }

  toggleButton.addEventListener("click", () => {
    showAddressForm(addressForm.hidden);
  });

  addressForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    addressError.textContent = "";

    const body = Object.fromEntries(new FormData(addressForm));
    const result = await api("/api/addresses/", { method: "POST", body: body });

    if (isAuthError(result.status)) {
      goToLogin();
      return;
    }
    if (!result.ok) {
      addressError.textContent = describeError(result.data);
      return;
    }

    addresses.push(result.data);
    selectedAddressId = result.data.id;
    addressForm.reset();
    renderAddresses();
    showToast("Address saved.");
  });

  // ---- placing the order ----
  placeButton.addEventListener("click", async () => {
    orderError.textContent = "";

    if (!selectedAddressId) {
      orderError.textContent = "Please choose or add a delivery address.";
      return;
    }

    const body = { cartId: cart.id, addressId: selectedAddressId };
    const coupon = couponInput.value.trim();
    if (coupon) body.couponCode = coupon;

    placeButton.disabled = true; // stops a double click from placing two orders
    const result = await api("/api/orders/checkout", { method: "POST", body: body });
    placeButton.disabled = false;

    if (isAuthError(result.status)) {
      goToLogin();
      return;
    }
    if (!result.ok) {
      orderError.textContent = describeError(result.data);
      return;
    }
    showConfirmation(result.data);
  });

  // The API also returns a paymentUrl, but it is a placeholder until the payment
  // gateway story is built, so the page stays here and shows the order instead.
  function showConfirmation(order) {
    main.hidden = true;
    document.getElementById("conf-id").textContent = "#" + order.orderId;
    document.getElementById("conf-status").textContent = order.status;
    document.getElementById("conf-total").textContent = money(order.totalAmount);

    const couponNote = document.getElementById("conf-coupon");
    if (order.couponCode) {
      couponNote.textContent = "Coupon applied: " + order.couponCode;
      couponNote.hidden = false;
    }

    confirmation.hidden = false;
    confirmation.focus();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  init();
})();