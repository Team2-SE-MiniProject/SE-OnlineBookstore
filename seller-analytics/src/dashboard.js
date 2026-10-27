(function () {
  const A = window.Analytics;
  const el = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text; // textContent, never innerHTML: no XSS from book titles etc.
    if (cls) n.className = cls;
    return n;
  };

  // KPIs
  const k = A.inventoryKpis(BOOKS);
  const totalSold = BOOKS.reduce((s, b) => s + b.sold, 0);
  const kpis = [
    ["Titles listed", k.titles],
    ["Units in stock", k.units],
    ["Low stock titles", k.lowStock],
    ["Out of stock titles", k.outOfStock],
    ["Units sold (all time)", totalSold],
  ];
  const kpiList = document.getElementById("kpis");
  for (const [label, value] of kpis) {
    const li = el("li", undefined, "kpi");
    li.append(el("span", label, "label"), el("strong", String(value), "value"));
    kpiList.append(li);
  }

  // Inventory
  const statusClass = { "In stock": "ok", "Low stock": "warn", "Out of stock": "bad" };
  const statusIcon = { "In stock": "✔ ", "Low stock": "⚠ ", "Out of stock": "✖ " };
  const body = document.getElementById("inv-body");
  const live = document.getElementById("inv-status");

  function renderInventory(list) {
    body.replaceChildren();
    for (const b of list) {
      const tr = el("tr");
      const s = A.stockStatus(b.stock);
      const td = el("td");
      td.append(el("span", statusIcon[s] + s, "badge " + statusClass[s]));
      tr.append(
        el("th", b.title),
        el("td", b.category),
        el("td", A.inr(b.price), "num"),
        el("td", String(b.stock), "num"),
        td
      );
      tr.firstChild.scope = "row";
      body.append(tr);
    }
    if (!list.length) {
      const tr = el("tr");
      const td = el("td", "No books match your search.");
      td.colSpan = 5;
      tr.append(td);
      body.append(tr);
    }
    live.textContent = list.length + (list.length === 1 ? " book shown" : " books shown");
  }
  renderInventory(BOOKS);
  document.getElementById("search").addEventListener("input", (e) => renderInventory(A.filterBooks(BOOKS, e.target.value)));

  // Orders
  const ordBody = document.getElementById("ord-body");
  const orderIcon = { Delivered: "✔ ", Shipped: "➜ ", Processing: "… ", Cancelled: "✖ " };
  const orderCls = { Delivered: "ok", Shipped: "ok", Processing: "warn", Cancelled: "bad" };
  for (const o of RECENT_ORDERS) {
    const tr = el("tr");
    const th = el("th", o.id);
    th.scope = "row";
    const st = el("td");
    st.append(el("span", (orderIcon[o.status] || "") + o.status, "badge " + (orderCls[o.status] || "")));
    tr.append(th, el("td", o.customer), el("td", o.date), el("td", A.inr(o.total), "num"), st);
    ordBody.append(tr);
  }
})();
