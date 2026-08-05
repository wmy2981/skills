# CLAUDE.md

## Repository Structure

This is a collection of **agent skills**. Each skill is a self-contained directory following this pattern:

```
skill-name/
├── .claude-plugin/
│   └── plugin.json   # Claude Code plugin manifest (each skill is its own plugin)
├── SKILL.md          # Skill definition — trigger keywords, usage, docs
├── scripts/          # Helper scripts that power the skill
│   ├── .env.example  # Environment variable template (mandatory if env vars needed)
│   └── ...           # Script files
└── references/       # Reference docs, config templates (optional)
```

Root-level files:
- `.claude-plugin/marketplace.json` — marketplace manifest listing every skill as an installable plugin (`"source": "./<skill-name>"`). Keep it in sync when adding/removing skills.
- `README.md` — bilingual skill index with descriptions
- `CLAUDE.md` — this file, conventions for AI agent development

Each skill doubles as a standalone Claude Code plugin: `claude plugin marketplace add <repo>` then `claude plugin install <skill>@wmy-skills`. Users may install any subset — plugin.json's `name` must equal the SKILL.md frontmatter `name`.

## Skill Conventions

### SKILL.md

- **Written in English.**
- **Must** load the `skill-creator` skill and follow its instructions.
- Include an **Execution Rule** near the top: run the user's command directly without pre-checking; fix on failure. (Default)
- List dependencies under a **Requirements** section.
- Keep content under 500 lines; use `references/` for large reference docs.
- Frontmatter must include `skill_version` (semver) under `metadata:` (see Versioning). (Note: a bare indented `skill_version:` inside a `description: >-` block gets swallowed into the description string.)

### Versioning

Bump the skill version **exactly once per commit**, no matter how many changes the commit contains or how large they are:

- Bump BOTH the SKILL.md frontmatter `metadata.skill_version` AND the `version` field in the same skill's `.claude-plugin/plugin.json` to the same value.
- Increment exactly one digit by 1 (e.g. `1.1.0` → `1.1.1`). Never jump versions or increment more than one digit in a single commit.
- CI rejects a mismatch between the two files.

### Environment Variables

**User-facing setup** — when guiding the user to configure env vars, prefer the **shared global file** `~/.wmyskills/.env`. Read `scripts/.env.example` first, then add or update the env vars the skill needs in `~/.wmyskills/.env`. Do not run `cp .env.example path/to/.env` directly to avoid overwriting the original.

**Script loading** — always load env vars with explicit paths: `scripts/.env` (per-skill) first, then `~/.wmyskills/.env` (shared global). Loading never overrides existing values, so the earlier load takes priority (both `dotenv` and `load_dotenv` behave this way). The tracked template is `scripts/.env.example`.

Python:

```python
load_dotenv(dotenv_path=Path(__file__).parent / ".env")       # per-skill
load_dotenv(dotenv_path=Path.home() / ".wmyskills" / ".env")  # shared global
```

TypeScript (run with Bun, see Common Commands):

```typescript
import * as dotenv from "dotenv"; // namespace import — passes `tsc --noEmit` without esModuleInterop
import os from "node:os";
import path from "node:path";

dotenv.config({ path: path.join(import.meta.dirname, ".env") });        // per-skill
dotenv.config({ path: path.join(os.homedir(), ".wmyskills", ".env") }); // shared global
```

### Scripts

Scripts may be written in **Python** or **TypeScript**. Keep the language consistent within a skill.

- **English output** — all user-facing text, CLI help, and JSON keys must be English.
- **`--help` must work without env vars** — env initialization goes after argument parsing (e.g. `argparse.parse_args()` in Python; parse CLI args before touching env in TypeScript).
- **UTF-8 support** — scripts that may output non-ASCII text (e.g. echoing user-provided filenames or content, allowed even though default output is English) must ensure UTF-8 console output. Patterns below.

**Python** — standard pattern (placed after imports, before any code):

```python
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
if sys.platform == "win32":
    subprocess.run("chcp 65001", shell=True, capture_output=True)
```

**TypeScript** — skip the stdout reconfigure (Bun always writes UTF-8 bytes), but still switch the console codepage on Windows so it renders correctly. Place after imports:

```typescript
import { execSync } from "node:child_process";

if (process.platform === "win32") {
  try {
    execSync("chcp 65001", { stdio: "ignore" });
  } catch {
    // chcp unavailable (e.g. minimal shells) — output is already UTF-8 bytes
  }
}
```

### Runtime Data

Configs, templates, and output files produced at runtime go in `~/.wmyskills/<skill-name>/`. Never store runtime data inside skill folders.

## Common Commands

### Python

```bash
pip install -r <skill>/requirements.txt          # install dependencies (if requirements.txt exists)
pip install pyyaml python-dotenv                 # common across skills
python -m py_compile <skill>/scripts/*.py        # syntax check
python <skill>/scripts/<script>.py --help        # smoke test entry point
```

### TypeScript (Bun)

```bash
bun install                                      # install dependencies (run in skill dir)
bun add dotenv                                   # common across skills
bunx tsc --noEmit                                # type-check (requires tsconfig.json + typescript devDependency)
bun run <skill>/scripts/<script>.ts --help       # smoke test entry point
```

### Validation (language-agnostic)

```bash
# SKILL.md frontmatter
python -c "import yaml; yaml.safe_load(open('<skill>/SKILL.md').read().split('---')[1])"

# Plugin manifests (Claude Code CLI)
claude plugin validate <skill>                       # per-skill plugin.json
claude plugin validate .claude-plugin/marketplace.json
```

## Skill Development Checklist

When developing or modifying a skill (condensed from the conventions above — refer to them for details):

- [ ] **SKILL.md** — English, with trigger keywords, Execution Rule, Requirements
- [ ] **Script** — English output, UTF-8 support, `--help` without env vars (Python or TypeScript)
- [ ] **`.env.example`** — created if the script needs env vars
- [ ] **Runtime data** — stored in `~/.wmyskills/<skill-name>/`, not in the repo
- [ ] **Tests** — syntax/type check (`py_compile` or `tsc --noEmit`) + `--help` smoke test
- [ ] **Plugin manifests** — `plugin.json` (name matches SKILL.md frontmatter, version matches `skill_version`) + `marketplace.json` entry; validate with `claude plugin validate`
- [ ] **`README.md`** — update if adding/removing a skill
- [ ] **Commit** — after all checks pass

## Git Workflow

- Commits follow Conventional Commits: `type(scope): lowercase description` in English
