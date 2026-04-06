# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-04-05

### Added
- **Global Configuration System**: Configuration now stored in `~/.config/gitai/config.json` for persistent settings across projects
- **New CLI Commands**:
  - `gitai init` - Interactive configuration setup with arrow key navigation
  - `gitai config` - View current configuration (API key masked for security)
  - `gitai config key=value` - Update specific configuration settings
  - `gitai help` - Display help information and usage examples
- **Auto-Push Configuration**: New `auto_push` option to automatically push commits after creation
- **Enhanced Interactive Setup**:
  - Arrow key navigation for list selections (▶ indicator)
  - Yes/No toggle with arrow keys for boolean options
  - Basic settings (API key, model, style) - required
  - Advanced settings (max_title_length, include_body, auto_commit, auto_push, retry, llm_max_tokens, verbose_log, custom_instructions) - optional
- **Auto-Init on First Run**: When no configuration exists, `gitai` automatically prompts for setup
- **Configuration Precedence**: Environment variables > Global config > Remote default (GitHub Gist) > Default values
- **Remote Default API Key**: Fetch default API key from maintainer's GitHub Gist for out-of-box functionality
- **API Key Masking**: Sensitive API keys are masked in configuration output (e.g., `AIza••••••••chyg`)
- **New Configuration Options**:
  - `llm_max_tokens` - Maximum output tokens for commit messages (default: 2048)
  - `verbose_log` - Enable verbose logging (default: false)

### Changed
- **Entry Point**: Updated from `gitai.cli.cli:main` to `gitai.main:main_entry` for command handling
- **Documentation**: Updated README.md with comprehensive installation methods (uv, pipx, pip, source)
- **Author Info**: Updated with real social media links (LinkedIn, X)
- **Default Values**: All boolean options default to `false` except `include_body` (default: `true`)
- **Environment Variable**: Renamed `AI_KEY` to `API_KEY` for consistency

### Fixed
- **.env Parsing**: Removed inline comments that were causing environment variable parsing issues
- **Configuration Loading**: Fixed LLM_MODEL environment variable not being loaded correctly
- **Command Handling**: Fixed `gitai` without arguments showing help instead of generating commit messages

### Technical Changes
- Added `src/gitai/utils/global_config.py` module for global configuration management
- Added `fetch_default_api_key()` function to fetch remote default API key from GitHub Gist
- Added `select_from_list()` function for arrow key navigation in lists
- Added `ask_yes_no()` function for Yes/No toggle with arrow keys
- Added `mask_api_key()` function for secure API key display
- Added `clear_screen()` function for terminal screen clearing
- Updated `src/gitai/core/llm.py` to fall back to global config when env vars are not set
- Updated `pyproject.toml` entry point to use new command handler
- Updated `.env.example` with new environment variables

---

## [0.1.0] - Initial Release

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