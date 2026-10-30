const { test } = require("node:test");
const assert = require("node:assert/strict");
const A = require("../src/analytics.js");
const { BOOKS, MONTHLY_SALES } = require("../src/data.js");

test("stockStatus boundaries", () => {
  assert.equal(A.stockStatus(0), "Out of stock");
  assert.equal(A.stockStatus(-1), "Out of stock");
  assert.equal(A.stockStatus(1), "Low stock");
  assert.equal(A.stockStatus(5), "Low stock");
  assert.equal(A.stockStatus(6), "In stock");
});

test("lastMonths returns the newest n and handles n > length", () => {
  const r = A.lastMonths(MONTHLY_SALES, 3);
  assert.equal(r.length, 3);
  assert.equal(r[2].month, "Oct 2026");
  assert.equal(A.lastMonths(MONTHLY_SALES, 99).length, MONTHLY_SALES.length);
});

test("summarize totals and average order value", () => {
  const s = A.summarize([{ revenue: 1000, orders: 4 }, { revenue: 500, orders: 1 }]);
  assert.deepEqual(s, { revenue: 1500, orders: 5, avgOrderValue: 300 });
  assert.deepEqual(A.summarize([]), { revenue: 0, orders: 0, avgOrderValue: 0 });
});

test("monthOverMonth", () => {
  assert.equal(A.monthOverMonth([{ revenue: 100 }, { revenue: 110 }]), 10);
  assert.equal(A.monthOverMonth([{ revenue: 200 }, { revenue: 150 }]), -25);
  assert.equal(A.monthOverMonth([{ revenue: 100 }]), null);
  assert.equal(A.monthOverMonth([{ revenue: 0 }, { revenue: 50 }]), null);
});

test("topSellers sorts by units and does not mutate input", () => {
  const copy = JSON.stringify(BOOKS);
  const top = A.topSellers(BOOKS, 2);
  assert.equal(top[0].title, "Atomic Habits");
  assert.equal(top.length, 2);
  assert.equal(JSON.stringify(BOOKS), copy);
});

test("revenueByCategory aggregates and sorts descending", () => {
  const r = A.revenueByCategory([
    { category: "A", price: 10, sold: 5 },
    { category: "B", price: 100, sold: 1 },
    { category: "A", price: 10, sold: 10 },
  ]);
  assert.deepEqual(r, [{ category: "B", revenue: 100 }, { category: "A", revenue: 150 }].sort((a, b) => b.revenue - a.revenue));
});

test("inventoryKpis counts low and out of stock separately", () => {
  const k = A.inventoryKpis(BOOKS);
  assert.equal(k.titles, 8);
  assert.equal(k.outOfStock, 1);
  assert.equal(k.lowStock, 2);
});

test("filterBooks matches title or category, case-insensitive, trims", () => {
  assert.equal(A.filterBooks(BOOKS, "  CLEAN ").length, 1);
  assert.equal(A.filterBooks(BOOKS, "technology").length, 3);
  assert.equal(A.filterBooks(BOOKS, "").length, BOOKS.length);
  assert.equal(A.filterBooks(BOOKS, "zzz").length, 0);
});

test("toCsv escapes quotes/commas and neutralises formula injection", () => {
  const csv = A.toCsv(
    [{ a: 'He said "hi", ok', b: "=SUM(A1)" }],
    [{ key: "a", label: "A" }, { key: "b", label: "B" }]
  );
  assert.equal(csv, 'A,B\n"He said ""hi"", ok",\'=SUM(A1)');
});
