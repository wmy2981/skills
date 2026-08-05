# CLAUDE.md

## Repository Structure

This is a collection of **agent skills**. Each skill is a self-contained directory following this pattern:

```
skill-name/
├── SKILL.md           # Skill definition — trigger keywords, usage, docs
├── scripts/           # Helper scripts that power the skill
│   ├── .env.example   # Environment variable template (mandatory if env vars needed)
│   └── ...            # Script files
└── references/        # Reference docs, config templates (optional)
```

Root-level files:
- `README.md` — bilingual skill index with descriptions
- `CLAUDE.md` — this file, conventions for AI agent development

## Skill Conventions

### SKILL.md
- **Written in English.**
- **Must** load the `skill-creator` skill and follow its instructions.
- Include an **Execution Rule** near the top: run the user's command directly without pre-checking; fix on failure. (Default)
- List dependencies under a **Requirements** section.
- Keep content under 500 lines; use `references/` for large reference docs.
- **Environment variable setup**: when guiding the user to configure env vars, prefer the **shared global file** `~/.wmyskills/.env`. Read `scripts/.env.example` first, then add or update the env vars that skill needs in `~/.wmyskills/.env`.Do not run `cp .env.example path/to/.env` directly to avoid overwritting origin.

### Scripts

Scripts may be written in **Python** or **TypeScript** — both are supported. Keep the language consistent within a skill.

- **English output** — all user-facing text, CLI help, and JSON keys must be English.
- **`--help` must work without env vars** — env initialization goes after argument parsing (e.g. `argparse.parse_args()` in Python; parse CLI args before touching env in TypeScript).
- **Environment variables** — always load with explicit paths: `scripts/.env` (per-skill) first, then `~/.wmyskills/.env` (shared global). Loading never overrides existing values, so the earlier load takes priority. The tracked template is `scripts/.env.example`.

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
  `dotenv` never overrides existing values, matching Python's `load_dotenv` semantics.

### Runtime Data
Configs, templates, and output files produced at runtime go in `~/.wmyskills/<skill-name>/`. Never store runtime data inside skill folders.

## Common Commands

```bash
# Python — install dependencies
pip install -r <skill>/requirements.txt          # if requirements.txt exists
pip install pyyaml python-dotenv                 # common across skills

# Python — check script syntax
python -m py_compile <skill>/scripts/*.py

# Validate SKILL.md frontmatter (language-agnostic)
python -c "import yaml; yaml.safe_load(open('<skill>/SKILL.md').read().split('---')[1])"

# Python — test script entry point
python <skill>/scripts/<script>.py --help

# TypeScript — install dependencies (run in skill dir)
bun install                                      # if package.json exists
bun add dotenv                                   # common across skills

# TypeScript — type-check scripts (requires tsconfig.json + typescript devDependency)
bunx tsc --noEmit

# TypeScript — test script entry point
bun run <skill>/scripts/<script>.ts --help
```

## Windows UTF-8 Support

Python scripts that may output non-ASCII text — e.g. echoing user-provided filenames or content, allowed even though default output is English — must add UTF-8 console support. Standard pattern (placed after imports, before any code):

```python
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
if sys.platform == "win32":
    subprocess.run("chcp 65001", shell=True, capture_output=True)
```

TypeScript scripts skip the stdout reconfigure (Bun always writes UTF-8 bytes), but must still switch the console codepage on Windows so it renders correctly. Place after imports:

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

## Skill Development Checklist

When developing or modifying a skill:

- [ ] **SKILL.md** — English, with trigger keywords, Execution Rule, Requirements
- [ ] **Script** — English output, UTF-8 support, `--help` without env vars (Python or TypeScript)
- [ ] **`.env.example`** — created if the script needs env vars
- [ ] **Runtime data** — stored in `~/.wmyskills/<skill-name>/`, not in the repo
- [ ] **Tests** — syntax/type check (`py_compile` or `tsc --noEmit`) + `--help` smoke test
- [ ] **`README.md`** — update if adding/removing a skill
- [ ] **Commit** — after all checks pass

## Git Workflow

- Commits follow Conventional Commits: `type(scope): lowercase description` in English
