import { viewerStyles } from "./styles.ts";
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
${viewerStyles}</style>
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
