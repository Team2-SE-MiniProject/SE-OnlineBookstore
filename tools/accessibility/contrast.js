#!/usr/bin/env node
// WCAG 2.1 contrast ratio calculator. Usage: node tools/contrast.js           (checks this project's palette)
//                                           node tools/contrast.js #fff #777  (check any pair)
const lum = (hex) => {
  const h = hex.replace("#", "");
  const f = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(f.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

if (process.argv.length >= 4) {
  const r = ratio(process.argv[2], process.argv[3]);
  console.log(r.toFixed(2) + ":1  normal text " + (r >= 4.5 ? "PASS" : "FAIL") + ", large text/UI " + (r >= 3 ? "PASS" : "FAIL"));
  process.exit(r >= 4.5 ? 0 : 1);
}

const pairs = [
  ["body text", "#1a1a1a", "#ffffff", 4.5],
  ["muted text on white", "#4a4f5a", "#ffffff", 4.5],
  ["muted text on surface", "#4a4f5a", "#f4f6fa", 4.5],
  ["header text on primary", "#ffffff", "#0b4f9c", 4.5],
  ["active nav (primary on white)", "#0b4f9c", "#ffffff", 4.5],
  ["button text on primary", "#ffffff", "#0b4f9c", 4.5],
  ["success text", "#0f6b2f", "#ffffff", 4.5],
  ["warning text", "#8a4b00", "#ffffff", 4.5],
  ["error text", "#a31212", "#ffffff", 4.5],
  ["input/table border (UI component)", "#6b7280", "#ffffff", 3],
  ["focus ring", "#1a1a1a", "#ffffff", 3],
];
let bad = 0;
for (const [name, fg, bg, min] of pairs) {
  const r = ratio(fg, bg);
  if (r < min) bad++;
  console.log(`${r >= min ? "PASS" : "FAIL"}  ${r.toFixed(2).padStart(5)}:1 (min ${min})  ${name}  ${fg} on ${bg}`);
}
process.exit(bad ? 1 : 0);
