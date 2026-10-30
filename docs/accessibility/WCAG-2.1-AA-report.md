# WCAG 2.1 AA accessibility pass (#58)

Ref: SRS BOOK-NF-005 | SAD 4.5 UX Design | Test: TC-UX-01

## Acceptance criteria status
| Criterion | Status |
|---|---|
| Browse, cart and checkout flows pass an accessibility check | **Pass**: static check on all storefront templates, and Lighthouse accessibility 100 / 100 / 100 (section 3) |
| Colour contrast, labels and keyboard navigation are fixed | Contrast and labels: **pass** (static and Lighthouse). Manual keyboard test: not recorded yet (section 4) |

## 1. Static template check (tools/accessibility/a11y-check.js)
Run from the project root:

    node tools/accessibility/a11y-check.js accounts bookstore cart catalog notifications orders reviews storefront wishlist

Checks: page language, title, viewport and zoom, one h1 per page, main landmark, skip link, labelled form controls, button and link names, image alt text, table captions and header scope, duplicate ids, positive tabindex, removed focus outlines.

Result: every storefront template passes (base, books, cart, checkout, login, register).
Base templates are only flagged for more than one h1, because child pages add their own h1.

## 2. Colour contrast (tools/accessibility/contrast.js)
    node tools/accessibility/contrast.js

Result: all checked pairs pass WCAG 2.1 AA (normal text at least 4.5:1, borders and focus at least 3:1). Use `node tools/accessibility/contrast.js "#fg" "#bg"` to test any other pair.

## 3. Live checks (Chrome DevTools, Lighthouse, Accessibility category, 29 Oct 2026)
| Page | URL | Lighthouse accessibility score | Notes |
|---|---|---|---|
| Browse | / | 100 | |
| Cart | /cart/ | 100 | Tested with an empty cart |
| Checkout | /checkout/ | 100 | Tested with an empty cart |

## 4. Keyboard navigation (Tab, Shift+Tab, Enter)
Not recorded in this change. A manual Tab-through of Browse, Cart and Checkout is still to be added.

## How to repeat the live checks
1. Run the site and log in.
2. Open each page, press F12, open Lighthouse, tick only Accessibility, click Analyze page load.
3. Press Tab through the page and note anything that cannot be reached or seen.
