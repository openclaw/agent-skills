export type OpenBrowserCommand = {
  args: string[];
  executable: string;
};

export function resolveOpenBrowserCommand(
  platform: NodeJS.Platform,
  filePath: string,
): OpenBrowserCommand {
  if (platform === "darwin") {
    return { executable: "open", args: [filePath] };
  }
  if (platform === "win32") {
    return { executable: "explorer.exe", args: [filePath] };
  }
  return { executable: "xdg-open", args: [filePath] };
}
