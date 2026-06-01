const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const htmlPath = path.join(root, "index.html");
const worksIndexPath = path.join(root, "assets", "works", "index.json");

const SOURCE_PLATFORM = "\u5c0f\u7ea2\u4e66";
const TYPE_IMAGE_TEXT = "\u56fe\u6587";
const TYPE_VIDEO = "\u89c6\u9891";
const TYPE_ARTICLE = "\u6587\u7ae0";
const ALLOWED_TYPES = new Set([TYPE_IMAGE_TEXT, TYPE_VIDEO, TYPE_ARTICLE]);
const KICKER_SEPARATOR = "\u00b7";

function read(filePath) {
  return fs.readFileSync(filePath, "utf8");
}

function stripHtml(value) {
  return value
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<[^>]*>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, "\"")
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

function stripNonVisibleBlocks(value) {
  return value
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?<\/style>/gi, "");
}

function fail(message) {
  failures.push(message);
}

function checkNoCorruption(label, value) {
  if (/[?]{2,}|\uFFFD|锟/.test(value)) {
    fail(`${label} contains replacement/question-mark corruption.`);
  }
}

const failures = [];
const html = read(htmlPath);
const visibleHtml = stripNonVisibleBlocks(html);
const worksIndex = JSON.parse(read(worksIndexPath));

const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) {
  fail("index.html is missing its inline script block.");
} else {
  try {
    new Function(scriptMatch[1]);
  } catch (error) {
    fail(`inline script syntax error: ${error.message}`);
  }
}

[
  "\u539f\u6587\u5185\u5bb9",
  "\u539f\u59cb\u5185\u5bb9\u5165\u53e3",
  "\u5f52\u6863\u5230 L-One",
  "source-card",
].forEach((term) => {
  if (visibleHtml.includes(term)) fail(`forbidden front-end text found: ${term}`);
});

checkNoCorruption("visible index.html", visibleHtml);
checkNoCorruption("assets/works/index.json", read(worksIndexPath));

if (visibleHtml.includes(` ${KICKER_SEPARATOR.replace(KICKER_SEPARATOR, "?")} `)) {
  fail("visible index.html contains a question-mark separator between labels.");
}

const secondaryCards = html.match(/class="work-card"/g) || [];
if (secondaryCards.length !== worksIndex.length - 1) {
  fail(`Works page should render ${worksIndex.length - 1} secondary work cards, got ${secondaryCards.length}.`);
}
if ((html.match(/data-filter=/g) || []).length !== 4) {
  fail("Works page should render 4 filter buttons.");
}
if ((html.match(/work-story original-note/g) || []).length !== worksIndex.length) {
  fail("Each work detail page must render one original-note body block.");
}
const originalNoteCss = html.match(/\.work-story\.original-note \{[\s\S]*?\}/)?.[0] || "";
if (originalNoteCss.includes("border-top") || originalNoteCss.includes("border-bottom")) {
  fail("Original note body should not use a hard horizontal divider.");
}
if (!html.includes(".works-board.is-filtered .work-featured[hidden]")) {
  fail("Filtered Works layout must not override hidden featured cards.");
}

for (const work of worksIndex) {
  const metadataPath = path.join(root, work.metadata);
  const metadataText = read(metadataPath);
  const metadata = JSON.parse(metadataText);
  const desc = String(metadata.desc || "").trim();

  checkNoCorruption(`${work.slug} metadata.json`, metadataText);

  if (metadata.sourcePlatform !== SOURCE_PLATFORM) {
    fail(`${work.slug} sourcePlatform should be ${SOURCE_PLATFORM}.`);
  }
  if (!ALLOWED_TYPES.has(metadata.type)) {
    fail(`${work.slug} type is not supported: ${metadata.type}.`);
  }
  if (work.sourcePlatform !== metadata.sourcePlatform) {
    fail(`${work.slug} index sourcePlatform does not match metadata.`);
  }
  if (work.type !== metadata.type) {
    fail(`${work.slug} index type does not match metadata.`);
  }
  if (String(metadata.sourcePlatform).includes("?") || String(metadata.type).includes("?")) {
    fail(`${work.slug} metadata platform/type contains question marks.`);
  }
  const cardTypePattern = new RegExp(`data-route="work-${work.slug}"[^>]*data-work-type="${metadata.type}"`);
  if (!cardTypePattern.test(html)) {
    fail(`${work.slug} Works card is missing or has the wrong data-work-type.`);
  }

  const minDescLength = metadata.type === TYPE_VIDEO ? 40 : 120;
  if (desc.length < minDescLength) {
    fail(`${work.slug} desc is too short for an archived ${metadata.type} note: ${desc.length} chars.`);
  }

  const sectionPattern = new RegExp(
    `<section class="page" id="page-work-${work.slug}">([\\s\\S]*?)(?=<section class="page" id="page-|<section class="page" id="page-videos">)`
  );
  const sectionMatch = html.match(sectionPattern);
  if (!sectionMatch) {
    fail(`${work.slug} detail section is missing.`);
    continue;
  }

  const section = sectionMatch[1];
  checkNoCorruption(`${work.slug} rendered section`, stripNonVisibleBlocks(section));
  if (section.includes(`${SOURCE_PLATFORM} ? ${metadata.type}`)) {
    fail(`${work.slug} rendered kicker uses a question-mark separator.`);
  }
  if (!section.includes(`${SOURCE_PLATFORM} ${KICKER_SEPARATOR} ${metadata.type}`)) {
    fail(`${work.slug} rendered kicker is missing normalized platform/type labels.`);
  }

  const bodyMatch = section.match(/<div class="work-story original-note">\s*<div class="story-body"><p>([\s\S]*?)<\/p><\/div>\s*<\/div>/);
  if (!bodyMatch) {
    fail(`${work.slug} original note body is missing.`);
    continue;
  }

  const renderedBody = stripHtml(bodyMatch[1]);
  const normalizedDesc = desc.replace(/\s+/g, " ").trim();
  if (renderedBody.length < Math.floor(normalizedDesc.length * 0.9)) {
    fail(`${work.slug} rendered body is shorter than metadata desc (${renderedBody.length}/${normalizedDesc.length}).`);
  }
  if (!renderedBody.includes(normalizedDesc.slice(0, 30))) {
    fail(`${work.slug} rendered body does not contain the start of metadata desc.`);
  }
}

if (failures.length) {
  console.error("Site audit failed:");
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}

console.log(`Site audit passed: ${worksIndex.length} works checked.`);
