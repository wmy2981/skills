#!/usr/bin/env bun
/**
 * CLI wrapper for the chinese-poetry-api REST service.
 * Repo: https://github.com/palemoky/chinese-poetry-api
 * All responses are printed as raw JSON, exactly as the server returns them.
 */

import * as dotenv from "dotenv"; // namespace import — passes `tsc --noEmit` without esModuleInterop
import { execSync } from "node:child_process";
import os from "node:os";
import path from "node:path";

const VERSION = "1.0.0";
// POETRY_API_URL overrides it and must also be a full base — the script appends nothing.
const DEFAULT_BASE_URL = "https://poetry.palemoky.com/api";
const TIMEOUT_MS = 30_000;

if (process.platform === "win32") {
  try {
    execSync("chcp 65001", { stdio: "ignore" });
  } catch {
    // chcp unavailable (e.g. minimal shells) — output is already UTF-8 bytes
  }
}

type Values = Map<string, string[]>;

interface Flag {
  name: string;
  desc: string;
  repeatable?: boolean;
}

interface Command {
  summary: string;
  flags: Flag[];
  required?: string[];
  noLang?: boolean; // server rejects the lang param on this endpoint
  build: (v: Values) => string;
}

function get(v: Values, key: string): string | undefined {
  return v.get(key)?.[0];
}

function has(v: Values, key: string): boolean {
  return (v.get(key)?.length ?? 0) > 0;
}

function qs(v: Values, keys: string[]): string {
  const p = new URLSearchParams();
  for (const key of keys) {
    for (const value of v.get(key) ?? []) {
      p.append(key.replace(/-/g, "_"), value);
    }
  }
  return p.toString();
}

const COMMANDS: Record<string, Command> = {
  health: {
    summary: "Health check",
    flags: [],
    build: () => `/health`,
  },
  stats: {
    summary: "Overall statistics (poem/author/dynasty counts)",
    flags: [],
    noLang: true, // /stats rejects any query parameter, including lang
    build: () => `/stats`,
  },
  poems: {
    summary: "List poems with filters",
    flags: [
      { name: "dynasty", desc: "Dynasty name, e.g. 唐" },
      { name: "author", desc: "Author name, e.g. 李白" },
      { name: "dynasty-id", desc: "Dynasty ID" },
      { name: "type-id", desc: "Poetry type ID (repeatable, OR)", repeatable: true },
      { name: "page", desc: "Page number, default 1" },
      { name: "page-size", desc: "Page size, max 100" },
    ],
    build: (v) =>
      `/poems?${qs(v, ["dynasty", "author", "dynasty-id", "type-id", "page", "page-size"])}`,
  },
  search: {
    summary: "Full-text search",
    required: ["q"],
    flags: [
      { name: "q", desc: "Search query (required)" },
      { name: "type", desc: "Search field: all (default), title, content, author" },
      { name: "page", desc: "Page number, default 1" },
      { name: "page-size", desc: "Page size, max 100" },
    ],
    build: (v) => `/poems/search?${qs(v, ["q", "type", "page", "page-size"])}`,
  },
  random: {
    summary: "Random poem (filterable)",
    flags: [
      { name: "author", desc: "Author name" },
      { name: "author-id", desc: "Author ID" },
      { name: "dynasty", desc: "Dynasty name" },
      { name: "dynasty-id", desc: "Dynasty ID" },
      { name: "type", desc: "Poetry type name (repeatable, OR)", repeatable: true },
      { name: "type-id", desc: "Poetry type ID" },
      { name: "char", desc: "Single character (飞花令); only combinable with --lang" },
    ],
    build: (v) =>
      `/poems/random?${qs(v, ["author", "author-id", "dynasty", "dynasty-id", "type", "type-id", "char"])}`,
  },
  authors: {
    summary: "List authors",
    flags: [
      { name: "page", desc: "Page number, default 1" },
      { name: "page-size", desc: "Page size, max 100" },
    ],
    build: (v) => `/authors?${qs(v, ["page", "page-size"])}`,
  },
  author: {
    summary: "Get an author by ID",
    required: ["id"],
    flags: [{ name: "id", desc: "Author ID (required)" }],
    build: (v) => `/authors/${get(v, "id")}`,
  },
  dynasties: {
    summary: "List dynasties (with poem counts)",
    flags: [],
    build: () => `/dynasties`,
  },
  dynasty: {
    summary: "Get a dynasty by ID",
    required: ["id"],
    flags: [{ name: "id", desc: "Dynasty ID (required)" }],
    build: (v) => `/dynasties/${get(v, "id")}`,
  },
  types: {
    summary: "List poetry types",
    flags: [],
    build: () => `/types`,
  },
  type: {
    summary: "Get a poetry type by ID",
    required: ["id"],
    flags: [{ name: "id", desc: "Poetry type ID (required)" }],
    build: (v) => `/types/${get(v, "id")}`,
  },
};

function help(): void {
  console.log(`chinese-poetry-api CLI ${VERSION}`);
  console.log("Query the chinese-poetry-api REST service (https://github.com/palemoky/chinese-poetry-api)");
  console.log("Usage: main.ts <command> [options]");
  console.log("Run 'main.ts <command> --help' for command details.\n");
  console.log("Commands:");
  for (const [name, cmd] of Object.entries(COMMANDS)) {
    console.log(`  ${name.padEnd(10)} ${cmd.summary}`);
  }
  console.log(`\nCommon option: --lang zh-Hans|zh-Hant  Switch simplified/traditional Chinese`);
  console.log("Flags accept both --name and -name forms (e.g. -q 静夜思).");
}

function commandHelp(name: string, cmd: Command): void {
  console.log(`Usage: main.ts ${name} [options]\n`);
  console.log(`${cmd.summary}\n`);
  console.log("Options:");
  for (const f of cmd.flags) {
    console.log(`  --${f.name.padEnd(12)} ${f.desc}${f.repeatable ? " (repeatable)" : ""}`);
  }
  if (!cmd.noLang) console.log("  --lang         Language: zh-Hans (default) or zh-Hant");
}

function fail(msg: string): never {
  console.error(`Error: ${msg}`);
  console.error("Run 'main.ts --help' for usage.");
  process.exit(1);
}

function parseFlags(args: string[]): Values {
  const values: Values = new Map();
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg.startsWith("-") && arg !== "-") {
      // Accept both --name and -name (e.g. -q 静夜思). "--" vs "-" only affects display.
      const stripped = arg.replace(/^-+/, "");
      const eq = stripped.indexOf("=");
      let key: string;
      let val: string | undefined;
      if (eq > 0) {
        key = stripped.slice(0, eq);
        val = stripped.slice(eq + 1);
      } else {
        key = stripped;
        val = args[i + 1];
        if (val !== undefined && !val.startsWith("-")) {
          i++;
        } else {
          val = undefined;
        }
      }
      if (val === undefined || val === "") fail(`Flag --${key} requires a value`);
      const list = values.get(key) ?? [];
      list.push(val);
      values.set(key, list);
    } else {
      fail(`Unexpected argument: ${arg}`);
    }
  }
  return values;
}

async function request(baseUrl: string, p: string): Promise<void> {
  try {
    const res = await fetch(`${baseUrl}${p}`, { signal: AbortSignal.timeout(TIMEOUT_MS) });
    const text = await res.text();
    if (!res.ok) {
      console.error(`Error ${res.status}: ${text}`);
      process.exit(1);
    }
    console.log(text);
  } catch (err) {
    console.error(`Request failed: ${(err as Error).message}`);
    process.exit(1);
  }
}

async function main(): Promise<void> {
  const argv = process.argv.slice(2);
  if (argv.length === 0 || argv[0] === "--help" || argv[0] === "-h") {
    help();
    process.exit(0);
  }

  const name = argv[0];
  const cmd = COMMANDS[name];
  if (!cmd) fail(`Unknown command: ${name}`);

  if (argv.includes("--help") || argv.includes("-h")) {
    commandHelp(name, cmd);
    process.exit(0);
  }

  const values = parseFlags(argv.slice(1));

  // Validate flags before touching any config
  const valid = new Set(cmd.flags.map((f) => f.name));
  valid.add("lang"); // global flag, valid on every command
  for (const key of values.keys()) {
    if (!valid.has(key)) fail(`Unknown flag --${key} for command '${name}'`);
    const repeatable = cmd.flags.find((f) => f.name === key)?.repeatable ?? false; // lang: not repeatable
    if (!repeatable && (values.get(key)?.length ?? 0) > 1) {
      fail(`Flag --${key} can only be used once`);
    }
  }
  for (const req of cmd.required ?? []) {
    if (!has(values, req)) fail(`Missing required flag --${req}`);
  }

  // Environment initialization goes after argument parsing (--help works without env)
  dotenv.config({ path: path.join(import.meta.dirname, ".env") });        // per-skill
  dotenv.config({ path: path.join(os.homedir(), ".wmyskills", ".env") }); // shared global

  const lang = get(values, "lang");
  if (lang && cmd.noLang) fail(`Command '${name}' does not support --lang`);
  const baseUrl = (process.env.POETRY_API_URL || DEFAULT_BASE_URL).replace(/\/+$/, "");
  let p = cmd.build(values);
  if (lang) {
    const sep = p.includes("?") ? "&" : "?";
    p = `${p}${sep}lang=${encodeURIComponent(lang)}`;
  }

  await request(baseUrl, p);
}

main();
