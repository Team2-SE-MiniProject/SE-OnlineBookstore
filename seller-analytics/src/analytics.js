// Pure logic (no DOM) so it can be unit tested and reused by a backend.
const LOW_STOCK_THRESHOLD = 5;

function stockStatus(stock) {
  if (stock <= 0) return "Out of stock";
  if (stock <= LOW_STOCK_THRESHOLD) return "Low stock";
  return "In stock";
}

function lastMonths(monthly, n) {
  return monthly.slice(Math.max(0, monthly.length - n));
}

function summarize(monthly) {
  const revenue = monthly.reduce((s, m) => s + m.revenue, 0);
  const orders = monthly.reduce((s, m) => s + m.orders, 0);
  return { revenue, orders, avgOrderValue: orders ? Math.round(revenue / orders) : 0 };
}

// Percent change of the last month vs the one before it. Returns null if not computable.
function monthOverMonth(monthly) {
  if (monthly.length < 2) return null;
  const prev = monthly[monthly.length - 2].revenue;
  const cur = monthly[monthly.length - 1].revenue;
  if (!prev) return null;
  return Math.round(((cur - prev) / prev) * 1000) / 10;
}

function topSellers(books, n) {
  return [...books].sort((a, b) => b.sold - a.sold).slice(0, n);
}

function revenueByCategory(books) {
  const map = {};
  for (const b of books) map[b.category] = (map[b.category] || 0) + b.sold * b.price;
  return Object.entries(map)
    .map(([category, revenue]) => ({ category, revenue }))
    .sort((a, b) => b.revenue - a.revenue);
}

function inventoryKpis(books) {
  return {
    titles: books.length,
    units: books.reduce((s, b) => s + b.stock, 0),
    lowStock: books.filter((b) => b.stock > 0 && b.stock <= LOW_STOCK_THRESHOLD).length,
    outOfStock: books.filter((b) => b.stock <= 0).length,
  };
}

function filterBooks(books, query) {
  const q = query.trim().toLowerCase();
  if (!q) return books;
  return books.filter((b) => b.title.toLowerCase().includes(q) || b.category.toLowerCase().includes(q));
}

function csvCell(v) {
  let s = String(v);
  if (/^[=+\-@]/.test(s)) s = "'" + s; // prevent spreadsheet formula injection
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

function toCsv(rows, columns) {
  const head = columns.map((c) => csvCell(c.label)).join(",");
  const body = rows.map((r) => columns.map((c) => csvCell(r[c.key])).join(","));
  return [head, ...body].join("\n");
}

const inr = (n) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

const api = { LOW_STOCK_THRESHOLD, stockStatus, lastMonths, summarize, monthOverMonth, topSellers, revenueByCategory, inventoryKpis, filterBooks, toCsv, inr };
if (typeof module !== "undefined") module.exports = api;
else window.Analytics = api;
