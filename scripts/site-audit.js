const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const htmlPath = path.join(root, "index.html");
const worksIndexPath = path.join(root, "assets", "works", "index.json");
const materialsDir = path.join(root, "materials");
const materialsHtmlPath = path.join(materialsDir, "index.html");
const materialsCssPath = path.join(materialsDir, "materials.css");
const materialsJsPath = path.join(materialsDir, "materials.js");
const materialsConfigPath = path.join(materialsDir, "config.json");
const materialsDataPath = path.join(materialsDir, "data", "assets.json");

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

if (!html.includes('href="materials/"') || !html.includes('<strong>Materials</strong><span>素材库</span>')) {
  fail("Main navigation should include Materials / 素材库 linking to materials/.");
}
if (!html.includes('{ url: "materials/", title: "Materials"')) {
  fail("Home search index should include the Materials page.");
}
if (!/\.home-m3-nav\s*\{[^}]*grid-template-columns:\s*repeat\(5,\s*minmax\(0,\s*1fr\)\)/.test(html)) {
  fail("Home center navigation should keep all five links on one row.");
}

[
  materialsHtmlPath,
  materialsCssPath,
  materialsJsPath,
  materialsConfigPath,
  materialsDataPath,
].forEach((filePath) => {
  if (!fs.existsSync(filePath)) fail(`Materials page file is missing: ${path.relative(root, filePath)}.`);
});

if (fs.existsSync(materialsHtmlPath)) {
  const materialsHtml = read(materialsHtmlPath);
  const visibleMaterialsHtml = stripNonVisibleBlocks(materialsHtml);
  checkNoCorruption("visible materials/index.html", visibleMaterialsHtml);
  [
    "Materials",
    "素材库",
    "搜索素材",
    "分类",
    "文件类型",
    "标签",
    "素材上传",
    "暂无素材",
  ].forEach((term) => {
    if (!visibleMaterialsHtml.includes(term)) fail(`Materials page is missing visible text: ${term}.`);
  });
  ["grid", "list", "folder"].forEach((view) => {
    if (!materialsHtml.includes(`data-view="${view}"`)) fail(`Materials page is missing ${view} view control.`);
  });
  if (!materialsHtml.includes('href="../index.html#home"')) {
    fail("Materials page should link back to the main site home route.");
  }
}

if (fs.existsSync(materialsCssPath)) {
  const materialsCss = read(materialsCssPath);
  if (!materialsCss.includes("--page: #fff;")) {
    fail("Materials page background should match the main site's white background.");
  }
  if (!materialsCss.includes("background: rgba(255, 255, 255, .88);")) {
    fail("Materials header background should match the white page background.");
  }
}

if (fs.existsSync(materialsJsPath)) {
  const materialsJs = read(materialsJsPath);
  try {
    new Function(materialsJs);
  } catch (error) {
    fail(`materials.js syntax error: ${error.message}`);
  }
  ["manifestUrl", "mediaBaseUrl", "renderAssets", "applyFilters"].forEach((term) => {
    if (!materialsJs.includes(term)) fail(`materials.js is missing required data hook: ${term}.`);
  });
}

if (fs.existsSync(materialsConfigPath)) {
  const config = JSON.parse(read(materialsConfigPath));
  if (!Object.prototype.hasOwnProperty.call(config, "manifestUrl")) fail("Materials config is missing manifestUrl.");
  if (!Object.prototype.hasOwnProperty.call(config, "mediaBaseUrl")) fail("Materials config is missing mediaBaseUrl.");
  if (!Object.prototype.hasOwnProperty.call(config, "uploadUrl")) fail("Materials config is missing uploadUrl.");
}

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
if (secondaryCards.length !== worksIndex.length) {
  fail(`Works page should render ${worksIndex.length} regular work cards, got ${secondaryCards.length}.`);
}
if ((html.match(/data-filter=/g) || []).length !== 3) {
  fail("Works page should render 3 category filter buttons.");
}
const worksPageMatch = html.match(/<section class="page" id="page-works">([\s\S]*?)<section class="page" id="page-work-/);
const worksPageHtml = worksPageMatch?.[1] || "";
if (stripNonVisibleBlocks(worksPageHtml).includes("\u5168\u90e8\u5206\u7c7b")) {
  fail("Works page should not show an all-category filter button.");
}
if ((html.match(/work-story original-note/g) || []).length !== worksIndex.length) {
  fail("Each work detail page must render one original-note body block.");
}
const originalNoteCss = html.match(/\.work-story\.original-note \{[\s\S]*?\}/)?.[0] || "";
if (originalNoteCss.includes("border-top") || originalNoteCss.includes("border-bottom")) {
  fail("Original note body should not use a hard horizontal divider.");
}
if (html.includes('<a class="work-featured"')) {
  fail("Works page should not render the old static featured card.");
}
if (!html.includes('<div class="section-head"><h1>WORKS</h1></div>')) {
  fail("Works page title should be WORKS.");
}
if (!html.includes('class="works-spotlight" data-works-spotlight')) {
  fail("Works page should include a scoped recent spotlight module.");
}
const latestFiveRoutes = worksIndex
  .slice()
  .sort((a, b) => String(b.publishedAt).localeCompare(String(a.publishedAt)))
  .slice(0, 5)
  .map((work) => `work-${work.slug}`);
const spotlightRoutesMatch = scriptMatch?.[1].match(/const spotlightItems = \[([\s\S]*?)\];/);
const spotlightRouteText = spotlightRoutesMatch?.[1] || "";
let previousRouteIndex = -1;
for (const route of latestFiveRoutes) {
  const routeIndex = spotlightRouteText.indexOf(`route: "${route}"`);
  if (routeIndex === -1) {
    fail(`Works spotlight is missing recent work route: ${route}.`);
  }
  if (routeIndex < previousRouteIndex) {
    fail("Works spotlight routes should follow publishedAt descending order.");
  }
  previousRouteIndex = routeIndex;
}
if (!html.includes("#page-works .works-board [data-work-type]")) {
  fail("Works filter must only target cards inside .works-board.");
}
if (!html.includes("applyWorkFilter(\"\")")) {
  fail("Works page should default to the unfiltered regular card collection.");
}
if (html.includes("works-selector") || html.includes("worksData")) {
  fail("Works page must not use the old full-page selector implementation.");
}
if (!html.includes("width: min(300px, 100%)")) {
  fail("Spotlight active title should have a bounded width to avoid image overlap.");
}
if (!html.includes("{ x: 64, y: 218")) {
  fail("Spotlight active title should stay inside the left text area.");
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
