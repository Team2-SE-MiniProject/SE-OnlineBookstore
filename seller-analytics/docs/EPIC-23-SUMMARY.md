# [EPIC] Seller & Admin Management (#23)

Sprint 2 progress for the sub-issues (epic shows 0/3 complete).

| Issue | Title | Assignee | Status in this change |
|---|---|---|---|
| #51 | Seller dashboard | vidyasriganesh | Built: `src/seller-dashboard.html` |
| #52 | Admin dashboard | (other member) | Not in this change |
| #53 | Sales analytics | vidyasriganesh | Built: `src/sales-analytics.html` |

Related, same assignee: #58 WCAG 2.1 AA accessibility pass (parent is epic #25, not #23). See `ACCESSIBILITY-REPORT-58.md`.

## #51 Seller dashboard
- Overview cards: titles listed, units in stock, low stock, out of stock, units sold
- Searchable inventory table with stock status (low stock = 5 units or fewer, set in `LOW_STOCK_THRESHOLD`)
- Recent orders table

## #53 Sales analytics
- Time range: 3 / 6 / 12 months
- Summary: revenue, orders, average order value, month-over-month change
- Revenue bar chart with a data-table alternative
- Top 5 books and revenue by category
- CSV export (formula-injection safe)

## Verification
- 9 unit tests on `analytics.js`: all pass
- Both pages render with no script errors; filters verified
- Accessibility static check and contrast check: pass

## Remaining before the epic can close
1. Replace `src/data.js` with real API calls (suggested: `GET /api/seller/books`, `/api/seller/orders`, `/api/seller/sales?months=n`) scoped to the logged-in seller.
2. Add server-side authorisation so a seller only sees their own data.
3. Port the pages into the project's framework and routing (logic in `analytics.js` is framework-free and reusable as-is).
4. #52 Admin dashboard (other assignee) completes the epic.

## PR checklist (from the issue template)
- [ ] Implement
- [ ] Write unit tests
- [ ] Raise a PR that references the issue (`Closes #51`, `Closes #53`, `Closes #58`)
- [ ] Repo owner reviews and merges
