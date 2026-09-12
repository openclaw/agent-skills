import type { JsonlRecord, SessionEvent, SessionImage } from "./types.ts";

export function parseJsonl(text: string): { records: JsonlRecord[]; warnings: string[] } {
  const records: JsonlRecord[] = [];
  const warnings: string[] = [];
  const lines = text.split(/\r?\n/u);
  for (const [index, raw] of lines.entries()) {
    const line = raw.trim();
    if (!line) {
      continue;
    }
    try {
      records.push({ line: index + 1, value: JSON.parse(line) as unknown });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      warnings.push(`line ${index + 1}: invalid JSON: ${message}`);
    }
  }
  return { records, warnings };
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

export function numberValue(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

export function pretty(value: unknown): string {
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) {
      return "";
    }
    try {
      return JSON.stringify(JSON.parse(trimmed) as unknown, null, 2);
    } catch {
      return trimmed;
    }
  }
  if (value === undefined || value === null) {
    return "";
  }
  return JSON.stringify(value, null, 2);
}

export function compactText(parts: Array<string | undefined>): string {
  return parts
    .map((part) => part?.trim())
    .filter((part): part is string => Boolean(part))
    .join("\n\n");
}

export function isImageSource(value: string): boolean {
  const trimmed = value.trim();
  if (/^(data:image\/|https?:\/\/|file:\/\/|\/\/|\/(?!\/)|\.{1,2}\/)/iu.test(trimmed)) {
    return true;
  }
  if (/^[a-z]:[\\/]/iu.test(trimmed)) {
    return hasImageExtension(trimmed);
  }
  if (/^[a-z][a-z0-9+.-]*:/iu.test(trimmed)) {
    return false;
  }
  return /^[^\s<>]+\.(?:avif|gif|jpe?g|png|webp)(?:[?#].*)?$/iu.test(trimmed);
}

export function hasImageExtension(value: string): boolean {
  return /\.(?:avif|gif|jpe?g|png|webp)(?:[?#].*)?$/iu.test(value.trim());
}

function imageSourceFromBlock(block: Record<string, unknown>): string | undefined {
  const direct =
    stringValue(block.image_url) ??
    stringValue(block.image) ??
    stringValue(block.openUrl) ??
    stringValue(block.open_url) ??
    stringValue(block.url) ??
    stringValue(block.uri);
  if (direct && isImageSource(direct)) {
    return direct;
  }

  const directMediaType =
    stringValue(block.mimeType) ?? stringValue(block.mediaType) ?? stringValue(block.media_type);
  const directData = stringValue(block.data) ?? stringValue(block.base64);
  if (directMediaType?.startsWith("image/") && directData) {
    return `data:${directMediaType};base64,${directData}`;
  }

  const source =
    (isRecord(block.image_url) ? block.image_url : undefined) ??
    (isRecord(block.imageUrl) ? block.imageUrl : undefined) ??
    (isRecord(block.source) ? block.source : undefined);
  if (!source) {
    return undefined;
  }
  const sourceUrl =
    stringValue(source.openUrl) ??
    stringValue(source.open_url) ??
    stringValue(source.url) ??
    stringValue(source.uri);
  if (sourceUrl && isImageSource(sourceUrl)) {
    return sourceUrl;
  }

  const mediaType = stringValue(source.media_type) ?? stringValue(source.mediaType);
  const data = stringValue(source.data);
  if (mediaType?.startsWith("image/") && data) {
    return `data:${mediaType};base64,${data}`;
  }
  return undefined;
}

export function imageAttachmentsFromContent(content: unknown): SessionImage[] {
  if (!Array.isArray(content)) {
    return [];
  }
  const images: SessionImage[] = [];
  for (const [index, block] of content.entries()) {
    if (!isRecord(block)) {
      continue;
    }
    const type = stringValue(block.type);
    if (type && !["input_image", "image", "image_url"].includes(type)) {
      continue;
    }
    const src = imageSourceFromBlock(block);
    if (!src) {
      continue;
    }
    images.push({
      src,
      alt: stringValue(block.alt) ?? stringValue(block.name) ?? `Image ${index + 1}`,
      detail: stringValue(block.detail),
    });
  }
  return images;
}

export function cleanImageMarkerText(text: string, hasImages = false): string {
  if (!hasImages) {
    return text.trim();
  }
  const cleaned = text.replace(/<image\s+name=\[Image\s+#\d+\]>\s*/giu, "").trim();
  if (/^<\/image>\s*$/iu.test(cleaned)) {
    return "";
  }
  return cleaned.replace(/^\s*(?:\[[^\]\n]*Image\s*#?\d+[^\]\n]*\]\s*)+/iu, "").trim();
}

export function textFromContentBlocks(content: unknown): string {
  if (typeof content === "string") {
    return cleanImageMarkerText(content);
  }
  if (!Array.isArray(content)) {
    return "";
  }
  const parts: string[] = [];
  const hasImages = imageAttachmentsFromContent(content).length > 0;
  for (const block of content) {
    if (typeof block === "string") {
      const text = cleanImageMarkerText(block, hasImages);
      if (text) {
        parts.push(text);
      }
      continue;
    }
    if (!isRecord(block)) {
      continue;
    }
    const type = stringValue(block.type);
    const text =
      stringValue(block.text) ??
      stringValue(block.content) ??
      stringValue(block.output) ??
      stringValue(block.input);
    if (
      text &&
      (!type ||
        [
          "input_text",
          "output_text",
          "text",
          "thinking",
          "tool_result",
          "function_call_output",
        ].includes(type))
    ) {
      const cleaned = cleanImageMarkerText(text, hasImages);
      if (cleaned) {
        parts.push(cleaned);
      }
    }
  }
  return cleanImageMarkerText(compactText(parts), hasImages);
}

export function firstText(value: unknown, keys: string[]): string | undefined {
  if (!isRecord(value)) {
    return undefined;
  }
  for (const key of keys) {
    const result = stringValue(value[key]);
    if (result) {
      return result;
    }
  }
  return undefined;
}

export function expandMemoryCitationEvents(events: SessionEvent[]): SessionEvent[] {
  const result: SessionEvent[] = [];
  const citationPattern = /<oai-mem-citation>[\s\S]*?<\/oai-mem-citation>/gu;

  for (const event of events) {
    if (
      event.kind !== "message" ||
      event.role !== "assistant" ||
      !event.text.includes("<oai-mem-citation>")
    ) {
      result.push(event);
      continue;
    }

    const matches = [...event.text.matchAll(citationPattern)];
    let footerStart = event.text.length;
    const citations: string[] = [];
    for (let index = matches.length - 1; index >= 0; index -= 1) {
      const match = matches[index];
      const matchEnd = match.index + match[0].length;
      if (event.text.slice(matchEnd, footerStart).trim()) {
        break;
      }
      citations.unshift(match[0].trim());
      footerStart = match.index;
    }
    if (citations.length === 0) {
      result.push(event);
      continue;
    }

    const text = event.text
      .slice(0, footerStart)
      .replace(/\n{3,}/gu, "\n\n")
      .trim();
    if (text) {
      result.push({ ...event, text });
    }
    for (const [index, citation] of citations.entries()) {
      result.push({
        id: `${event.id}-memory-${index + 1}`,
        kind: "memory",
        role: "memory",
        title: "Memory note",
        text: citation,
        timestamp: event.timestamp,
        raw: event.raw,
      });
    }
  }

  return result;
}
