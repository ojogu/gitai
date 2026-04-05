# Changelog

All notable changes to this project will be documented in this file.

## [0.1.3] - 2026-04-05

### Added
- **Global Configuration System**: Configuration now stored in `~/.config/gitai/config.json` for persistent settings across projects
- **New CLI Commands**:
  - `gitai init` - Interactive configuration setup with model selection presets
  - `gitai config` - View current configuration (API key masked for security)
  - `gitai config key=value` - Update specific configuration settings
  - `gitai help` - Display help information and usage examples
- **Configuration Precedence**: Environment variables > Global config > Default values
- **Interactive Setup Wizard**: Beautiful Rich UI with panels, colors, and guided prompts
- **Model Presets**: Quick selection for popular models (Gemini 2.5 Flash, Gemini 1.5 Pro, GPT-4o)
- **API Key Masking**: Sensitive API keys are masked in configuration output (e.g., `AIza••••••••chyg`)

### Changed
- **Entry Point**: Updated from `gitai.cli.cli:main` to `gitai.main:main_entry` for command handling
- **Documentation**: Updated README.md with comprehensive installation methods (uv, pipx, pip, source)
- **Author Info**: Updated with real social media links (LinkedIn, X)

### Fixed
- **.env Parsing**: Removed inline comments that were causing environment variable parsing issues
- **Configuration Loading**: Fixed LLM_MODEL environment variable not being loaded correctly

### Technical Changes
- Added `src/gitai/utils/global_config.py` module for global configuration management
- Updated `src/gitai/core/llm.py` to fall back to global config when env vars are not set
- Updated `pyproject.toml` entry point to use new command handler

---

## [0.1.0] - Initial Release

### Added
- Automatic Git commit message generation using AI
- Support for multiple LLM providers via LiteLLM
- Conventional Commits format support
- Interactive commit message approval workflow
- Semantic diff analysis
- Breaking change detection
- Rich terminal UI with formatted output
- Comprehensive logging and error handling
- Project-level configuration via `config.json`
- Environment variable configuration support

### Technologies
- Python 3.10+
- LiteLLM for universal LLM access
- Rich for terminal UI
- Unidiff for diff parsing
- Setuptools for packaging