(function () {
  const A = window.Analytics;
  const NS = "http://www.w3.org/2000/svg";
  const el = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };
  const row = (cells, headFirst) => {
    const tr = el("tr");
    cells.forEach((c, i) => {
      const isHead = headFirst && i === 0;
      const cell = el(isHead ? "th" : "td", c.text, c.num ? "num" : undefined);
      if (isHead) cell.scope = "row";
      tr.append(cell);
    });
    return tr;
  };

  function drawChart(data) {
    const W = 720, H = 300, m = { t: 20, r: 10, b: 50, l: 70 };
    const max = Math.max(...data.map((d) => d.revenue));
    const bw = (W - m.l - m.r) / data.length;
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("class", "chart");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", `Bar chart of monthly revenue for the last ${data.length} months. The same data is available in the table below.`);

    const add = (name, attrs, text) => {
      const n = document.createElementNS(NS, name);
      for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
      if (text !== undefined) n.textContent = text;
      svg.append(n);
    };
    add("line", { x1: m.l, y1: H - m.b, x2: W - m.r, y2: H - m.b, class: "axis" });
    add("line", { x1: m.l, y1: m.t, x2: m.l, y2: H - m.b, class: "axis" });
    add("text", { x: m.l - 6, y: m.t + 4, "text-anchor": "end" }, A.inr(max));
    add("text", { x: m.l - 6, y: H - m.b, "text-anchor": "end" }, "₹0");

    data.forEach((d, i) => {
      const h = ((H - m.t - m.b) * d.revenue) / max;
      const x = m.l + i * bw + bw * 0.15;
      add("rect", { x, y: H - m.b - h, width: bw * 0.7, height: h, class: "bar" });
      add("text", { x: x + (bw * 0.7) / 2, y: H - m.b + 16, "text-anchor": "middle" }, d.month.slice(0, 3));
    });
    const box = document.getElementById("chart");
    box.replaceChildren(svg);
  }

  function render(n) {
    const data = A.lastMonths(MONTHLY_SALES, n);
    const s = A.summarize(data);
    const mom = A.monthOverMonth(data);

    const items = [
      ["Revenue", A.inr(s.revenue)],
      ["Orders", String(s.orders)],
      ["Average order value", A.inr(s.avgOrderValue)],
      ["Latest month vs previous", mom === null ? "n/a" : (mom >= 0 ? "▲ +" : "▼ ") + mom + "%"],
    ];
    const ul = document.getElementById("summary");
    ul.replaceChildren();
    for (const [label, value] of items) {
      const li = el("li", undefined, "kpi");
      li.append(el("span", label, "label"), el("strong", value, "value"));
      ul.append(li);
    }

    drawChart(data);
    document.getElementById("chart-cap").textContent =
      `Revenue from ${data[0].month} to ${data[data.length - 1].month}. Highest month: ${data.reduce((a, b) => (b.revenue > a.revenue ? b : a)).month}.`;

    const mb = document.getElementById("m-body");
    mb.replaceChildren(...data.map((d) => row([{ text: d.month }, { text: A.inr(d.revenue), num: true }, { text: String(d.orders), num: true }], true)));

    document.getElementById("range-status").textContent = `Showing last ${n} months. Revenue ${A.inr(s.revenue)}, ${s.orders} orders.`;
  }

  document.getElementById("top-body").replaceChildren(
    ...A.topSellers(BOOKS, 5).map((b, i) =>
      row([{ text: String(i + 1) }, { text: b.title }, { text: String(b.sold), num: true }, { text: A.inr(b.sold * b.price), num: true }], false)
    )
  );
  document.getElementById("cat-body").replaceChildren(
    ...A.revenueByCategory(BOOKS).map((c) => row([{ text: c.category }, { text: A.inr(c.revenue), num: true }], true))
  );

  const select = document.getElementById("range");
  select.addEventListener("change", () => render(Number(select.value)));
  document.getElementById("export").addEventListener("click", () => {
    const data = A.lastMonths(MONTHLY_SALES, Number(select.value));
    const csv = A.toCsv(data, [{ key: "month", label: "Month" }, { key: "revenue", label: "Revenue (INR)" }, { key: "orders", label: "Orders" }]);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = "sales-analytics.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  });

  render(Number(select.value));
})();
