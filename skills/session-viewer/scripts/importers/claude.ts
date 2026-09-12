import {
  compactText,
  expandMemoryCitationEvents,
  firstText,
  imageAttachmentsFromContent,
  isRecord,
  pretty,
  stringValue,
  textFromContentBlocks,
} from "../core/jsonl.ts";
import type { JsonlRecord, SessionDocument, SessionEvent, SessionImporter } from "../core/types.ts";

function timestampOf(value: Record<string, unknown>): string | undefined {
  return (
    stringValue(value.timestamp) ?? stringValue(value.created_at) ?? stringValue(value.updated_at)
  );
}

function parseContentBlocks(
  recordId: string,
  content: unknown,
  timestamp: string | undefined,
  fallbackRole: string,
): SessionEvent[] {
  if (typeof content === "string") {
    return content.trim()
      ? [
          {
            id: recordId,
            kind: "message",
            role: fallbackRole,
            title: fallbackRole,
            text: content.trim(),
            timestamp,
          },
        ]
      : [];
  }
  if (!Array.isArray(content)) {
    return [];
  }

  const events: SessionEvent[] = [];
  const textParts: string[] = [];
  const images = imageAttachmentsFromContent(content);
  let textIndex = 0;

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
      const text = firstText(block, ["thinking", "text", "content"]);
      if (!text) {
        continue;
      }
      events.push({
        id: `${recordId}-thinking-${textIndex++}`,
        kind: "reasoning",
        title: "thinking",
        text,
        timestamp,
        raw: block,
      });
      continue;
    }
    if (type === "tool_use") {
      const name = stringValue(block.name) ?? "tool_use";
      events.push({
        id: `${recordId}-tool-${textIndex++}`,
        kind: "tool_call",
        title: `tool call: ${name}`,
        text: pretty(block.input),
        timestamp,
        callId: stringValue(block.id),
        toolName: name,
        status: "running",
        raw: block,
      });
      continue;
    }
    if (type === "tool_result") {
      const images = imageAttachmentsFromContent(block.content);
      const text =
        textFromContentBlocks(block.content) ||
        (images.length ? "" : pretty(block.content ?? block));
      events.push({
        id: `${recordId}-result-${textIndex++}`,
        kind: "tool_result",
        title: stringValue(block.tool_use_id)
          ? `tool result: ${stringValue(block.tool_use_id)}`
          : "tool result",
        text,
        images: images.length ? images : undefined,
        timestamp,
        callId: stringValue(block.tool_use_id),
        status: block.is_error === true ? "error" : "ok",
        raw: block,
      });
      continue;
    }
    const text = textFromContentBlocks([block]);
    if (text) {
      textParts.push(text);
    }
  }

  const mergedText = compactText(textParts);
  if (mergedText || images.length > 0) {
    events.unshift({
      id: `${recordId}-text`,
      kind: "message",
      role: fallbackRole,
      title: fallbackRole,
      text: mergedText,
      images: images.length ? images : undefined,
      timestamp,
    });
  }
  return events;
}

export const claudeImporter: SessionImporter = {
  format: "claude",
  detect(records) {
    return records.some((record) => {
      if (!isRecord(record.value)) {
        return false;
      }
      const type = record.value.type;
      const message = isRecord(record.value.message) ? record.value.message : undefined;
      return (
        type === "summary" ||
        type === "user" ||
        type === "assistant" ||
        message?.role === "user" ||
        message?.role === "assistant"
      );
    });
  },
  parse(records, sourcePath) {
    const meta: SessionDocument["meta"] = {};
    const events: SessionEvent[] = [];
    const warnings: string[] = [];

    for (const record of records) {
      if (!isRecord(record.value)) {
        continue;
      }
      const type = stringValue(record.value.type);
      const timestamp = timestampOf(record.value);
      if (type === "summary") {
        const summary = firstText(record.value, ["summary", "text"]);
        if (summary) {
          meta.summary = summary;
        }
        continue;
      }

      const message = isRecord(record.value.message) ? record.value.message : record.value;
      const role = stringValue(message.role) ?? type ?? "event";
      const content = message.content;
      const parsedEvents = parseContentBlocks(`claude-${record.line}`, content, timestamp, role);
      if (parsedEvents.length > 0) {
        events.push(...parsedEvents.map((event) => ({ ...event, raw: event.raw ?? record.value })));
        continue;
      }

      const text = firstText(record.value, ["text", "content"]);
      if (text) {
        events.push({
          id: `claude-${record.line}`,
          kind: role === "system" ? "system" : "message",
          role,
          title: role,
          text,
          timestamp,
          raw: record.value,
        });
      }
    }

    if (events.length === 0) {
      warnings.push("no Claude message events found");
    }

    const title =
      stringValue(meta.summary) ??
      (sourcePath ? sourcePath.split(/[\\/]/u).pop() : undefined) ??
      "Claude session";
    return {
      format: "claude",
      title,
      sourcePath,
      meta,
      events: expandMemoryCitationEvents(events),
      warnings,
    };
  },
};
