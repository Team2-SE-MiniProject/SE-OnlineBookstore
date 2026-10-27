# [BOOK-NF-005] WCAG 2.1 AA accessibility pass (#58)

Ref: SRS BOOK-NF-005 | SAD 4.5 UX Design | Test: TC-UX-01 | 2 story points | Sprint 2 (due 30 Oct 2026)

## Scope note
The acceptance criteria name the **storefront** browse, cart and checkout flows. The storefront code was not available when this was prepared, so:

- The seller dashboard and sales analytics pages (#51, #53) were built to AA and **verified** (below).
- `src/styles.css` is a reusable accessible baseline (focus, contrast tokens, 44px targets, reduced motion, forced colours).
- `tools/a11y-check.js` and `tools/contrast.js` are ready to run on the storefront templates. **That run is the remaining step to tick the two acceptance criteria.**

## Acceptance criteria
| Criterion | Status |
|---|---|
| Browse, cart and checkout flows pass an accessibility check | **Pending** – run the commands in "How to verify the storefront" |
| Colour contrast, labels and keyboard navigation are fixed | **Done for seller pages**; apply `styles.css` tokens to the storefront |

## Verified results (seller pages)
| Check | Result |
|---|---|
| Static checker (`a11y-check.js`) on both pages | PASS: lang, title, viewport, one h1, main landmark, skip link, labelled controls, table captions + `scope`, no duplicate ids |
| Contrast (`contrast.js`), 11 pairs | PASS: lowest text ratio 6.64:1 (min 4.5); borders/focus ≥ 4.83:1 (min 3) |
| Rendered in jsdom, no script errors; search and range filter work | PASS |

## WCAG 2.1 AA mapping
| SC | How it is met |
|---|---|
| 1.1.1 Non-text content | Chart is `role="img"` with description; same data in a table under "View chart data as a table" |
| 1.3.1 Info and relationships | Landmarks, heading order, `<caption>`, `th scope`, `<label for>` |
| 1.4.1 Use of colour | Status always has text **and** a symbol (✔ ⚠ ✖) |
| 1.4.3 / 1.4.11 Contrast | See contrast table; tokens documented in `styles.css` |
| 1.4.4 / 1.4.10 Resize and reflow | rem units, no zoom lock, tables scroll in their own region, works at 320px |
| 2.1.1 Keyboard | Only native controls; scroll regions are focusable (`tabindex="0"`) |
| 2.4.1 Bypass blocks | Skip link to `#main` |
| 2.4.2 / 2.4.6 Titles, headings | Unique `<title>`, descriptive headings and labels |
| 2.4.7 Focus visible | 3px outline plus halo, never removed |
| 2.5.5 Target size (AAA, applied anyway) | 44×44px minimum for buttons, links, inputs |
| 3.1.1 Language | `<html lang="en">` |
| 3.3.2 Labels | Every input has a visible label |
| 4.1.2 Name, role, value | Native elements; `aria-current="page"` on nav |
| 4.1.3 Status messages | `role="status"` live region announces result counts and range changes |

## How to verify the storefront
```bash
node tools/a11y-check.js path/to/storefront/templates     # structural issues, exits 1 on failure
node tools/contrast.js "#777" "#fff"                       # check any colour pair
```
Then do this manual pass on browse → cart → checkout (about 20 minutes):
1. Unplug the mouse. Tab through each page: order is logical, focus is always visible, no traps, Enter/Space work on every control.
2. Zoom to 200% and to 320px width: nothing is cut off or needs two-direction scrolling.
3. Run Lighthouse (Accessibility) or the axe DevTools extension on each page; fix anything flagged.
4. Screen reader spot check (NVDA on Windows, VoiceOver on Mac): form errors in checkout are announced and tied to their fields (`aria-describedby`, `aria-invalid`).
5. Record results against TC-UX-01.

## Common storefront fixes to look for
- Icon-only buttons (cart, search, wishlist) need `aria-label`.
- Book cover `<img>` needs `alt` (title and author); decorative images use `alt=""`.
- Quantity steppers and payment form fields need real `<label>`s, not placeholders.
- Checkout errors: message next to the field, plus a summary at the top that receives focus.
- Light-grey placeholder and "disabled-looking" text often fails 4.5:1.
