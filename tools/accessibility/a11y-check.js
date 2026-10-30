#!/usr/bin/env node
// Lightweight static WCAG 2.1 AA checker for HTML/templates (no dependencies).
// Usage: node tools/a11y-check.js <file-or-dir> [...]
// Covers structural checks only; pair with a manual keyboard + screen reader pass and axe/Lighthouse.
const fs = require("fs");
const path = require("path");

function collect(p, out = []) {
  const st = fs.statSync(p);
  if (st.isDirectory()) fs.readdirSync(p).forEach((f) => f !== "node_modules" && collect(path.join(p, f), out));
  else if (/\.(html?|ejs|hbs|jsx|tsx|vue|php|jinja2?)$/i.test(p)) out.push(p);
  return out;
}

function check(file) {
  const src = fs.readFileSync(file, "utf8");
  const issues = [];
  const add = (rule, msg) => issues.push(`${rule}: ${msg}`);
  const isPage = /<html[\s>]/i.test(src);

  if (isPage) {
    if (!/<html[^>]*\blang=/i.test(src)) add("3.1.1", "<html> has no lang attribute");
    if (!/<title>\s*\S/i.test(src)) add("2.4.2", "page has no <title>");
    if (!/<meta[^>]*name=["']viewport/i.test(src)) add("1.4.4", "missing viewport meta");
    if (/user-scalable\s*=\s*no|maximum-scale\s*=\s*1(\.0)?\b/i.test(src)) add("1.4.4", "viewport disables zoom");
    if (!/<main[\s>]/i.test(src) && !/role=["']main/i.test(src)) add("1.3.1", "no <main> landmark");
    if (!/class=["'][^"']*skip/i.test(src)) add("2.4.1", "no skip link found");
    // Template base files ({% block %}) get their <h1> from child templates, so only flag duplicates there.
    const h1s = (src.match(/<h1[\s>]/gi) || []).length;
    const isBaseTemplate = /\{%\s*block\s/.test(src);
    if (isBaseTemplate ? h1s > 1 : h1s !== 1) add("1.3.1", isBaseTemplate ? "base template has more than one <h1>" : "page should have exactly one <h1>");
  }

  for (const m of src.matchAll(/<img\b[^>]*>/gi)) if (!/\balt=/i.test(m[0])) add("1.1.1", `image without alt: ${m[0].slice(0, 60)}`);

  for (const m of src.matchAll(/<(input|select|textarea)\b[^>]*>/gi)) {
    const tag = m[0];
    if (/type=["'](hidden|submit|button|reset|image)["']/i.test(tag)) continue;
    const id = (tag.match(/\bid=["']([^"']+)["']/i) || [])[1];
    const labelled = /aria-label(ledby)?=/i.test(tag) || (id && new RegExp(`<label[^>]*\\bfor=["']${id}["']`, "i").test(src));
    if (!labelled) add("1.3.1/3.3.2", `form control without label: ${tag.slice(0, 70)}`);
  }

  for (const m of src.matchAll(/<button\b[^>]*>([\s\S]*?)<\/button>/gi)) {
    const text = m[1].replace(/<[^>]+>/g, "").trim();
    if (!text && !/aria-label/i.test(m[0])) add("4.1.2", "button without accessible name");
  }
  for (const m of src.matchAll(/<a\b[^>]*>([\s\S]*?)<\/a>/gi)) {
    const text = m[1].replace(/<[^>]+>/g, "").trim();
    if (!text && !/aria-label/i.test(m[0]) && !/<img[^>]*alt=["'][^"']+/i.test(m[1])) add("2.4.4", "link without accessible name");
    if (/^(click here|here|read more|more)$/i.test(text)) add("2.4.4", `vague link text "${text}"`);
  }
  for (const m of src.matchAll(/<(div|span)\b[^>]*\bonclick=/gi)) add("2.1.1", "click handler on <div>/<span>: use <button> or add role+tabindex+key handler");
  for (const m of src.matchAll(/tabindex=["']([1-9]\d*)["']/gi)) add("2.4.3", `positive tabindex (${m[1]}) breaks focus order`);
  if (/outline\s*:\s*(none|0)\b/i.test(src) && !/:focus-visible|:focus\b[^{]*\{[^}]*(box-shadow|border|outline\s*:\s*[^n0])/i.test(src)) add("2.4.7", "focus outline removed without replacement");

  for (const m of src.matchAll(/<table\b[\s\S]*?<\/table>/gi)) {
    if (!/<caption|aria-label|aria-labelledby/i.test(m[0])) add("1.3.1", "table without caption or label");
    if (!/<th\b[^>]*scope=/i.test(m[0])) add("1.3.1", "table headers missing scope");
  }
  const ids = [...src.matchAll(/\bid=["']([^"']+)["']/gi)].map((m) => m[1]);
  ids.filter((v, i) => ids.indexOf(v) !== i).forEach((d) => add("4.1.1", `duplicate id "${d}"`));

  return issues;
}

const targets = process.argv.slice(2);
if (!targets.length) { console.error("Usage: node a11y-check.js <file-or-dir> [...]"); process.exit(2); }
let total = 0;
for (const f of targets.flatMap((t) => collect(t))) {
  const issues = check(f);
  total += issues.length;
  console.log(`${issues.length ? "FAIL" : "PASS"}  ${f}`);
  issues.forEach((i) => console.log("   - " + i));
}
process.exit(total ? 1 : 0);
