const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const htmlPath = path.join(root, "motion-library.html");
const outputPath = path.join(root, "motion-library-data.json");
const page = fs.readFileSync(htmlPath, "utf8");

function decodeHtml(value) {
  return value
    .replace(/&#(\d+);/g, (_, code) => String.fromCodePoint(Number(code)))
    .replace(/&#x([0-9a-f]+);/gi, (_, code) => String.fromCodePoint(parseInt(code, 16)))
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, "&");
}

function stripTags(value) {
  return decodeHtml(value.replace(/<[^>]+>/g, "")).replace(/\s+/g, " ").trim();
}

function findBlockEnd(source, openBrace) {
  let depth = 0;
  let quote = "";
  for (let index = openBrace; index < source.length; index += 1) {
    const char = source[index];
    const previous = source[index - 1];
    if (quote) {
      if (char === quote && previous !== "\\") quote = "";
      continue;
    }
    if (char === '"' || char === "'") {
      quote = char;
      continue;
    }
    if (char === "{") depth += 1;
    if (char === "}") depth -= 1;
    if (depth === 0) return index;
  }
  throw new Error("Unclosed CSS block.");
}

function parseCss(source) {
  const rules = [];
  let index = 0;
  while (index < source.length) {
    const comment = source.indexOf("/*", index);
    if (comment === index || /^\s*$/.test(source.slice(index, comment >= 0 ? comment : source.length))) {
      if (comment >= 0) {
        const commentEnd = source.indexOf("*/", comment + 2);
        if (commentEnd < 0) break;
        index = commentEnd + 2;
        continue;
      }
    }
    while (/\s/.test(source[index] || "")) index += 1;
    if (index >= source.length) break;
    if (source.startsWith("/*", index)) {
      const commentEnd = source.indexOf("*/", index + 2);
      index = commentEnd < 0 ? source.length : commentEnd + 2;
      continue;
    }
    const openBrace = source.indexOf("{", index);
    if (openBrace < 0) break;
    const header = source.slice(index, openBrace).trim();
    const closeBrace = findBlockEnd(source, openBrace);
    const body = source.slice(openBrace + 1, closeBrace).trim();
    rules.push({ header, body });
    index = closeBrace + 1;
  }
  return rules;
}

function classMap(namespace, legacyRoot) {
  return {
    "motion-snippet": namespace,
    [legacyRoot]: null,
    "motion-box": `${namespace}-box`,
    "copy-cn": `${namespace}-title`,
    "copy-en": `${namespace}-subtitle`,
    "copy-split": `${namespace}-split`,
    "copy-count": `${namespace}-count`,
    "js-count": `${namespace}-counter`,
  };
}

function renameClasses(value, mapping, namespace) {
  return value.replace(/\.([a-zA-Z_][\w-]*)/g, (match, className) => {
    if (Object.prototype.hasOwnProperty.call(mapping, className)) {
      return mapping[className] ? `.${mapping[className]}` : "";
    }
    if (className.startsWith("tpl-")) return match;
    return `.${namespace}-${className}`;
  });
}

function renameHtmlClasses(value, mapping, namespace) {
  return value.replace(/class="([^"]+)"/g, (_, classNames) => {
    const renamed = classNames
      .split(/\s+/)
      .map((className) => {
        if (Object.prototype.hasOwnProperty.call(mapping, className)) return mapping[className];
        if (className.startsWith("tpl-")) return null;
        return `${namespace}-${className}`;
      })
      .filter(Boolean);
    return `class="${[...new Set(renamed)].join(" ")}"`;
  });
}

function isolateCss(fullCss, legacyRoot, namespace) {
  const rules = parseCss(fullCss);
  const mapping = classMap(namespace, legacyRoot);
  const selected = [];

  for (const rule of rules) {
    if (rule.header.startsWith("@keyframes")) continue;
    if (rule.header.startsWith("@")) continue;
    const selectors = rule.header.split(",").map((selector) => selector.trim());
    const legacyRootPattern = new RegExp(`\\.${legacyRoot}(?![\\w-])`);
    const effectSelectors = selectors.filter((selector) => legacyRootPattern.test(selector));
    const baseSelectors = selectors.filter((selector) => {
      if (/\.tpl-[\w-]+/.test(selector)) return false;
      return /\.(motion-snippet|motion-box|copy-cn|copy-en|copy-split|copy-count|js-count)\b/.test(selector);
    });
    const kept = effectSelectors.length ? effectSelectors : baseSelectors;
    if (!kept.length) continue;
    selected.push({
      header: renameClasses(kept.join(",\n"), mapping, namespace),
      body: rule.body,
    });
  }

  const selectedBody = selected.map((rule) => rule.body).join("\n");
  const keyframes = rules.filter((rule) => rule.header.startsWith("@keyframes"));
  const requiredKeyframes = keyframes.filter((rule) => {
    const name = rule.header.replace(/^@keyframes\s+/, "").trim();
    return new RegExp(`\\b${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`).test(selectedBody);
  });
  const keyframeMap = new Map(requiredKeyframes.map((rule) => {
    const name = rule.header.replace(/^@keyframes\s+/, "").trim();
    return [name, `${namespace}-${name}`];
  }));

  function renameKeyframes(value) {
    let output = value;
    for (const [from, to] of keyframeMap) output = output.replace(new RegExp(`\\b${from}\\b`, "g"), to);
    return output;
  }

  const cssRules = selected.map((rule) => `${rule.header}{${renameKeyframes(rule.body)}}`);
  const animationRules = requiredKeyframes.map((rule) => {
    const name = rule.header.replace(/^@keyframes\s+/, "").trim();
    return `@keyframes ${keyframeMap.get(name)}{${rule.body}}`;
  });
  return [...cssRules, ...animationRules].join("\n\n");
}

function scopeScript(script, namespace) {
  if (!script.trim()) return "";
  return `(() => {\n  const root = document.querySelector(".${namespace}");\n  if (!root) return;\n  const counters = root.querySelectorAll(".${namespace}-counter");\n  function runCount() {\n    counters.forEach((element) => {\n      const target = Number(element.dataset.target || 0);\n      const duration = 850;\n      const start = performance.now();\n      function tick(now) {\n        const progress = Math.min(1, (now - start) / duration);\n        const eased = 1 - Math.pow(1 - progress, 3);\n        element.textContent = String(Math.round(target * eased)).padStart(2, "0");\n        if (progress < 1) requestAnimationFrame(tick);\n      }\n      element.textContent = "00";\n      requestAnimationFrame(tick);\n    });\n  }\n  runCount();\n  window.setInterval(runCount, 2600);\n})();`;
}

const cardPattern = /<article\b[^>]*class="[^"]*effect-card[^"]*"[\s\S]*?(?=<article\b[^>]*class="[^"]*effect-card|<\/main>)/g;
const cards = [...page.matchAll(cardPattern)].map((match) => match[0]);

if (cards.length !== 64) throw new Error(`Expected 64 cards, found ${cards.length}.`);

const motions = cards.map((card, index) => {
  const number = String(index + 1).padStart(2, "0");
  const id = (card.match(/data-motion-id="([^"]+)"/) || [])[1];
  const namespace = `l1-motion-${number}`;
  const name = stripTags((card.match(/<div class="stage-info">[\s\S]*?<strong>([\s\S]*?)<\/strong>/) || [])[1] || "");
  const nameZh = stripTags((card.match(/<div class="stage-info">[\s\S]*?<small>([\s\S]*?)<\/small>/) || [])[1] || "");
  const technique = stripTags((card.match(/<div class="code-tools">\s*<span>([\s\S]*?)<\/span>/) || [])[1] || "");
  const encodedCode = (card.match(/<code\b[^>]*class="[^"]*snippet-code[^"]*"[^>]*>([\s\S]*?)<\/code>/) || [])[1] || "";
  const source = decodeHtml(encodedCode);
  const purpose = ((source.match(/用途：([^\n]+)/) || [])[1] || "").trim();
  const styleMatch = source.match(/<style>([\s\S]*?)<\/style>/);
  const scriptMatches = [...source.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((match) => match[1]).join("\n");
  const legacyRoot = (source.match(/class="motion-snippet\s+(tpl-[^"]+)"/) || [])[1];
  if (!legacyRoot || !styleMatch) throw new Error(`${id} source is incomplete.`);
  const sourceHtml = source
    .slice(0, source.indexOf("<style>"))
    .replace(/<!--[\s\S]*?-->/g, "")
    .trim();
  const mapping = classMap(namespace, legacyRoot);
  const html = renameHtmlClasses(sourceHtml, mapping, namespace);
  const css = isolateCss(styleMatch[1], legacyRoot, namespace);
  const js = scopeScript(scriptMatches, namespace);
  const description = purpose || `${nameZh}采用${technique}。`;
  return { id, namespace, name, nameZh, description, technique, html, css, js };
});

fs.writeFileSync(outputPath, `${JSON.stringify(motions, null, 2)}\n`, "utf8");
console.log(`Migrated ${motions.length} isolated motions to ${path.relative(root, outputPath)}.`);
