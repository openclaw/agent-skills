import type { SessionDocument } from "./core/types.ts";

export type HtmlOptions = {
  embedMode: "normalized" | "raw" | "blank";
  rawText?: string;
};

function base64Utf8(text: string): string {
  return Buffer.from(text, "utf8").toString("base64");
}

function htmlEscape(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function scriptJsonEscape(value: string): string {
  return value
    .replaceAll("<", "\\u003c")
    .replaceAll(">", "\\u003e")
    .replaceAll("&", "\\u0026")
    .replaceAll("\u2028", "\\u2028")
    .replaceAll("\u2029", "\\u2029");
}

function buildEmbeddedPayload(document: SessionDocument | null, options: HtmlOptions): string {
  if (options.embedMode === "normalized" && document) {
    return JSON.stringify({ kind: "normalized", data: base64Utf8(JSON.stringify(document)) });
  }
  if (options.embedMode === "raw") {
    return JSON.stringify({
      kind: "raw",
      data: base64Utf8(options.rawText ?? ""),
      warnings: document?.warnings ?? [],
    });
  }
  return JSON.stringify({ kind: "blank", data: "" });
}

export function buildSessionViewerHtml(
  document: SessionDocument | null,
  options: HtmlOptions,
): string {
  const payload = buildEmbeddedPayload(document, options);
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${htmlEscape(document?.title ?? "Session Viewer")}</title>
<script>
(() => {
  try {
    const stored = localStorage.getItem("session-viewer-theme") || "system";
    const dark = stored === "dark" || (stored === "system" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    document.documentElement.style.colorScheme = dark ? "dark" : "light";
  } catch {}
})();
</script>
<style>
:root {
  --bg: #f4f4f4;
  --panel: #ffffff;
  --panel-2: #ededed;
  --sidebar: rgba(247, 247, 247, .96);
  --sidebar-2: #eeeeee;
  --ink: #171717;
  --muted: #6f6f6f;
  --hair: #d1d1d1;
  --accent: #4b5563;
  --accent-2: #3f3f46;
  --tool: #525252;
  --ok: #525252;
  --warn: #737373;
  --user-bubble: #e9e9e9;
  --mark: #d9d9d9;
  --shadow: 0 1px 2px rgba(0, 0, 0, .05), 0 10px 30px rgba(0, 0, 0, .07);
  --control: #ffffff;
  --control-hover: #efefef;
  --radius: 10px;
  --radius-sm: 7px;
  --ring: color-mix(in srgb, var(--accent) 28%, transparent);
}
:root[data-theme="dark"] {
  --bg: #151515;
  --panel: #1f1f1f;
  --panel-2: #242424;
  --sidebar: rgba(22, 22, 22, .96);
  --sidebar-2: #1b1b1b;
  --ink: #ededed;
  --muted: #a3a3a3;
  --hair: #343434;
  --accent: #c4c4c4;
  --accent-2: #e5e5e5;
  --tool: #c2c2c2;
  --ok: #a3a3a3;
  --warn: #b8b8b8;
  --user-bubble: #262626;
  --mark: #3a3a3a;
  --shadow: 0 1px 2px rgba(0, 0, 0, .25), 0 14px 34px rgba(0, 0, 0, .32);
  --control: #262626;
  --control-hover: #303030;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  color: var(--ink);
  background:
    linear-gradient(90deg, rgba(0,0,0,.035) 1px, transparent 1px) 0 0/28px 28px,
    linear-gradient(0deg, rgba(0,0,0,.03) 1px, transparent 1px) 0 0/28px 28px,
    var(--bg);
  font-family: Avenir Next, Aptos, ui-sans-serif, system-ui, sans-serif;
  letter-spacing: 0;
}
button, input, select { font: inherit; letter-spacing: 0; }
#app { display: grid; grid-template-columns: 324px minmax(0, 1fr); min-height: 100vh; }
aside {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: auto;
  border-right: 1px solid var(--hair);
  background: var(--sidebar);
  backdrop-filter: blur(14px);
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
aside::-webkit-scrollbar { width: 10px; }
aside::-webkit-scrollbar-thumb { background: color-mix(in srgb, var(--muted) 32%, transparent); border-radius: 999px; border: 3px solid transparent; background-clip: padding-box; }
aside::-webkit-scrollbar-thumb:hover { background: color-mix(in srgb, var(--muted) 55%, transparent); background-clip: padding-box; }
main { min-width: 0; padding: 22px clamp(16px, 4vw, 56px) 80px; }
.brand { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.brand h1 { margin: 0; font-size: 15px; font-weight: 700; line-height: 1.1; letter-spacing: .01em; }
.brand span {
  color: var(--muted);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .08em;
  padding: 3px 8px;
  border: 1px solid var(--hair);
  border-radius: 999px;
  background: var(--panel-2);
}
.brand span:empty { display: none; }
.loader {
  border: 1px dashed var(--hair);
  border-radius: var(--radius);
  background: var(--sidebar-2);
  padding: 10px;
}
#file-input { width: 100%; font-size: 12px; color: var(--muted); cursor: pointer; }
#file-input::file-selector-button {
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
  background: var(--control);
  border: 1px solid var(--hair);
  border-radius: var(--radius-sm);
  padding: 6px 12px;
  margin-right: 10px;
  cursor: pointer;
  transition: background .15s ease, border-color .15s ease;
}
#file-input::file-selector-button:hover { background: var(--control-hover); border-color: var(--muted); }
.controls { display: grid; gap: 9px; }
.search-row { display: flex; gap: 7px; }
#search {
  width: 100%;
  border: 1px solid var(--hair);
  background: var(--control);
  color: var(--ink);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  min-height: 36px;
  transition: border-color .15s ease, box-shadow .15s ease;
}
#search::placeholder { color: var(--muted); }
.theme-select {
  width: 100%;
  border: 1px solid var(--hair);
  background: var(--control);
  color: var(--ink);
  padding: 8px 34px 8px 12px;
  min-height: 36px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23999' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  transition: border-color .15s ease, box-shadow .15s ease;
}
.filters { display: flex; flex-wrap: wrap; gap: 6px; }
.show-system { width: 100%; }
.chip, .icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--hair);
  background: var(--control);
  color: var(--ink);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  min-height: 30px;
  font-size: 12px;
  font-weight: 500;
  transition: background .15s ease, border-color .15s ease, color .15s ease, transform .08s ease;
}
.chip:hover, .icon-btn:hover { background: var(--control-hover); border-color: var(--muted); }
.chip:active, .icon-btn:active { transform: translateY(1px); }
.chip[aria-pressed="true"] { background: var(--ink); color: var(--panel); border-color: var(--ink); }
.chip[aria-pressed="true"]:hover { background: var(--ink); border-color: var(--ink); }
.icon-btn { min-width: 36px; padding: 6px; border-radius: var(--radius-sm); color: var(--muted); }
.chip:focus-visible, .icon-btn:focus-visible, #search:focus-visible, .theme-select:focus-visible, #file-input:focus-visible {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--ring);
}
.meta, .stats {
  border: 1px solid var(--hair);
  border-radius: var(--radius);
  background: var(--sidebar-2);
  padding: 11px 12px;
  font-size: 11px;
  color: var(--ink);
  display: grid;
  gap: 6px;
}
.meta div, .stats div { display: flex; align-items: baseline; gap: 10px; overflow-wrap: anywhere; }
.stats div { justify-content: space-between; font-variant-numeric: tabular-nums; }
.meta div b, .stats div b {
  flex: none;
  color: var(--muted);
  font-weight: 600;
  font-size: 9.5px;
  text-transform: uppercase;
  letter-spacing: .06em;
  white-space: nowrap;
}
.timeline { display: flex; flex-direction: column; gap: 2px; }
.nav-item {
  position: relative;
  width: 100%;
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  gap: 9px;
  align-items: baseline;
  text-align: left;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink);
  padding: 6px 9px;
  cursor: pointer;
  transition: background .12s ease;
}
.nav-item::before {
  content: "";
  position: absolute;
  left: 1px;
  top: 6px;
  bottom: 6px;
  width: 2px;
  border-radius: 2px;
  background: transparent;
  transition: background .12s ease;
}
.nav-item:hover { background: color-mix(in srgb, var(--accent) 11%, transparent); }
.nav-item:hover::before { background: var(--accent); }
.nav-item:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--ring); }
.nav-kind { color: var(--muted); font-size: 9px; text-transform: uppercase; font-weight: 700; letter-spacing: .04em; }
.nav-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11.5px; color: var(--muted); }
.nav-item:hover .nav-title { color: var(--ink); }
.header {
  max-width: 920px;
  margin: 0 auto 30px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: start;
}
.header h2 {
  margin: 0;
  font-size: 18px;
  line-height: 1.25;
  max-width: 42ch;
  overflow-wrap: anywhere;
}
.header p { margin: 5px 0 0; color: var(--muted); font-size: 12px; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: end; }
.event-list { max-width: 920px; margin: 0 auto; display: grid; gap: 0; }
.event {
  background: transparent;
  border: 0;
  box-shadow: none;
  margin: 0 0 18px;
  scroll-margin-top: 18px;
}
.event:not(.reader-message):not(.work-card) {
  background: var(--panel);
  border: 1px solid var(--hair);
  box-shadow: var(--shadow);
}
.reader-message {
  display: flex;
  flex-direction: column;
}
.reader-message .event-header { display: none; }
.reader-message .body { padding: 0; }
.reader-message .body pre {
  font: 16px/1.62 Avenir Next, Aptos, ui-sans-serif, system-ui, sans-serif;
}
.message-images {
  display: grid;
  gap: 10px;
  margin: 0 0 12px;
}
.message-image {
  display: block;
  width: auto;
  max-width: min(100%, 760px);
  max-height: 560px;
  object-fit: contain;
  border: 1px solid var(--hair);
  border-radius: 14px;
  background: var(--panel-2);
  box-shadow: var(--shadow);
}
.message-image-link {
  display: inline-flex;
  width: max-content;
  max-width: 100%;
  color: var(--accent);
  border: 1px solid var(--hair);
  border-radius: 8px;
  padding: 7px 10px;
  overflow-wrap: anywhere;
}
.reader-message[data-speaker="user"] .message-images {
  justify-items: end;
}
.reader-message[data-speaker="user"] .message-image {
  max-width: 100%;
  box-shadow: none;
}
.markdown {
  font: 16px/1.62 Avenir Next, Aptos, ui-sans-serif, system-ui, sans-serif;
  overflow-wrap: anywhere;
}
.markdown > :first-child { margin-top: 0; }
.markdown > :last-child { margin-bottom: 0; }
.markdown p { margin: 0 0 14px; }
.markdown h1, .markdown h2, .markdown h3 {
  margin: 24px 0 10px;
  line-height: 1.25;
  font-size: 1.08em;
}
.markdown ul, .markdown ol {
  margin: 0 0 14px;
  padding-left: 1.35em;
}
.markdown li { margin: 3px 0; }
.markdown code {
  font: .92em/1.35 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: var(--panel-2);
  border-radius: 5px;
  padding: 1px 5px;
}
.markdown pre {
  margin: 0 0 14px;
  padding: 10px 12px;
  background: var(--panel-2);
  border: 1px solid var(--hair);
  border-radius: 6px;
  overflow: auto;
  white-space: pre-wrap;
}
.markdown pre code {
  background: transparent;
  border-radius: 0;
  padding: 0;
}
.markdown a { color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 2px; }
.reader-message[data-speaker="user"] {
  align-items: flex-end;
  margin: 6px 0 34px;
}
.reader-message[data-speaker="user"] .body {
  max-width: min(720px, 78%);
  background: var(--user-bubble);
  border-radius: 20px;
  padding: 12px 16px;
}
.reader-message[data-speaker="assistant"] {
  margin: 0 0 20px;
}
.reader-message[data-speaker="assistant"] .body {
  max-width: 900px;
}
.work-card {
  color: var(--muted);
  margin: -2px 0 18px;
  box-shadow: none;
}
.work-card details { border-top: 0; }
.work-card summary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  padding: 2px 0 8px;
  font-size: 14px;
}
.work-card summary:hover { color: var(--ink); }
.work-summary { font-weight: 600; color: inherit; }
.work-counts { color: var(--muted); font-size: 12px; }
.work-items {
  display: grid;
  gap: 6px;
  padding: 6px 0 12px 22px;
  border-left: 1px solid var(--hair);
}
.work-item {
  background: transparent;
}
.work-item-head {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 8px;
  align-items: baseline;
  padding: 4px 0;
  color: var(--muted);
}
.work-item .badge {
  border: 0;
  justify-content: start;
  padding: 0;
  min-height: 0;
}
.work-item .body { padding: 2px 0 10px; }
.work-item pre { color: var(--muted); }
.event.hidden { display: none; }
.event-header {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: baseline;
  padding: 10px 12px;
  border-bottom: 1px solid var(--hair);
}
.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  border: 1px solid var(--hair);
  color: var(--muted);
  padding: 3px 7px;
  font-size: 11px;
  text-transform: uppercase;
}
.event[data-kind="tool_call"] .badge, .event[data-kind="tool_result"] .badge { color: var(--tool); border-color: var(--muted); }
.event[data-kind="reasoning"] .badge { color: var(--warn); border-color: var(--muted); }
.event[data-status="error"] .badge { color: var(--accent-2); border-color: var(--accent-2); }
.event-title { min-width: 0; font-weight: 700; overflow-wrap: anywhere; }
.time { color: var(--muted); font-size: 12px; white-space: nowrap; }
.body { padding: 14px 16px; }
.body.system-preview pre {
  max-height: 48vh;
  overflow: auto;
}
details { border-top: 1px solid var(--hair); }
summary { cursor: pointer; color: var(--accent); padding: 10px 16px; }
pre {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: 12px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.body pre { font-size: 13px; }
.raw pre { padding: 0 16px 16px; color: var(--muted); }
.warnings {
  margin-bottom: 20px;
  padding: 16px;
  border: 1px solid var(--hair);
  border-radius: var(--radius-sm);
  background: var(--panel-2);
  overflow-wrap: anywhere;
}
.warnings ul { margin: 8px 0 0; padding-left: 20px; }
mark { background: var(--mark); color: var(--ink); padding: 0 1px; }
.empty {
  max-width: 760px;
  margin: 100px auto;
  border: 1px dashed var(--hair);
  border-radius: var(--radius);
  background: var(--panel);
  padding: 28px;
}
@media (max-width: 860px) {
  #app { grid-template-columns: 1fr; }
  aside { position: relative; height: auto; border-right: 0; border-bottom: 1px solid var(--hair); }
  .event-header { grid-template-columns: 1fr; gap: 6px; }
  .header { display: block; }
  .actions { justify-content: start; margin-top: 12px; }
}
</style>
</head>
<body>
<div id="app">
  <aside>
    <div class="brand"><h1>Session Viewer</h1><span id="format-label"></span></div>
    <div class="loader">
      <input id="file-input" type="file" accept=".json,.jsonl,.txt">
    </div>
    <div class="controls">
      <div class="search-row">
        <input id="search" type="search" placeholder="Search session">
        <button class="icon-btn" id="clear-search" title="Clear search" aria-label="Clear search">x</button>
      </div>
      <select class="theme-select" id="theme-select" aria-label="Theme">
        <option value="system">System theme</option>
        <option value="light">Light theme</option>
        <option value="dark">Dark theme</option>
      </select>
      <select class="theme-select" id="view-mode" aria-label="View mode">
        <option value="reader">Reading view</option>
        <option value="detail">Detail view</option>
      </select>
      <div class="filters" id="filters"></div>
      <button class="chip show-system" id="show-system">Show system events</button>
    </div>
    <div class="stats" id="stats"></div>
    <div class="meta" id="meta"></div>
    <div class="timeline" id="timeline"></div>
  </aside>
  <main>
    <div class="header">
      <div>
        <h2 id="title">Session</h2>
        <p id="subtitle"></p>
      </div>
      <div class="actions">
        <button class="chip" id="expand-all">Expand tools</button>
        <button class="chip" id="collapse-all">Collapse tools</button>
        <button class="chip" id="toggle-raw" aria-pressed="false">Raw JSON</button>
      </div>
    </div>
    <section class="warnings" id="warnings" aria-label="Session warnings" hidden></section>
    <div class="event-list" id="events"></div>
  </main>
</div>
<script id="viewer-payload" type="application/json">${scriptJsonEscape(payload)}</script>
<script>
(() => {
  const filters = ["message", "tool_call", "tool_result", "reasoning", "memory", "system", "event"];
  const themeStorageKey = "session-viewer-theme";
  const viewModeStorageKey = "session-viewer-view-mode";
  const maxSearchBlocks = 250;
  const defaultFilters = filters.filter((filter) => filter !== "system" && filter !== "event");
  const state = { doc: null, enabled: new Set(defaultFilters), homePath: "", query: "", showRaw: false, theme: localStorage.getItem(themeStorageKey) || "system", viewMode: localStorage.getItem(viewModeStorageKey) || "reader" };
  let searchTimer = 0;
  const $ = (id) => document.getElementById(id);
  const escapeHtml = (value) => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
  const shortenHomePaths = (value) => {
    const text = String(value ?? "");
    if (!state.homePath || state.homePath === "/") return text;
    return text.split(state.homePath).join("~");
  };
  const inferHomePath = (doc) => {
    const candidates = [
      doc?.sourcePath,
      ...Object.values(doc?.meta ?? {}).filter((value) => typeof value === "string"),
      ...(doc?.events ?? []).slice(0, 200).map((event) => event.text),
    ];
    for (const candidate of candidates) {
      const match = String(candidate ?? "").match(/(\\/Users\\/[^/]+|\\/home\\/[^/]+)(?=\\/|$)/u);
      if (match) return match[1];
    }
    return "";
  };
  const decodeBase64 = (value) => new TextDecoder().decode(Uint8Array.from(atob(value), (ch) => ch.charCodeAt(0)));
  const systemDark = () => window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  const applyTheme = () => {
    const resolved = state.theme === "system" ? (systemDark() ? "dark" : "light") : state.theme;
    document.documentElement.dataset.theme = resolved;
    document.documentElement.style.colorScheme = resolved;
    $("theme-select").value = state.theme;
  };
  const compact = (parts) => parts.map((p) => String(p ?? "").trim()).filter(Boolean).join("\\n\\n");
  const isObject = (v) => v && typeof v === "object" && !Array.isArray(v);
  const isImageSource = (value) => {
    const trimmed = String(value ?? "").trim();
    if (/^(data:image\\/|https?:\\/\\/|file:\\/\\/|\\/\\/|\\/(?!\\/)|\\.{1,2}\\/)/iu.test(trimmed)) return true;
    if (/^[a-z]:[\\\\/]/iu.test(trimmed)) return hasImageExtension(trimmed);
    if (/^[a-z][a-z0-9+.-]*:/iu.test(trimmed)) return false;
    return /^[^\\s<>]+\\.(?:avif|gif|jpe?g|png|webp)(?:[?#].*)?$/iu.test(trimmed);
  };
  const hasImageExtension = (value) => /\\.(?:avif|gif|jpe?g|png|webp)(?:[?#].*)?$/iu.test(String(value ?? "").trim());
  const imageSourceFromBlock = (block) => {
    const direct = typeof block.image_url === "string" ? block.image_url : block.image ?? block.openUrl ?? block.open_url ?? block.url ?? block.uri;
    if (typeof direct === "string" && isImageSource(direct)) return direct;
    const directMediaType = block.mimeType ?? block.mediaType ?? block.media_type;
    const directData = block.data ?? block.base64;
    if (typeof directMediaType === "string" && directMediaType.startsWith("image/") && typeof directData === "string") {
      return "data:" + directMediaType + ";base64," + directData;
    }
    const source = isObject(block.image_url)
      ? block.image_url
      : isObject(block.imageUrl)
      ? block.imageUrl
      : isObject(block.source)
      ? block.source
      : null;
    if (!source) return "";
    const sourceUrl = source.openUrl ?? source.open_url ?? source.url ?? source.uri;
    if (typeof sourceUrl === "string" && isImageSource(sourceUrl)) return sourceUrl;
    const mediaType = source.media_type ?? source.mediaType;
    if (typeof mediaType === "string" && mediaType.startsWith("image/") && typeof source.data === "string") {
      return "data:" + mediaType + ";base64," + source.data;
    }
    return "";
  };
  const imageBlocks = (content) => {
    if (!Array.isArray(content)) return [];
    return content.flatMap((block, index) => {
      if (!isObject(block)) return [];
      const type = String(block.type ?? "");
      if (type && !["input_image", "image", "image_url"].includes(type)) return [];
      const src = imageSourceFromBlock(block);
      return src ? [{ src, alt: String(block.alt ?? block.name ?? "Image " + (index + 1)), detail: block.detail }] : [];
    });
  };
  const arrayOrSingle = (value) => Array.isArray(value) ? value : value == null ? [] : [value];
  const indexedStrings = (message, keys) => {
    const lists = keys.map((key) => arrayOrSingle(message[key]));
    const length = Math.max(0, ...lists.map((list) => list.length));
    return Array.from({ length }, (_, index) => lists.map((list) => list[index]).find((item) => typeof item === "string" && item.trim()));
  };
  const mediaImages = (message) => {
    if (!isObject(message)) return [];
    const paths = indexedStrings(message, ["MediaPaths", "mediaPaths", "media_paths", "MediaPath", "mediaPath", "media_path"]);
    const urls = indexedStrings(message, ["MediaUrls", "mediaUrls", "media_urls", "MediaUrl", "mediaUrl", "media_url"]);
    const types = indexedStrings(message, ["MediaTypes", "mediaTypes", "media_types", "MediaType", "mediaType", "media_type"]);
    const length = Math.max(paths.length, urls.length, types.length);
    const refCount = Array.from({ length }, (_, index) => paths[index] ?? urls[index]).filter(Boolean).length;
    const typeCount = types.filter(Boolean).length;
    const typesAreAligned = typeCount === refCount;
    const seen = new Set();
    const images = [];
    for (let index = 0; index < length; index += 1) {
      const src = paths[index] ?? urls[index];
      if (!src || seen.has(src)) continue;
      const detail = typesAreAligned ? types[index] : undefined;
      const imageLike = isImageSource(src) && (detail?.startsWith("image/") || hasImageExtension(src));
      if (imageLike) {
        images.push({ src, alt: "Image " + (index + 1), detail });
        seen.add(src);
      }
    }
    return images;
  };
  const cleanImageMarkerText = (text, hasImages = false) => {
    if (!hasImages) return String(text ?? "").trim();
    let cleaned = String(text ?? "").replace(/<image\\s+name=\\[Image\\s+#\\d+\\]>\\s*/giu, "").trim();
    if (/^<\\/image>\\s*$/iu.test(cleaned)) return "";
    if (hasImages) cleaned = cleaned.replace(/^\\s*(?:\\[[^\\]\\n]*Image\\s*#?\\d+[^\\]\\n]*\\]\\s*)+/iu, "").trim();
    return cleaned;
  };
  const pretty = (v) => {
    if (typeof v === "string") {
      try { return JSON.stringify(JSON.parse(v), null, 2); } catch { return v.trim(); }
    }
    return v == null ? "" : JSON.stringify(v, null, 2);
  };
  const textBlocks = (content) => {
    if (typeof content === "string") return cleanImageMarkerText(content);
    if (!Array.isArray(content)) return "";
    const hasImages = imageBlocks(content).length > 0;
    return compact(content.map((block) => {
      if (typeof block === "string") return cleanImageMarkerText(block, hasImages);
      if (!isObject(block)) return "";
      return cleanImageMarkerText(block.text ?? block.content ?? block.output ?? "", hasImages);
    }));
  };
  const isTurnAbortedText = (text) => {
    const trimmed = String(text ?? "").trim();
    return /^<turn_aborted>[\\s\\S]*<\\/turn_aborted>$/u.test(trimmed)
      && trimmed.includes("The user interrupted the previous turn on purpose.")
      && trimmed.includes("Any running unified exec processes may still be running in the background.");
  };
  const turnAbortedEvent = (id, timestamp, raw) => ({ id, kind: "event", title: "Turn aborted", text: "Turn aborted by user.", timestamp, raw });
  const expandMemoryCitations = (events) => {
    const pattern = /<oai-mem-citation>[\\s\\S]*?<\\/oai-mem-citation>/gu;
    const result = [];
    for (const event of events) {
      if (event.kind !== "message" || event.role !== "assistant" || !String(event.text ?? "").includes("<oai-mem-citation>")) {
        result.push(event);
        continue;
      }
      const matches = [...event.text.matchAll(pattern)];
      let footerStart = event.text.length;
      const citations = [];
      for (let index = matches.length - 1; index >= 0; index -= 1) {
        const match = matches[index];
        const matchEnd = match.index + match[0].length;
        if (event.text.slice(matchEnd, footerStart).trim()) break;
        citations.unshift(match[0].trim());
        footerStart = match.index;
      }
      if (!citations.length) {
        result.push(event);
        continue;
      }
      const text = event.text.slice(0, footerStart).replace(/\\n{3,}/gu, "\\n\\n").trim();
      if (text) result.push({ ...event, text });
      citations.forEach((citation, index) => result.push({ id: event.id + "-memory-" + (index + 1), kind: "memory", role: "memory", title: "Memory note", text: citation, timestamp: event.timestamp, raw: event.raw }));
    }
    return result;
  };
  const parseJsonl = (text) => text.split(/\\r?\\n/u).map((line, index) => ({ line: index + 1, raw: line.trim() })).filter((row) => row.raw).map((row) => {
    try { return { line: row.line, value: JSON.parse(row.raw) }; }
    catch (error) { return { line: row.line, value: { type: "parse_error", error: String(error), raw: row.raw } }; }
  });
  const ts = (record) => isObject(record.value) && typeof record.value.timestamp === "string" ? record.value.timestamp : undefined;
  const detect = (records) => {
    if (records.some((r) => isObject(r.value) && (r.value.type === "session_meta" || r.value.type === "response_item"))) return "codex";
    if (records.some((r) => isObject(r.value) && (r.value.type === "session" || (r.value.type === "message" && isObject(r.value.message))))) return "pi-openclaw";
    if (records.some((r) => isObject(r.value) && ["summary", "user", "assistant"].includes(String(r.value.type)) || (isObject(r.value?.message) && ["user", "assistant"].includes(String(r.value.message.role))))) return "claude";
    return "unknown";
  };
  const parseRaw = (text, name = "session") => {
    const records = parseJsonl(text);
    const format = detect(records);
    const events = [];
    const meta = {};
    for (const record of records) {
      const v = record.value;
      if (!isObject(v)) continue;
      if (format === "codex") {
        if (v.type === "session_meta" && isObject(v.payload)) Object.assign(meta, v.payload);
        if (v.type === "event_msg") {
          const p = isObject(v.payload) ? v.payload : {};
          if (p.type === "turn_aborted" && events.at(-1)?.title !== "Turn aborted") {
            const previous = events.at(-1);
            if (previous?.kind === "message" && previous.role === "user" && isTurnAbortedText(previous.text)) events.pop();
            events.push(turnAbortedEvent("e" + record.line, ts(record), p));
          }
          continue;
        }
        if (v.type !== "response_item") continue;
        const p = isObject(v.payload) ? v.payload : {};
        const type = p.type;
        if (type === "message") {
          const images = imageBlocks(p.content);
          const text = textBlocks(p.content);
          if (text || images.length) events.push({ id: "e" + record.line, kind: p.role === "developer" ? "system" : "message", role: p.role, title: String(p.role ?? "message"), text, images: images.length ? images : undefined, timestamp: ts(record), raw: p });
        } else if (type === "reasoning") {
          const text = compact([Array.isArray(p.summary) ? compact(p.summary.map((s) => s?.text)) : "", textBlocks(p.content)]);
          if (text) events.push({ id: "e" + record.line, kind: "reasoning", title: "reasoning", text, timestamp: ts(record), raw: p });
        } else if (type === "function_call" || type === "custom_tool_call" || type === "web_search_call") {
          events.push({ id: "e" + record.line, kind: "tool_call", title: "tool call: " + (p.name ?? type), text: pretty(p.arguments ?? p.input ?? p), timestamp: ts(record), callId: p.call_id, toolName: p.name, status: "running", raw: p });
        } else if (type === "function_call_output" || type === "custom_tool_call_output") {
          events.push({ id: "e" + record.line, kind: "tool_result", title: "tool result" + (p.call_id ? ": " + p.call_id : ""), text: pretty(p.output), timestamp: ts(record), callId: p.call_id, status: "unknown", raw: p });
        }
        continue;
      }
      if (format === "pi-openclaw") {
        if (v.type === "session") Object.assign(meta, v);
        if (v.type !== "message" || !isObject(v.message)) continue;
        const m = v.message;
        if (m.role === "toolResult") {
          const images = [...imageBlocks(m.content), ...mediaImages(m)];
          events.push({ id: String(v.id ?? "e" + record.line), kind: "tool_result", title: "tool result" + (m.toolCallId ? ": " + m.toolCallId : ""), text: textBlocks(m.content) || (images.length ? "" : pretty(m)), images: images.length ? images : undefined, timestamp: v.timestamp, callId: m.toolCallId, toolName: m.toolName, status: m.isError ? "error" : "ok", raw: v });
        } else {
          const messageContent = Array.isArray(m.content) ? m.content.filter((block) => !(isObject(block) && block.type === "thinking")) : m.content;
          const images = [...imageBlocks(m.content), ...mediaImages(m)];
          const text = textBlocks(messageContent);
          if (text || images.length) events.push({ id: String(v.id ?? "e" + record.line), kind: "message", role: m.role, title: String(m.role ?? "message"), text, images: images.length ? images : undefined, timestamp: v.timestamp, raw: v });
          for (const block of Array.isArray(m.content) ? m.content : []) {
            if (isObject(block) && block.type === "thinking" && (block.thinking ?? block.text)) events.push({ id: String(v.id ?? "e" + record.line) + "-thinking-" + events.length, kind: "reasoning", title: "thinking", text: block.thinking ?? block.text, timestamp: v.timestamp, raw: block });
            if (isObject(block) && block.type === "toolCall") events.push({ id: String(v.id ?? "e" + record.line) + "-tool-" + events.length, kind: "tool_call", title: "tool call: " + (block.name ?? "tool"), text: pretty(block.arguments ?? block.input), timestamp: v.timestamp, callId: block.id, toolName: block.name, status: "running", raw: block });
          }
        }
        continue;
      }
      if (format === "claude") {
        const m = isObject(v.message) ? v.message : v;
        const role = m.role ?? v.type ?? "message";
        const content = m.content;
        const images = imageBlocks(content);
        const messageContent = Array.isArray(content) ? content.filter((block) => !(isObject(block) && block.type === "thinking")) : content;
        const text = textBlocks(messageContent);
        if (text || images.length) events.push({ id: "e" + record.line, kind: role === "system" ? "system" : "message", role, title: String(role), text, images: images.length ? images : undefined, timestamp: v.timestamp, raw: v });
        for (const block of Array.isArray(content) ? content : []) {
          if (!isObject(block)) continue;
          if (block.type === "thinking" && (block.thinking ?? block.text ?? block.content)) events.push({ id: "e" + record.line + "-thinking", kind: "reasoning", title: "thinking", text: block.thinking ?? block.text ?? block.content, timestamp: v.timestamp, raw: block });
          if (block.type === "tool_use") events.push({ id: "e" + record.line + "-tool-" + events.length, kind: "tool_call", title: "tool call: " + (block.name ?? "tool"), text: pretty(block.input), timestamp: v.timestamp, callId: block.id, toolName: block.name, status: "running", raw: block });
          if (block.type === "tool_result") {
            const images = imageBlocks(block.content);
            events.push({ id: "e" + record.line + "-result-" + events.length, kind: "tool_result", title: "tool result" + (block.tool_use_id ? ": " + block.tool_use_id : ""), text: textBlocks(block.content) || (images.length ? "" : pretty(block.content)), images: images.length ? images : undefined, timestamp: v.timestamp, callId: block.tool_use_id, status: block.is_error ? "error" : "ok", raw: block });
          }
        }
      }
    }
    return { format, title: meta.id || meta.summary || name, meta, events: expandMemoryCitations(events), warnings: [] };
  };
  const indexEvent = (event) => {
    const imageText = Array.isArray(event.images) ? event.images.map((image) => [image.alt, image.detail, image.src].join(" ")).join("\\n") : "";
    event.searchText = [event.title, event.role, event.text, shortenHomePaths(event.text), imageText, event.toolName, event.callId].join("\\n").toLowerCase();
  };
  const indexDoc = (doc) => (doc?.events ?? []).forEach(indexEvent);
  const matches = (event) => {
    if (!state.query) return true;
    return String(event.searchText ?? "").includes(state.query);
  };
  const isVisible = (event) => state.query ? matches(event) : state.enabled.has(event.kind);
  const isContextPacket = (event) => {
    if (event.kind !== "message") return false;
    const text = String(event.text ?? "");
    return /^# AGENTS\\.md instructions/u.test(text)
      || text.includes("<environment_context>")
      || text.includes("<permissions instructions>")
      || text.includes("<skills_instructions>")
      || text.includes("========= MEMORY_SUMMARY BEGINS");
  };
  const isReaderMessage = (event) => event.kind === "message" && !["system", "developer"].includes(String(event.role ?? "")) && !isContextPacket(event);
  const itemMatches = (item) => item.type === "message" ? matches(item.event) : item.events.some(matches);
  const plural = (count, singular, pluralForm = singular + "s") => count + " " + (count === 1 ? singular : pluralForm);
  const countParts = (events) => {
    const labels = {
      tool_call: ["tool call", "tool calls"],
      tool_result: ["tool result", "tool results"],
      reasoning: ["reasoning note", "reasoning"],
      memory: ["memory note", "memory notes"],
      system: ["system item", "system items"],
      event: ["event", "events"],
      message: ["message", "messages"],
    };
    const counts = {};
    for (const event of events) counts[event.kind] = (counts[event.kind] ?? 0) + 1;
    return Object.entries(counts).map(([kind, count]) => {
      const label = labels[kind] ?? [kind, kind];
      return plural(count, label[0], label[1]);
    });
  };
  const activityLabel = (events, title) => {
    if (title === "Session context") return "Session context";
    if (title === "Memory note") return "Memory note";
    if (events.length === 1 && events[0].title === "Turn aborted") return "Turn aborted by user.";
    const parts = countParts(events);
    return "Activity" + (parts.length ? ": " + parts.join(", ") : "");
  };
  const buildReaderItems = (events) => {
    const items = [];
    let pending = [];
    const flush = () => {
      if (!pending.length) return;
      const first = pending[0];
      const contextOnly = pending.every((event) => isContextPacket(event) || event.kind === "system");
      const memoryOnly = pending.every((event) => event.kind === "memory");
      const title = contextOnly ? "Session context" : memoryOnly ? "Memory note" : "Activity";
      items.push({ type: "work", id: "work-" + first.id, events: pending, title: activityLabel(pending, title), summary: countParts(pending).join(", ") });
      pending = [];
    };
    for (const event of events) {
      if (!isVisible(event)) continue;
      if (event.kind === "memory") {
        flush();
        pending.push(event);
        flush();
        continue;
      }
      if (isReaderMessage(event)) {
        flush();
        items.push({ type: "message", id: event.id, event, title: event.title });
      } else {
        pending.push(event);
      }
    }
    flush();
    return state.query ? items.filter(itemMatches) : items;
  };
  const highlight = (text) => {
    const escaped = escapeHtml(shortenHomePaths(text));
    if (!state.query || state.query.length < 3) return escaped;
    const q = state.query
      .replace(/[.*+?^$()|[\\]\\\\]/g, "\\\\$&")
      .replaceAll("{", "\\\\{")
      .replaceAll("}", "\\\\}");
    return escaped.replace(new RegExp(q, "gi"), (m) => "<mark>" + m + "</mark>");
  };
  const inlineMarkdown = (text) => {
    const tick = String.fromCharCode(96);
    const placeholders = [];
    const stash = (value) => {
      const key = "\\u0000" + placeholders.length + "\\u0000";
      placeholders.push(value);
      return key;
    };
    const anchor = (url, label) => '<a href="' + escapeHtml(url) + '" target="_blank" rel="noreferrer">' + escapeHtml(shortenHomePaths(label)) + '</a>';
    let working = String(text ?? "");
    working = working.replace(/\\[([^\\]]+)\\]\\((https?:\\/\\/[^\\s)]+|file:\\/\\/[^\\s)]+)\\)/gu, (_, label, url) => stash(anchor(url, label)));
    working = working.replace(new RegExp(tick + "([^" + tick + "]+)" + tick, "gu"), (_, code) => stash("<code>" + escapeHtml(shortenHomePaths(code)) + "</code>"));
    working = working.replace(/https?:\\/\\/[^\\s<]+[^\\s<.,;:!?)\\]]/gu, (url) => stash(anchor(url, url)));
    let html = escapeHtml(shortenHomePaths(working));
    html = html.replace(/\\*\\*([^*]+)\\*\\*/gu, "<strong>$1</strong>");
    html = html.replace(/__([^_]+)__/gu, "<strong>$1</strong>");
    html = html.replace(/(^|\\s)\\*([^*\\n]+)\\*(?=\\s|$)/gu, "$1<em>$2</em>");
    html = html.replace(/(^|\\s)_([^_\\n]+)_(?=\\s|$)/gu, "$1<em>$2</em>");
    html = html.replace(/\\u0000(\\d+)\\u0000/gu, (_, index) => placeholders[Number(index)] ?? "");
    if (state.query && state.query.length >= 3) {
      const q = state.query
        .replace(/[.*+?^$()|[\\]\\\\]/g, "\\\\$&")
        .replaceAll("{", "\\\\{")
        .replaceAll("}", "\\\\}");
      html = html.replace(/(<[^>]+>|[^<]+)/gu, (segment) => {
        if (segment.startsWith("<")) return segment;
        return segment.replace(new RegExp(q, "gi"), (m) => "<mark>" + m + "</mark>");
      });
    }
    return html;
  };
  const markdownToHtml = (text) => {
    const fenceMarker = String.fromCharCode(96).repeat(3);
    const lines = String(text ?? "").replaceAll("\\r\\n", "\\n").split("\\n");
    const out = [];
    let paragraph = [];
    let list = null;
    let fence = null;
    const flushParagraph = () => {
      if (!paragraph.length) return;
      out.push("<p>" + inlineMarkdown(paragraph.join(" ")) + "</p>");
      paragraph = [];
    };
    const flushList = () => {
      if (!list) return;
      out.push("<" + list.type + ">" + list.items.map((item) => "<li>" + inlineMarkdown(item) + "</li>").join("") + "</" + list.type + ">");
      list = null;
    };
    const closeBlocks = () => { flushParagraph(); flushList(); };
    for (const line of lines) {
      const fenceMatch = line.startsWith(fenceMarker);
      if (fence) {
        if (fenceMatch) {
          out.push("<pre><code>" + escapeHtml(shortenHomePaths(fence.lines.join("\\n"))) + "</code></pre>");
          fence = null;
        } else {
          fence.lines.push(line);
        }
        continue;
      }
      if (fenceMatch) {
        closeBlocks();
        fence = { lines: [] };
        continue;
      }
      if (!line.trim()) {
        closeBlocks();
        continue;
      }
      const heading = /^(#{1,3})\\s+(.+)$/u.exec(line);
      if (heading) {
        closeBlocks();
        out.push("<h" + heading[1].length + ">" + inlineMarkdown(heading[2]) + "</h" + heading[1].length + ">");
        continue;
      }
      const unordered = /^\\s*[-*]\\s+(.+)$/u.exec(line);
      const ordered = /^\\s*\\d+[.)]\\s+(.+)$/u.exec(line);
      if (unordered || ordered) {
        flushParagraph();
        const type = unordered ? "ul" : "ol";
        if (!list || list.type !== type) flushList();
        if (!list) list = { type, items: [] };
        list.items.push((unordered ?? ordered)[1]);
        continue;
      }
      flushList();
      paragraph.push(line.trim());
    }
    closeBlocks();
    if (fence) out.push("<pre><code>" + escapeHtml(shortenHomePaths(fence.lines.join("\\n"))) + "</code></pre>");
    return out.join("");
  };
  const renderImages = (event) => {
    const images = Array.isArray(event.images) ? event.images.filter((image) => image?.src && isImageSource(image.src)) : [];
    if (!images.length) return "";
    return '<div class="message-images">' + images.map((image) => {
      if (String(image.src).startsWith("data:image/")) {
        return '<img class="message-image" loading="lazy" src="' + escapeHtml(image.src) + '" alt="' + escapeHtml(image.alt ?? "Image") + '">';
      }
      return '<a class="message-image-link" href="' + escapeHtml(image.src) + '" target="_blank" rel="noreferrer">Image attachment</a>';
    }).join("") + '</div>';
  };
  const rawBlock = (event) => state.showRaw ? '<details class="raw" open><summary>raw</summary><pre>' + escapeHtml(JSON.stringify(event.raw ?? {}, null, 2)) + '</pre></details>' : "";
  const renderEvent = (event, options = {}) => {
    const bodyClass = event.kind === "system" ? "body system-preview" : "body";
    const imageHtml = renderImages(event);
    const bodyContent = options.reader && event.kind === "message"
      ? '<div class="body">' + imageHtml + (event.text ? '<div class="markdown">' + markdownToHtml(event.text) + '</div>' : '') + '</div>'
      : '<div class="' + bodyClass + '">' + imageHtml + (event.text ? '<pre>' + highlight(event.text) + '</pre>' : '') + '</div>';
    const toolDetails = (event.kind === "tool_call" || event.kind === "tool_result") && !options.inline
      ? '<details><summary>payload</summary><div class="body">' + imageHtml + (event.text ? '<pre>' + highlight(event.text) + '</pre>' : '') + '</div></details>'
      : bodyContent;
    const messageClass = options.reader ? " reader-message" : "";
    const speaker = String(event.role ?? event.kind).split(" ")[0];
    return '<article class="event' + messageClass + '" id="' + escapeHtml(event.id) + '" data-kind="' + escapeHtml(event.kind) + '" data-role="' + escapeHtml(event.role ?? event.kind) + '" data-speaker="' + escapeHtml(speaker) + '" data-status="' + escapeHtml(event.status ?? "") + '"><div class="event-header"><span class="badge">' + escapeHtml(event.role ?? event.kind) + '</span><div class="event-title">' + escapeHtml(event.title) + '</div><span class="time">' + escapeHtml(event.timestamp ?? "") + '</span></div>' + toolDetails + rawBlock(event) + '</article>';
  };
  const renderWorkItem = (event) => {
    const imageHtml = renderImages(event);
    return '<div class="work-item" data-kind="' + escapeHtml(event.kind) + '"><div class="work-item-head"><span class="badge">' + escapeHtml(event.kind) + '</span><div class="event-title">' + escapeHtml(event.title) + '</div></div><div class="body">' + imageHtml + (event.text ? '<pre>' + highlight(event.text) + '</pre>' : '') + '</div>' + rawBlock(event) + '</div>';
  };
  const renderReaderItem = (item) => {
    if (item.type === "message") return renderEvent(item.event, { reader: true });
    const open = state.query && itemMatches(item) ? " open" : "";
    return '<article class="event work-card" id="' + escapeHtml(item.id) + '" data-kind="work"><details' + open + '><summary><span class="work-summary">' + escapeHtml(item.title) + '</span></summary><div class="work-items">' + item.events.map(renderWorkItem).join("") + '</div></details></article>';
  };
  const render = () => {
    const doc = state.doc;
    $("view-mode").value = state.viewMode;
    $("format-label").textContent = doc ? doc.format : "";
    $("title").textContent = doc ? shortenHomePaths(doc.title ?? "Session") : "Drop in a session";
    $("subtitle").textContent = doc?.sourcePath ? shortenHomePaths(doc.sourcePath) : "Load a Codex, Claude, or OpenClaw/Pi JSONL file.";
    const warnings = doc?.warnings ?? [];
    $("warnings").hidden = warnings.length === 0;
    $("warnings").innerHTML = warnings.length
      ? '<strong>Session warnings</strong><ul>' + warnings.map((warning) => '<li>' + escapeHtml(shortenHomePaths(warning)) + '</li>').join("") + '</ul>'
      : "";
    const visible = doc ? doc.events.filter(isVisible) : [];
    const readerItems = doc && state.viewMode === "reader" ? buildReaderItems(doc.events) : [];
    const renderedReaderItems = state.query ? readerItems.slice(0, maxSearchBlocks) : readerItems;
    const renderedVisible = state.query ? visible.slice(0, maxSearchBlocks) : visible;
    const searchOverflow = state.query && (
      (state.viewMode === "reader" && readerItems.length > renderedReaderItems.length) ||
      (state.viewMode !== "reader" && visible.length > renderedVisible.length)
    );
    const navItems = state.viewMode === "reader" ? readerItems.map((item) => ({
      id: item.id,
      kind: item.type === "message" ? String(item.event.role ?? "message") : "work",
      title: item.type === "message" ? item.event.title : item.summary,
    })) : visible.map((event) => ({ id: event.id, kind: event.kind, title: event.title }));
    const hiddenSystem = doc ? doc.events.filter((event) => event.kind === "system").length : 0;
    $("stats").innerHTML = doc ? [
      ["events", doc.events.length],
      ["visible", visible.length],
      ["reading blocks", state.viewMode === "reader" ? readerItems.length : "detail"],
      ["system hidden", state.enabled.has("system") ? 0 : hiddenSystem],
      ["warnings", doc.warnings?.length ?? 0],
    ].map(([k,v]) => "<div><b>" + k + ":</b> " + escapeHtml(v) + "</div>").join("") : "";
    const metaEntries = Object.entries(doc?.meta ?? {}).filter(([key]) => ["id", "cwd", "timestamp", "cli_version", "model_provider"].includes(key));
    $("meta").innerHTML = doc ? metaEntries.map(([k,v]) => "<div><b>" + escapeHtml(k) + ":</b> " + escapeHtml(shortenHomePaths(v)) + "</div>").join("") : "";
    $("timeline").innerHTML = navItems.slice(0, 600).map((item) => '<button class="nav-item" data-jump="' + escapeHtml(item.id) + '"><span class="nav-kind">' + escapeHtml(item.kind) + '</span><span class="nav-title">' + escapeHtml(item.title) + '</span></button>').join("");
    const overflow = searchOverflow ? '<div class="empty"><h2>Showing first ' + maxSearchBlocks + ' matches</h2><p>Narrow the search to render fewer results.</p></div>' : "";
    const content = state.viewMode === "reader" ? renderedReaderItems.map(renderReaderItem).join("") : renderedVisible.map((event) => renderEvent(event)).join("");
    $("events").innerHTML = doc && (content || overflow) ? content + overflow : '<div class="empty"><h2>No session loaded</h2><p>Choose a JSONL file in the sidebar.</p></div>';
  };
  const scheduleRender = () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(render, 80);
  };
  const loadDoc = (doc) => { indexDoc(doc); state.doc = doc; state.homePath = inferHomePath(doc); state.enabled = new Set(defaultFilters); renderFilters(); render(); };
  const renderFilters = () => {
    $("filters").innerHTML = filters.filter((filter) => filter !== "system").map((filter) => '<button class="chip" data-filter="' + filter + '" aria-pressed="' + state.enabled.has(filter) + '">' + filter.replace("_", " ") + '</button>').join("");
    $("show-system").textContent = state.enabled.has("system") ? "Hide system events" : "Show system events";
  };
  $("filters").addEventListener("click", (event) => {
    const button = event.target.closest("[data-filter]");
    if (!button) return;
    const filter = button.dataset.filter;
    if (state.enabled.has(filter)) state.enabled.delete(filter); else state.enabled.add(filter);
    renderFilters(); render();
  });
  $("show-system").addEventListener("click", () => {
    if (state.enabled.has("system")) state.enabled.delete("system"); else state.enabled.add("system");
    $("show-system").textContent = state.enabled.has("system") ? "Hide system events" : "Show system events";
    renderFilters();
    render();
  });
  $("timeline").addEventListener("click", (event) => {
    const button = event.target.closest("[data-jump]");
    if (button) document.getElementById(button.dataset.jump)?.scrollIntoView({ block: "start", behavior: "smooth" });
  });
  $("search").addEventListener("input", (event) => {
    const query = event.target.value.trim().toLowerCase();
    const nextQuery = query.length >= 3 ? query : "";
    if (nextQuery === state.query) return;
    state.query = nextQuery;
    scheduleRender();
  });
  $("clear-search").addEventListener("click", () => { state.query = ""; $("search").value = ""; render(); });
  $("theme-select").addEventListener("change", (event) => {
    state.theme = event.target.value;
    localStorage.setItem(themeStorageKey, state.theme);
    applyTheme();
  });
  $("view-mode").addEventListener("change", (event) => {
    state.viewMode = event.target.value;
    localStorage.setItem(viewModeStorageKey, state.viewMode);
    render();
  });
  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if (state.theme === "system") applyTheme();
    });
  }
  $("toggle-raw").addEventListener("click", () => { state.showRaw = !state.showRaw; $("toggle-raw").setAttribute("aria-pressed", String(state.showRaw)); render(); });
  $("expand-all").addEventListener("click", () => document.querySelectorAll("details").forEach((d) => { d.open = true; }));
  $("collapse-all").addEventListener("click", () => document.querySelectorAll("details").forEach((d) => { d.open = false; }));
  $("file-input").addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    loadDoc(parseRaw(text, file.name));
  });
  renderFilters();
  applyTheme();
  const embedded = JSON.parse($("viewer-payload").textContent || '{"kind":"blank"}');
  if (embedded.kind === "normalized") loadDoc(JSON.parse(decodeBase64(embedded.data)));
  else if (embedded.kind === "raw") {
    const doc = parseRaw(decodeBase64(embedded.data), "embedded session");
    doc.warnings.unshift(...(embedded.warnings ?? []));
    loadDoc(doc);
  }
  else render();
})();
</script>
</body>
</html>`;
}
