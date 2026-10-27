// Sample data. Replace with API calls (e.g. GET /api/seller/books, /orders, /sales) when wiring to the backend.
const BOOKS = [
  { id: "B001", title: "The Pragmatic Programmer", category: "Technology", price: 899, stock: 18, sold: 124 },
  { id: "B002", title: "Clean Code", category: "Technology", price: 749, stock: 4, sold: 156 },
  { id: "B003", title: "Wings of Fire", category: "Biography", price: 299, stock: 42, sold: 310 },
  { id: "B004", title: "The Alchemist", category: "Fiction", price: 349, stock: 3, sold: 275 },
  { id: "B005", title: "Atomic Habits", category: "Self-help", price: 499, stock: 27, sold: 402 },
  { id: "B006", title: "Sapiens", category: "History", price: 599, stock: 9, sold: 198 },
  { id: "B007", title: "Godan", category: "Fiction", price: 199, stock: 0, sold: 87 },
  { id: "B008", title: "Introduction to Algorithms", category: "Technology", price: 1899, stock: 12, sold: 64 },
];

const MONTHLY_SALES = [
  { month: "Nov 2025", revenue: 84200, orders: 212 },
  { month: "Dec 2025", revenue: 121500, orders: 301 },
  { month: "Jan 2026", revenue: 97300, orders: 244 },
  { month: "Feb 2026", revenue: 88900, orders: 223 },
  { month: "Mar 2026", revenue: 102400, orders: 259 },
  { month: "Apr 2026", revenue: 95100, orders: 238 },
  { month: "May 2026", revenue: 110800, orders: 277 },
  { month: "Jun 2026", revenue: 118600, orders: 293 },
  { month: "Jul 2026", revenue: 104700, orders: 262 },
  { month: "Aug 2026", revenue: 126300, orders: 318 },
  { month: "Sep 2026", revenue: 133900, orders: 341 },
  { month: "Oct 2026", revenue: 141200, orders: 359 },
];

const RECENT_ORDERS = [
  { id: "ORD-1042", customer: "A. Sharma", total: 1248, status: "Shipped", date: "2026-10-26" },
  { id: "ORD-1041", customer: "R. Iyer", total: 499, status: "Processing", date: "2026-10-26" },
  { id: "ORD-1040", customer: "S. Khan", total: 2398, status: "Delivered", date: "2026-10-25" },
  { id: "ORD-1039", customer: "M. Das", total: 749, status: "Cancelled", date: "2026-10-24" },
  { id: "ORD-1038", customer: "P. Nair", total: 897, status: "Delivered", date: "2026-10-24" },
];

if (typeof module !== "undefined") module.exports = { BOOKS, MONTHLY_SALES, RECENT_ORDERS };
