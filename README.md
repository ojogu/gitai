# gitAI

## AI-Powered Git Commit Message Generator

gitAI is a developer CLI tool that analyzes staged git changes and generates contextually accurate commit messages in seconds — no more struggling to articulate "what changed and why."

---

## The Problem

Writing clear, meaningful commit messages is one of the most overlooked time-sinks in software development. Developers either rush through commits to get back to coding, or spend minutes trying to articulate intent. Vague messages like "update logic" or "fix" make git history useless for code review, debugging, and changelog generation.

gitAI solves this by running `gitai` after staging changes — it analyzes the diff, detects what was added/removed/modified, and returns a conventional commit message ready to confirm. The tool handles retries automatically if the first suggestion isn't quite right.

---

## Key Features

- Analyzes staged git changes and generates contextually accurate commit messages
- Detects language-agnostic patterns: function/class additions, exports, async, decorators
- Supports Conventional Commits format (feat, fix, refactor, test, chore, etc.)
- Includes raw diff in prompts so the LLM can verify hints against ground truth
- Confidence scoring flags large changesets for manual review
- Breaking change detection for API removals and export changes
- Configurable retry logic — regenerate or pick from previous attempts
- Auto-commit and auto-push workflows for automated pipelines
- Global and project-level configuration via file or environment variables

---

## Tech Stack

| Layer | Technology |
|------|------------|
| Language | Python 3.10+ |
| LLM Abstraction | litellm (Google Gemini, OpenAI, Groq, Anthropic) |
| Diff Parsing | unidiff |
| CLI Formatting | rich |
| Packaging | setuptools |

**Why litellm?** Provides a unified API for multiple LLM providers, making it trivial to switch models without code changes.

**Why unidiff?** Handles the messy details of unified diff parsing — hunk headers, line numbers, context — so the tool can focus on semantic extraction.

**Why rich?** Delivers beautiful, readable terminal output for messages, prompts, and error handling.

---

## System Architecture

```
git diff --cached → parser.py → extractor.py → schema_builder.py → llm.py → commit message
       (unidiff)    (signals)      (hints + diff)  (litellm)
```

1. **parser.py**: Parses staged diff output into structured hunks with 3 lines of context
2. **extractor.py**: Detects semantic patterns — function additions, class changes, exports
3. **schema_builder.py**: Merges signals with raw diffs, adds heuristics (type, scope, breaking change flags)
4. **llm.py**: Builds prompt, calls LLM via litellm, parses response

See `docs/README.md` for the full architecture deep-dive.

---

## Getting Started

### Prerequisites

- Python 3.10+
- Git repository with staged changes
- API key from an LLM provider (Google Gemini, OpenAI, Groq)

### Installation

```bash
# Clone and install
git clone https://github.com/ojogu/gitai.git
cd gitai

# Copy environment template
cp .env.example .env

# Install dependencies
pip install -e .
```

### Configuration

```bash
# Interactive setup (recommended)
gitai init

# Or manually edit ~/.config/gitai/config.json
```

### Usage

```bash
# Stage your changes
git add .

# Generate commit message
gitai
```

---

## Project Structure

```
gitAI/
├── src/gitai/
│   ├── cli/
│   │   └── cli.py              # Main CLI entry point
│   ├── core/
│   │   ├── parser.py           # Diff parsing (unidiff)
│   │   ├── extractor.py        # Semantic signal extraction
│   │   ├── schema_builder.py  # Hints + raw diff merging
│   │   ├── llm.py              # LLM API calls (litellm)
│   │   └── prompt.py           # Prompt construction
│   └── utils/
│       ├── config.py           # Project config loader
│       ├── global_config.py   # Global config (XDG)
│       ├── exceptions.py       # Custom exception hierarchy
│       └── log.py             # SafeLogger (sanitization)
├── docs/                       # Architecture deep-dives
├── config.json                 # Project-level config
└── .env.example               # Environment template
```

---

## Development Commands

```bash
# Type checking (if configured)
ruff check src/

# Tests
pytest src/test/

# Format check
ruff format --check src/
```

---

## Real Engineering Challenges

- **Confidence scoring**: Large changesets (>5 files, >50 lines) make heuristic commit type inference unreliable. The tool forces "low confidence" and instructs the LLM to derive intent directly from the diff.

- **Breaking change detection**: False positives are costly. Built a conservative multi-layered detector checking file deletions, config modifications, and export patterns — letting the LLM validate flagged changes.

- **LLM response handling**: Truncated responses and JSON code fences caused parsing failures. Implemented truncation detection and fallback to plain text.

- **Credential exposure**: API keys in debug output risked leakage. Built SafeLogger with regex-based sanitization before any log write.

See `docs/README.md` for full architecture details.

---

## Contact & License

- **Author**: Precious Ojogu
- **GitHub**: https://github.com/ojogu/gitai
- **License**: MIT

---

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)