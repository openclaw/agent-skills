import {
  expandMemoryCitationEvents,
  hasImageExtension,
  imageAttachmentsFromContent,
  isImageSource,
  isRecord,
  numberValue,
  pretty,
  stringValue,
  textFromContentBlocks,
} from "../core/jsonl.ts";
import type {
  JsonlRecord,
  SessionDocument,
  SessionEvent,
  SessionImage,
  SessionImporter,
} from "../core/types.ts";

function isoFromEpochMillis(value: unknown): string | undefined {
  const millis = numberValue(value);
  if (millis === undefined) {
    return undefined;
  }
  const date = new Date(millis);
  return Number.isNaN(date.getTime()) ? undefined : date.toISOString();
}

function timestampOf(
  entry: Record<string, unknown>,
  message?: Record<string, unknown>,
): string | undefined {
  const raw =
    stringValue(entry.timestamp) ??
    stringValue(entry.createdAt) ??
    stringValue(entry.updatedAt) ??
    isoFromEpochMillis(message?.timestamp);
  return raw;
}

function arrayOrSingle(value: unknown): unknown[] {
  return Array.isArray(value) ? value : value === undefined || value === null ? [] : [value];
}

function indexedStrings(
  message: Record<string, unknown>,
  keys: string[],
): Array<string | undefined> {
  const lists = keys.map((key) => arrayOrSingle(message[key]));
  const length = Math.max(0, ...lists.map((list) => list.length));
  const result: Array<string | undefined> = [];
  for (let index = 0; index < length; index += 1) {
    const value = lists
      .map((list) => list[index])
      .find((item): item is string => typeof item === "string" && item.trim().length > 0);
    result.push(value);
  }
  return result;
}

function imagesFromMessageMedia(message: Record<string, unknown>): SessionImage[] {
  const paths = indexedStrings(message, [
    "MediaPaths",
    "mediaPaths",
    "media_paths",
    "MediaPath",
    "mediaPath",
    "media_path",
  ]);
  const urls = indexedStrings(message, [
    "MediaUrls",
    "mediaUrls",
    "media_urls",
    "MediaUrl",
    "mediaUrl",
    "media_url",
  ]);
  const types = indexedStrings(message, [
    "MediaTypes",
    "mediaTypes",
    "media_types",
    "MediaType",
    "mediaType",
    "media_type",
  ]);
  const length = Math.max(paths.length, urls.length, types.length);
  if (length === 0) {
    return [];
  }
  const refCount = Array.from({ length }, (_, index) => paths[index] ?? urls[index]).filter(
    Boolean,
  ).length;
  const typeCount = types.filter(Boolean).length;
  const typesAreAligned = typeCount === refCount;
  const seen = new Set<string>();
  const images: SessionImage[] = [];
  for (let index = 0; index < length; index += 1) {
    const src = paths[index] ?? urls[index];
    if (!src || seen.has(src)) {
      continue;
    }
    const detail = typesAreAligned ? types[index] : undefined;
    const imageLike =
      isImageSource(src) && (detail?.startsWith("image/") === true || hasImageExtension(src));
    if (imageLike) {
      images.push({ src, alt: `Image ${index + 1}`, detail });
      seen.add(src);
    }
  }
  return images;
}

function eventsFromMessage(record: JsonlRecord, entry: Record<string, unknown>): SessionEvent[] {
  const message = isRecord(entry.message) ? entry.message : undefined;
  if (!message) {
    return [];
  }
  const role = stringValue(message.role) ?? "unknown";
  const timestamp = timestampOf(entry, message);
  const baseId = stringValue(entry.id) ?? `pi-${record.line}`;

  if (role === "toolResult") {
    const images = [
      ...imageAttachmentsFromContent(message.content),
      ...imagesFromMessageMedia(message),
    ];
    const text = textFromContentBlocks(message.content) || (images.length ? "" : pretty(message));
    return [
      {
        id: baseId,
        kind: "tool_result",
        title: stringValue(message.toolCallId)
          ? `tool result: ${stringValue(message.toolCallId)}`
          : "tool result",
        text,
        images: images.length ? images : undefined,
        timestamp,
        callId: stringValue(message.toolCallId),
        toolName: stringValue(message.toolName),
        status: message.isError === true ? "error" : "ok",
        raw: entry,
      },
    ];
  }

  const events: SessionEvent[] = [];
  const content = message.content;
  const textParts: string[] = [];
  const images = [...imageAttachmentsFromContent(content), ...imagesFromMessageMedia(message)];
  if (typeof content === "string") {
    textParts.push(content);
  } else if (Array.isArray(content)) {
    let blockIndex = 0;
    for (const block of content) {
      if (!isRecord(block)) {
        continue;
      }
      const type = stringValue(block.type);
      if (type === "text") {
        const text = stringValue(block.text);
        if (text) {
          textParts.push(text);
        }
        continue;
      }
      if (type === "thinking") {
        const text = stringValue(block.thinking) ?? stringValue(block.text);
        if (!text) {
          continue;
        }
        events.push({
          id: `${baseId}-thinking-${blockIndex++}`,
          kind: "reasoning",
          title: "thinking",
          text,
          timestamp,
          raw: block,
        });
        continue;
      }
      if (type === "toolCall") {
        const name = stringValue(block.name) ?? "toolCall";
        events.push({
          id: `${baseId}-tool-${blockIndex++}`,
          kind: "tool_call",
          title: `tool call: ${name}`,
          text: pretty(block.arguments ?? block.input),
          timestamp,
          callId: stringValue(block.id),
          toolName: name,
          status: "running",
          raw: block,
        });
        continue;
      }
    }
  }

  const text = textParts
    .map((part) => part.trim())
    .filter(Boolean)
    .join("\n\n");
  if (text) {
    events.unshift({
      id: baseId,
      kind: role === "system" ? "system" : "message",
      role,
      title: role,
      text,
      images: images.length ? images : undefined,
      timestamp,
      raw: entry,
    });
  } else if (images.length > 0) {
    events.unshift({
      id: baseId,
      kind: role === "system" ? "system" : "message",
      role,
      title: role,
      text: "",
      images,
      timestamp,
      raw: entry,
    });
  }
  return events;
}

export const piOpenClawImporter: SessionImporter = {
  format: "pi-openclaw",
  detect(records) {
    return records.some((record) => {
      if (!isRecord(record.value)) {
        return false;
      }
      return (
        record.value.type === "session" ||
        (record.value.type === "message" && isRecord(record.value.message))
      );
    });
  },
  parse(records, sourcePath) {
    const meta: SessionDocument["meta"] = {};
    const warnings: string[] = [];
    const events: SessionEvent[] = [];

    for (const record of records) {
      if (!isRecord(record.value)) {
        continue;
      }
      const type = stringValue(record.value.type);
      if (type === "session") {
        for (const [key, value] of Object.entries(record.value)) {
          if (
            typeof value === "string" ||
            typeof value === "number" ||
            typeof value === "boolean"
          ) {
            meta[key] = value;
          }
        }
        continue;
      }
      if (type === "message") {
        events.push(...eventsFromMessage(record, record.value));
        continue;
      }
      if (type === "label") {
        continue;
      }
      events.push({
        id: stringValue(record.value.id) ?? `pi-${record.line}`,
        kind: "event",
        title: type ? `entry: ${type}` : "entry",
        text: pretty(record.value),
        timestamp: timestampOf(record.value),
        raw: record.value,
      });
    }

    if (events.length === 0) {
      warnings.push("no Pi/OpenClaw message events found");
    }

    const title =
      stringValue(meta.id) ??
      (sourcePath ? sourcePath.split(/[\\/]/u).pop() : undefined) ??
      "OpenClaw session";
    return {
      format: "pi-openclaw",
      title,
      sourcePath,
      meta,
      events: expandMemoryCitationEvents(events),
      warnings,
    };
  },
};
