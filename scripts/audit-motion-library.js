const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const dataPath = path.join(root, "motion-library-data.json");
const htmlPath = path.join(root, "motion-library.html");
const jsPath = path.join(root, "motion-library.js");
const cssPath = path.join(root, "motion-library.css");
const failures = [];

function fail(message) {
  failures.push(message);
}

if (!fs.existsSync(dataPath)) {
  fail("motion-library-data.json is missing.");
}

if (!fs.existsSync(htmlPath)) {
  fail("motion-library.html is missing.");
}
if (!fs.existsSync(jsPath)) fail("motion-library.js is missing.");
if (!fs.existsSync(cssPath)) fail("motion-library.css is missing.");

if (!failures.length) {
  const motions = JSON.parse(fs.readFileSync(dataPath, "utf8"));
  const page = fs.readFileSync(htmlPath, "utf8");
  const pageScript = fs.readFileSync(jsPath, "utf8");
  const pageStyles = fs.readFileSync(cssPath, "utf8");

  if (!pageScript.includes("data-code-select") || !pageScript.includes("data-code-version")) {
    fail("Motion Library JavaScript is missing code-version switching.");
  }
  if (!pageScript.includes('.snippet-code.is-active')) {
    fail("Copy logic should target the active code version only.");
  }
  if (!pageScript.includes('if (!document.execCommand("copy"))')) {
    fail("Clipboard fallback should report a failed copy operation.");
  }
  if (!pageStyles.includes(".code-version-switch")) {
    fail("Motion Library CSS is missing code-version switch styles.");
  }
  if (!pageStyles.includes("--page:#fff;")) {
    fail("Motion Library page background should match the main site's white background.");
  }
  if (page.includes("data-restore-cards") || pageScript.includes("data-restore-cards") || pageStyles.includes(".restore-btn")) {
    fail("Motion Library should not expose restore-deleted controls.");
  }

  if (!Array.isArray(motions) || motions.length !== 64) {
    fail(`Expected 64 motion records, found ${Array.isArray(motions) ? motions.length : "invalid data"}.`);
  }

  const ids = new Set();
  const namespaces = new Set();
  const descriptions = new Set();

  for (const motion of Array.isArray(motions) ? motions : []) {
    const required = ["id", "namespace", "name", "nameZh", "description", "technique", "html", "css", "js"];
    for (const field of required) {
      if (!Object.prototype.hasOwnProperty.call(motion, field)) fail(`${motion.id || "unknown"} is missing ${field}.`);
    }

    if (ids.has(motion.id)) fail(`Duplicate motion id: ${motion.id}.`);
    if (namespaces.has(motion.namespace)) fail(`Duplicate namespace: ${motion.namespace}.`);
    ids.add(motion.id);
    namespaces.add(motion.namespace);
    descriptions.add(motion.description);

    if (!/^motion-\d{2}$/.test(motion.id || "")) fail(`Invalid motion id: ${motion.id}.`);
    if (!/^l1-motion-\d{2}$/.test(motion.namespace || "")) fail(`Invalid namespace: ${motion.namespace}.`);

    const source = `${motion.html || ""}\n${motion.css || ""}\n${motion.js || ""}`;
    if (/\?\?|\uFFFD/.test(`${motion.name}${motion.nameZh}${motion.description}${motion.technique}${source}`)) {
      fail(`${motion.id} contains corrupted text.`);
    }
    const foreignNamespaces = [...source.matchAll(/l1-motion-\d{2}/g)]
      .map((match) => match[0])
      .filter((namespace) => namespace !== motion.namespace);
    if (foreignNamespaces.length) fail(`${motion.id} contains foreign namespaces: ${[...new Set(foreignNamespaces)].join(", ")}.`);

    if (/\.tpl-[a-z0-9-]+/i.test(source)) fail(`${motion.id} still contains legacy tpl-* selectors.`);
    if (/(^|[},\n])\s*(html|body|:root|\*)\s*[{,]/m.test(motion.css || "")) {
      fail(`${motion.id} contains a global CSS selector.`);
    }

    const keyframes = [...(motion.css || "").matchAll(/@keyframes\s+([\w-]+)/g)].map((match) => match[1]);
    for (const name of keyframes) {
      if (!name.startsWith(`${motion.namespace}-`)) fail(`${motion.id} has an unscoped keyframe: ${name}.`);
    }

    if (motion.js && !motion.js.includes(`.${motion.namespace}`)) {
      fail(`${motion.id} JavaScript is not scoped to its root namespace.`);
    }

    if (!page.includes(`data-motion-id="${motion.id}"`)) fail(`${motion.id} card is missing from the page.`);
    if (!page.includes(`data-code-version="standalone" data-motion-id="${motion.id}"`)) {
      fail(`${motion.id} standalone HTML code is missing from the page.`);
    }
    if (!page.includes(`data-code-version="embed" data-motion-id="${motion.id}"`)) {
      fail(`${motion.id} embed code is missing from the page.`);
    }
  }
  if (descriptions.size !== 64) fail(`Expected 64 motion-specific descriptions, found ${descriptions.size}.`);
}

if (failures.length) {
  console.error("Motion Library audit failed:");
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}

console.log("Motion Library audit passed: 64 isolated motions checked.");
