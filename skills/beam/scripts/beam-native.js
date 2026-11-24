import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

function findBinary() {
  const filename = process.platform === "win32" ? "beam.exe" : "beam";
  for (const dir of (process.env.PATH || "").split(path.delimiter)) {
    if (!path.isAbsolute(dir)) continue;
    const executable = path.join(dir, filename);
    try {
      fs.accessSync(executable, fs.constants.X_OK);
      if (!fs.statSync(executable).isFile()) continue;
      // A symlink to this installed skill can also appear on PATH.
      if (fs.realpathSync(executable) === fs.realpathSync(process.argv[1])) continue;
      const probe = spawnSync(executable, ["skill-v1", "--protocol"], {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "ignore"],
        maxBuffer: 128,
        timeout: 3_000,
      });
      if (probe.status === 0 && probe.stdout === "1\n") return executable;
    } catch {
      // This candidate does not provide the installed-skill protocol.
    }
  }
}

// A failed mutating call may have committed remotely. Only the read-only
// capability probe is allowed to select the legacy transport.
export function nativeTransfer(command, mode, endpoint, payload, options) {
  // The standalone receiver discovers routes from a gateway base. Older hooks
  // also accepted arbitrary upload URLs, which must receive their exact POST.
  if (!new URL(endpoint).pathname.endsWith("/api/v1/beam/sessions")) return undefined;
  const exe = findBinary();
  if (!exe) return undefined;
  const operation = mode === "publish" || mode === "hook" ? "share" : mode;
  const request = {
    operation,
    endpoint,
    beamId: payload.beamId,
    ...(options.state ? { state: options.state } : {}),
    ...(payload.items && ["share", "handoff"].includes(operation)
      ? { packet: JSON.stringify(payload) }
      : {}),
    ...(operation === "handoff" && command === "publish" ? { snapshotFallback: true } : {}),
    ...(mode === "hook" ? { hook: true } : {}),
    ...(options.timeout ? { timeoutMs: Number(options.timeout) } : {}),
    ...(options["profile-dir"] ? { profileDir: options["profile-dir"] } : {}),
    ...(options.cli ? { cli: options.cli } : {}),
    ...(options.agent ? { agent: options.agent } : {}),
    ...(operation === "continue"
      ? { message: options.message, requestId: options["request-id"] }
      : {}),
  };
  const result = spawnSync(exe, ["skill-v1"], {
    input: JSON.stringify(request),
    encoding: "utf8",
    maxBuffer: 5 * 1024 * 1024,
    stdio: ["pipe", "pipe", "pipe"],
  });
  if (result.status !== 0) {
    throw new Error(
      result.stderr?.trim() || "Native Beam did not return a receipt. Reconcile before retrying.",
    );
  }
  let receipt;
  try {
    receipt = JSON.parse(result.stdout);
  } catch {
    throw new Error("Native Beam returned an unreadable receipt. Reconcile before retrying.");
  }
  if (!receipt || typeof receipt !== "object" || Array.isArray(receipt)) {
    throw new Error("Native Beam returned an invalid receipt. Reconcile before retrying.");
  }
  return receipt;
}
