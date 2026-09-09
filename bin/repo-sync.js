#!/usr/bin/env node
// ponytail: thin shim — Node only spawns python, no deps
const { spawnSync, spawn } = require("child_process");
const { existsSync } = require("fs");
const path = require("path");
const os = require("os");

const PKG_ROOT = path.resolve(__dirname, "..");
const PY = process.env.PYTHON || (os.platform() === "win32" ? "python" : "python3");

function findConsumerRoot(cwd) {
  let cur = path.resolve(cwd);
  for (let i = 0; i < 6; i++) {
    if (existsSync(path.join(cur, ".agents"))) return cur;
    const parent = path.dirname(cur);
    if (parent === cur) break;
    cur = parent;
  }
  return path.resolve(cwd);
}

function runPy(args, opts = {}) {
  const r = spawnSync(PY, args, { stdio: "inherit", shell: false, ...opts });
  return r.status ?? 1;
}

function printHelp() {
  console.log(`repo-sync — blast-radius + dashboard

Usage:
  repo-sync dashboard [--port 8765] [--open] [--once --json .agent/dashboard.json]
    Live view: human http://127.0.0.1:PORT  agent: curl /api/status or cat .agent/dashboard.json

  repo-sync add <skill>            copy .agents/skills/<skill> to consumer
  repo-sync validate [path]        python scripts/validate.py
  repo-sync manifest               python scripts/manifest.py
  repo-sync --help

Examples:
  npx --package @snoozer10/synthesize-skills repo-sync dashboard --port 8765 --open
  repo-sync dashboard --port 0 --once
  repo-sync dashboard --watch
`);
}

const argv = process.argv.slice(2);
const cmd = argv[0];

if (!cmd || cmd === "--help" || cmd === "-h" || cmd === "help") {
  printHelp();
  process.exit(0);
}

if (cmd === "dashboard") {
  const dash = path.posix.join(".agents", "skills", "repo-blast-radius-sync", "scripts", "dashboard.py");
  const dashAbs = path.join(PKG_ROOT, dash);
  // resolve consumer root for dashboard data (cwd)
  const consumerRoot = findConsumerRoot(process.cwd());
  // parse dashboard args passthrough
  const dashArgs = [dashAbs, ...argv.slice(1)];
  // if --open flag, start http then open browser
  const openIdx = dashArgs.indexOf("--open");
  const shouldOpen = openIdx !== -1;
  if (shouldOpen) dashArgs.splice(openIdx, 1);
  // find port to open
  let port = "8765";
  const pIdx = dashArgs.indexOf("--port");
  if (pIdx !== -1 && dashArgs[pIdx + 1]) port = dashArgs[pIdx + 1];
  if (port === "0") port = null; // random — dashboard.py will choose, we can't know beforehand without parsing output

  if (shouldOpen) {
    // spawn detached http, then open browser after short delay
    const child = spawn(PY, dashArgs, { stdio: "inherit", cwd: consumerRoot, shell: false });
    setTimeout(() => {
      const url = `http://127.0.0.1:${port || 8765}`;
      const opener = os.platform() === "win32" ? "start" : os.platform() === "darwin" ? "open" : "xdg-open";
      try { require("child_process").exec(`${opener} ${url}`); } catch {}
    }, 800);
    child.on("close", (c) => process.exit(c ?? 0));
  } else {
    const code = runPy(dashArgs, { cwd: consumerRoot });
    process.exit(code);
  }
} else if (cmd === "add") {
  const skill = argv[1];
  if (!skill) { console.error("usage: repo-sync add <skill-name>"); process.exit(2); }
  // copy from PKG_ROOT/.agents/skills/<skill> -> consumer/.agents/skills/<skill> (+ 3 hosts)
  const src = path.join(PKG_ROOT, ".agents", "skills", skill);
  if (!existsSync(src)) { console.error(`skill not found in package: ${skill}`); process.exit(1); }
  const consumerRoot = findConsumerRoot(process.cwd());
  const code = runPy([path.join(PKG_ROOT, "scripts", "validate.py"), path.join(src)], { cwd: PKG_ROOT });
  if (code !== 0) process.exit(code);
  const { mkdirSync, readdirSync, copyFileSync, statSync, readFileSync } = require("fs");
  const { createHash } = require("crypto");
  function copyRec(srcDir, destDir) {
    mkdirSync(destDir, { recursive: true });
    for (const ent of readdirSync(srcDir, { withFileTypes: true })) {
      const s = path.join(srcDir, ent.name);
      const d = path.join(destDir, ent.name);
      if (ent.isDirectory()) copyRec(s, d);
      else {
        // SHA256 skip
        let skip = false;
        if (existsSync(d)) {
          try {
            const a = createHash("sha256").update(readFileSync(s)).digest("hex");
            const b = createHash("sha256").update(readFileSync(d)).digest("hex");
            if (a === b) skip = true;
          } catch {}
        }
        if (!skip) copyFileSync(s, d);
      }
    }
  }
  for (const host of [".agents", ".claude", ".opencode", ".gemini"]) {
    copyRec(src, path.join(consumerRoot, host, "skills", skill));
  }
  console.log(`added ${skill} to ${consumerRoot}/.{agents,claude,opencode,gemini}/skills/${skill}`);
  runPy([path.join(PKG_ROOT, "scripts", "manifest.py")], { cwd: consumerRoot });
} else if (cmd === "validate") {
  const target = argv[1] || ".";
  process.exit(runPy([path.join(PKG_ROOT, "scripts", "validate.py"), target], { cwd: process.cwd() }));
} else if (cmd === "manifest") {
  process.exit(runPy([path.join(PKG_ROOT, "scripts", "manifest.py")], { cwd: process.cwd() }));
} else {
  console.error(`unknown command: ${cmd}`); printHelp(); process.exit(2);
}
