# GitAI

## Overview

You know how sometimes writing a good Git commit message feels like a chore, especially when you've got a bunch of small changes? This tool, GitAI, takes the pain out of it by automatically generating clear, concise commit messages for you based on your staged changes. It looks at what you've actually changed and suggests a message that truly reflects your work, so you can focus on coding.

## Features

Here's what GitAI can do for you:

*   **Intelligent Commit Message Generation**: Automatically creates relevant commit messages by analyzing your staged Git changes.
*   **Semantic Diff Analysis**: Goes beyond raw diffs to understand the high-level meaning of your changes, identifying new functions, class updates, dependency changes, and more.
*   **Conventional Commits Support**: Generate messages in the widely adopted Conventional Commits format (`type(scope): message`), helping keep your commit history clean and parseable.
*   **Configurable Output**: Customize the commit message style, title length, and whether to include a body in the generated message.
*   **Breaking Change Detection**: Offers hints for potential breaking changes, prompting you to review and confirm impact on public APIs.
*   **Flexible LLM Integration**: Uses `litellm` to support various large language models (LLMs) for message generation, allowing you to switch providers easily.
*   **Interactive Workflow**: Provides options to accept, reject, or retry message generation if the initial suggestion isn't quite right.
*   **Automatic Committing**: Option to automatically commit with the generated message, streamlining your workflow.

## Getting Started

Let's get you set up to use GitAI.

### Installation

To use GitAI globally without interfering with your system's Python packages, use one of the following methods:

#### Option 1: Using uv (Recommended - Fastest)
`uv` is an extremely fast Python package manager that handles tool isolation automatically.

```bash
# Install GitAI as a global tool
uv tool install ojogu-gitai

# It is now available globally
gitai --help
```

#### Option 2: Using pipx (Standard for CLI Tools)
`pipx` installs the package into an isolated environment and automatically adds the executable to your `$PATH`.

```bash
# Install pipx if you haven't already
sudo apt install pipx && pipx ensurepath

# Install GitAI
pipx install ojogu-gitai
```

#### Option 3: Using pip (Legacy/Global)
If you are on an older system or inside a container where PEP 668 isn't enforced, you can use standard pip. Note: On modern Linux, this may require the `--break-system-packages` flag.

```bash
pip install ojogu-gitai
```

#### Option 4: Install from Source (For Development)
If you want to contribute or modify the source code:

```bash
git clone https://github.com/ojogu/gitai.git
cd gitai
pip install -e .
```

**Requirements**: Python 3.10 or newer is required.

### Why Use uv or pipx?

By recommending `uv` or `pipx`, you're solving two problems for your users:

- **No Manual Activation**: The user doesn't need to run `source venv/bin/activate`. The tool just works like `ls` or `git`.
- **No Dependency Hell**: If GitAI requires pydantic v2 but their project uses pydantic v1, there won't be a conflict because GitAI's dependencies are hidden away in its own private folder.

### Verifying Installation

After installation, you can verify GitAI is working by running:

```bash
which gitai
```

This will show you exactly where the isolated executable lives (usually `~/.local/bin/gitai`).

### Environment Variables

Before you can run GitAI, you'll need to set up your AI provider API key and chosen LLM model. Create a `.env` file in the root of your project (where `pyproject.toml` is) with the following variables:

```example
AI_KEY=your_api_key_here
LLM_MODEL=gemini/gemini-2.5-flash # Or your preferred model like "openai/gpt-4o"
```

*   `AI_KEY`: Your API key for the chosen LLM provider (e.g., Google Gemini, OpenAI).
*   `LLM_MODEL`: The identifier for the LLM model you want to use. `litellm` supports many, so pick one that fits your needs. Examples include `gemini/gemini-1.5-flash`, `openai/gpt-3.5-turbo`, etc.

> 💡 **Tip**: For detailed instructions on configuring different AI providers (Google Gemini, OpenAI, Anthropic, Groq, etc.), see the [AI Model Configuration Guide](docs/AI_MODEL_CONFIGURATION.md).

You can also create a `config.json` file to customize GitAI's behavior:

```json
{
  "style": "conventional",
  "max_title_length": 72,
  "include_body": true,
  "custom_instructions": "",
  "auto_commit": false,
  "retry":3
}
```

## Usage

Using GitAI is pretty straightforward. Just make your changes, stage them, and let GitAI suggest a commit message.

1.  **Stage Your Changes**:
    Just like you normally would, add your changes to the staging area:
    ```bash
    git add .
    ```

2.  **Generate a Commit Message**:
    Now, run GitAI from your terminal. It'll analyze your staged changes and suggest a message.
    ```bash
    gitai
    ```

    GitAI will print a suggested commit message and ask you if you'd like to use it. If you're happy, type `y` and press Enter. If not, you can type `n` to get another suggestion (up to 3 retries by default) or exit.

    ```
    🔍 Generating commit message...

    ✨ Suggested Commit Message:

    feat(cli): add interactive retry for commit messages

    - Implemented a retry mechanism for generating commit messages.
    - Allows users to request new messages if the initial suggestion is not suitable.
    - Configurable `retry` count in `config.json`.

    --------------------------------------------------
    👉 Use this commit message? (y/n): y
    ✅ Commit created.
    ```

3.  **Automatic Committing**:
    If you've set `"auto_commit": true` in your `config.json`, GitAI will automatically commit with the generated message without asking for confirmation.

## Logging & Error Handling

GitAI includes comprehensive logging and error handling with a focus on security:

- **Secure Logging**: All logs are automatically sanitized to prevent sensitive data (API keys, passwords, tokens) from being written to log files.
- **Custom Exceptions**: Clear, actionable error messages with suggestions for resolution.
- **Debug-Friendly**: Detailed logs are stored in the `logs/` directory for troubleshooting.

For detailed information on configuring logging, understanding error types, and best practices, see the [Logging and Error Handling Guide](docs/LOGGING_AND_ERROR_HANDLING.md).

## Technologies Used

| Technology | Description | Link |
| :--------- | :---------- | :--- |
| **Python** | The primary programming language used for the project. | [Python](https://www.python.org/) |
| **Unidiff** | Library for parsing and working with unified diff output. | [Unidiff](https://github.com/matiasb/unidiff) |
| **LiteLLM** | A universal API for all Large Language Models, simplifying AI integration. | [LiteLLM](https://litellm.ai/) |
| **Rich** | A Python library for rich text and beautiful formatting in the terminal. | [Rich](https://github.com/Textualize/rich) |
| **Setuptools** | Standard library for packaging Python projects. | [Setuptools](https://setuptools.pypa.io/en/latest/) |

## Contributing

We'd love for you to contribute to GitAI! If you have ideas for new features, find a bug, or want to improve the codebase, please feel free to:

1.  **Fork the Repository**: Start by forking the project to your own GitHub account.
2.  **Create a New Branch**: Make a new branch for your changes (e.g., `feature/add-new-llm`, `bugfix/parsing-issue`).
3.  **Implement Your Changes**: Write your code, ensuring it follows the existing style and conventions.
4.  **Write Tests**: If applicable, add or update tests to cover your changes.
5.  **Submit a Pull Request**: Open a pull request against the `main` branch of this repository. Please provide a clear description of your changes and why they're beneficial.

## Author Info

*   **LinkedIn**: [Precious Ojogu](https://www.linkedin.com/in/precious-ojogu/)
*   **X (formerly Twitter)**: [@_Ojogu](https://x.com/_Ojogu)

---

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)
[![Made with LiteLLM](https://img.shields.io/badge/Made%20with-LiteLLM-purple)](https://litellm.ai/)

[![Readme was generated by Dokugen](https://img.shields.io/badge/Readme%20was%20generated%20by-Dokugen-brightgreen)](https://www.npmjs.com/package/dokugen)