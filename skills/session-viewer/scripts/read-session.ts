import fs from "node:fs/promises";
import type { FileHandle } from "node:fs/promises";

async function readExactly(handle: FileHandle, length: number, position: number): Promise<Buffer> {
  const buffer = Buffer.alloc(length);
  let offset = 0;
  while (offset < length) {
    const { bytesRead } = await handle.read(buffer, offset, length - offset, position + offset);
    if (bytesRead === 0) {
      throw new Error("session file ended before the expected read completed; retry the export");
    }
    offset += bytesRead;
  }
  return buffer;
}

export async function readSessionText(
  file: string,
  maxBytes?: number,
): Promise<{ size: number; text: string; truncated: boolean }> {
  if (maxBytes === undefined) {
    const buffer = await fs.readFile(file);
    return { size: buffer.length, text: buffer.toString("utf8"), truncated: false };
  }
  const handle = await fs.open(file, "r");
  try {
    const { size } = await handle.stat();
    if (size <= maxBytes) {
      return { size, text: (await readExactly(handle, size, 0)).toString("utf8"), truncated: false };
    }
    const headLength = Math.ceil(maxBytes / 2);
    const tailLength = maxBytes - headLength;
    const head = await readExactly(handle, headLength, 0);
    const tail = await readExactly(handle, tailLength, size - tailLength);
    return {
      size,
      text: `${head.toString("utf8")}\n[...middle omitted for scan...]\n${tail.toString("utf8")}`,
      truncated: true,
    };
  } finally {
    await handle.close();
  }
}
