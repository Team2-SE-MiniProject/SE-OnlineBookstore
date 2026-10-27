# Sprint 2 – Vidya's issues

Covers #51 Seller dashboard, #53 Sales analytics, #58 WCAG 2.1 AA pass, and the #23 epic summary.

## Run it
No build step and no dependencies.

```bash
npm test                                   # unit tests (Node 18+)
npm run a11y                               # static accessibility check
npm run contrast                           # colour contrast check
npx serve src    # or just open src/seller-dashboard.html in a browser
```

## Layout
```
src/
  seller-dashboard.html, dashboard.js      #51
  sales-analytics.html, analytics-page.js  #53
  analytics.js                             pure logic (tested, reusable on a backend)
  data.js                                  sample data: replace with API calls
  styles.css                               accessible baseline (#58)
test/analytics.test.js
tools/a11y-check.js, tools/contrast.js     #58 verification tools
docs/                                      #58 report, #23 epic summary
```

## Porting into the real project
- Copy `analytics.js` as-is (it is plain JS functions) and call it from your service or components.
- Rebuild the markup in your templates or components; keep the same landmarks, labels, captions and `role="status"` regions.
- Copy the CSS custom properties and focus styles from `styles.css` into the global stylesheet.

## Suggested PR text
Title: `Seller dashboard, sales analytics and WCAG 2.1 AA pass (Sprint 2)`
Body: `Closes #51, Closes #53, Closes #58. Adds seller dashboard and sales analytics, accessibility tooling and report, and unit tests (9 passing).`
