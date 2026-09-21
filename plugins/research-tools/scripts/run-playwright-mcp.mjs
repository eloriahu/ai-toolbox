import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const packageSpec = "@playwright/mcp@0.0.82";
const passthroughArgs = process.argv.slice(2);
const isWindows = process.platform === "win32";
const lookupCommand = isWindows ? "where.exe" : "which";

function commandOnPath(name) {
  const result = spawnSync(lookupCommand, [name], {
    encoding: "utf8",
    windowsHide: true,
  });
  return result.status === 0 && result.stdout.trim().length > 0;
}

const candidates = [];

if (commandOnPath(isWindows ? "npx.cmd" : "npx")) {
  candidates.push({
    command: isWindows ? "npx.cmd" : "npx",
    args: ["-y", packageSpec, ...passthroughArgs],
  });
}

if (commandOnPath(isWindows ? "pnpm.cmd" : "pnpm")) {
  candidates.push({
    command: isWindows ? "pnpm.cmd" : "pnpm",
    args: ["--package", packageSpec, "dlx", "playwright-mcp", ...passthroughArgs],
  });
}

const bundledPnpm = isWindows
  ? join(
      homedir(),
      ".cache",
      "codex-runtimes",
      "codex-primary-runtime",
      "dependencies",
      "bin",
      "fallback",
      "pnpm.cmd",
    )
  : join(
      homedir(),
      ".cache",
      "codex-runtimes",
      "codex-primary-runtime",
      "dependencies",
      "bin",
      "fallback",
      "pnpm",
    );

if (existsSync(bundledPnpm)) {
  candidates.push({
    command: bundledPnpm,
    args: ["--package", packageSpec, "dlx", "playwright-mcp", ...passthroughArgs],
  });
}

if (candidates.length === 0) {
  console.error(
    "Playwright MCP needs npx or pnpm. Install Node.js with npm/pnpm, then retry.",
  );
  process.exit(1);
}

const selected = candidates[0];
const result = spawnSync(selected.command, selected.args, {
  stdio: "inherit",
  shell: isWindows,
  windowsHide: true,
});

if (result.error) {
  console.error(`Unable to start Playwright MCP: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
