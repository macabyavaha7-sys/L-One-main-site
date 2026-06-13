const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const htmlPath = path.join(root, "motion-library.html");
const dataPath = path.join(root, "motion-library-data.json");
const motions = JSON.parse(fs.readFileSync(dataPath, "utf8"));
let page = fs.readFileSync(htmlPath, "utf8");

function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function embedCode(motion) {
  const script = motion.js ? `\n<script>\n${motion.js}\n<\/script>` : "";
  return `<!-- ${motion.name} / ${motion.nameZh} -->\n${motion.html}\n\n<style>\n${motion.css}\n</style>${script}`;
}

function standaloneCode(motion) {
  const script = motion.js ? `\n  <script>\n${motion.js.split("\n").map((line) => `  ${line}`).join("\n")}\n  <\/script>` : "";
  return `<!doctype html>\n<html lang="zh-CN">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>${motion.name} / ${motion.nameZh}</title>\n  <style>\n${motion.css.split("\n").map((line) => `  ${line}`).join("\n")}\n  </style>\n</head>\n<body>\n${motion.html.split("\n").map((line) => `  ${line}`).join("\n")}${script}\n</body>\n</html>`;
}

function codePanel(motion) {
  const standalone = escapeHtml(standaloneCode(motion));
  const embed = escapeHtml(embedCode(motion));
  return `<details class="code-panel">
    <summary class="code-summary">
      <span class="summary-text">
        <span class="code-title">${motion.id.slice(-2)} · ${motion.name} / ${motion.nameZh}</span>
        <span class="code-note">点击展开代码</span>
      </span>
      <span class="summary-action">展开</span>
    </summary>
    <div class="code-body">
      <div class="code-tools">
        <span>${motion.technique}</span>
        <button class="copy-btn" type="button">复制代码</button>
      </div>
      <div class="code-version-switch" role="group" aria-label="代码版本">
        <button class="is-active" type="button" data-code-select="standalone">独立 HTML</button>
        <button type="button" data-code-select="embed">嵌入组件</button>
      </div>
      <pre><code class="snippet-code is-active" data-code-version="standalone" data-motion-id="${motion.id}">${standalone}</code></pre>
      <pre hidden><code class="snippet-code" data-code-version="embed" data-motion-id="${motion.id}">${embed}</code></pre>
    </div>
  </details>`;
}

for (const motion of motions) {
  const cardStart = page.indexOf(`<article class="effect-card" data-motion-id="${motion.id}">`);
  if (cardStart < 0) throw new Error(`Card not found: ${motion.id}.`);
  const nextCard = page.indexOf('<article class="effect-card" data-motion-id="', cardStart + 1);
  const cardEnd = nextCard >= 0 ? nextCard : page.indexOf("</main>", cardStart);
  const card = page.slice(cardStart, cardEnd);
  const panelPattern = /<details class="code-panel">[\s\S]*?<\/details>/;
  if (!panelPattern.test(card)) throw new Error(`Code panel not found: ${motion.id}.`);
  let updated = card.replace(panelPattern, codePanel(motion));
  updated = updated.replace(
    /(<div class="stage-info">[\s\S]*?<p>)[\s\S]*?(<\/p>)/,
    `$1${escapeHtml(motion.description)}$2`
  );
  page = page.slice(0, cardStart) + updated + page.slice(cardEnd);
}

page = page.replace(/[ \t]+$/gm, "");
fs.writeFileSync(htmlPath, page, "utf8");
console.log(`Rebuilt ${motions.length} Motion Library code panels.`);
