# global_config.py
#
# This module manages GitAI's global configuration stored in ~/.config/gitai/config.json
# It provides a fallback mechanism when environment variables are not set.

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box

console = Console()

# Configuration paths
CONFIG_DIR = Path.home() / ".config" / "gitai"
CONFIG_FILE = CONFIG_DIR / "config.json"
FALLBACK_CONFIG = Path.home() / ".gitai.json"

# Remote default API key URL (GitHub Gist)
DEFAULT_API_KEY_URL = "https://gist.githubusercontent.com/ojogu/0cf0d416b778d3bc28794dc5a6d18be9/raw/9834d2a69ef80fe3077ca45ef5bb71a995949b59/config.json"

# Default configuration values
DEFAULT_CONFIG = {
    "api_key": "",
    "model": "gemini/gemini-2.5-flash",
    "style": "conventional",
    "max_title_length": 72,
    "include_body": True,
    "custom_instructions": "",
    "auto_commit": False,
    "auto_push": False,
    "retry": 3,
    "llm_max_tokens": 2048,
    "verbose_log": False
}


def get_config_path() -> Path:
    """Get the path to the config file, checking fallback if needed."""
    if CONFIG_FILE.exists():
        return CONFIG_FILE
    elif FALLBACK_CONFIG.exists():
        return FALLBACK_CONFIG
    return CONFIG_FILE


def ensure_config_dir() -> None:
    """Ensure the config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_global_config() -> Dict[str, Any]:
    """
    Load the global configuration from file.
    
    Returns:
        Dict containing the configuration, or default values if not found.
    """
    config_path = get_config_path()
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return {**DEFAULT_CONFIG, **config}
        except (json.JSONDecodeError, IOError) as e:
            console.print(f"[yellow]Warning: Could not parse config file: {e}[/yellow]")
            return DEFAULT_CONFIG.copy()
    
    return DEFAULT_CONFIG.copy()


def save_global_config(config: Dict[str, Any]) -> None:
    """
    Save the configuration to the global config file.
    
    Args:
        config: The configuration dictionary to save.
    """
    ensure_config_dir()
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
    
    console.print(f"[green]✓ Configuration saved to {CONFIG_FILE}[/green]")


def fetch_default_api_key() -> str:
    """
    Fetch default API key from remote URL (GitHub Gist).
    
    Returns:
        The API key if fetch successful, empty string otherwise.
    """
    try:
        response = requests.get(DEFAULT_API_KEY_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("api_key", "")
    except Exception:
        return ""


def get_effective_config() -> Dict[str, Any]:
    """
    Get the effective configuration, with environment variables taking precedence.
    
    This function checks:
    1. Environment variables (API_KEY, LLM_MODEL, etc.)
    2. Global config file (~/.config/gitai/config.json)
    3. Remote default API key (GitHub Gist)
    4. Default values
    
    Returns:
        Dict containing the effective configuration.
    """
    # Start with global config
    config = load_global_config()
    
    # Fetch remote default API key if local config doesn't have one
    if not config.get("api_key"):
        remote_key = fetch_default_api_key()
        if remote_key:
            config["api_key"] = remote_key
    
    # Environment variables take precedence
    env_mappings = {
        "API_KEY": "api_key",
        "LLM_MODEL": "model",
        "LLM_MAX_TOKENS": "llm_max_tokens",
        "VERBOSE_LOG": "verbose_log",
    }
    
    for env_var, config_key in env_mappings.items():
        env_value = os.getenv(env_var)
        if env_value:
            # Type conversion for known keys
            if config_key in ("llm_max_tokens",):
                try:
                    env_value = int(env_value)
                except ValueError:
                    continue
            elif config_key in ("verbose_log",):
                env_value = env_value.lower() in ("true", "yes", "1")
            config[config_key] = env_value
    
    return config


def clear_screen():
    """Clear the terminal screen."""
    import os
    os.system('clear' if os.name == 'posix' else 'cls')


def mask_api_key(api_key: str) -> str:
    """
    Mask an API key for display, showing only first 3 and last 3 characters.
    
    Args:
        api_key: The API key to mask.
    
    Returns:
        Masked API key string (e.g., "AIz*********hyg")
    """
    if not api_key or len(api_key) <= 6:
        return "•" * 8
    return api_key[:3] + "*" * (len(api_key) - 6) + api_key[-3:]


def select_from_list(options: list, default: int = 0, title: str = "") -> int:
    """
    Interactive list selection using arrow keys.
    
    Args:
        options: List of option strings to display.
        default: Default selected index.
        title: Optional title for the selection.
    
    Returns:
        The index of the selected option.
    """
    selected = default
    
    while True:
        clear_screen()
        if title:
            console.print(f"[dim]{title}[/dim]\n")
        
        for i, option in enumerate(options):
            if i == selected:
                console.print(f"  [green]▶ {option}[/green]")
            else:
                console.print(f"  ○ {option}")
        
        console.print("\n[dim]Use ↑↓ to navigate, Enter to select[/dim]")
        
        # Read a single character
        try:
            import sys
            import tty
            import termios
            
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            
            if ch == '\x1b':
                # Escape sequence
                ch2 = sys.stdin.read(1)
                ch3 = sys.stdin.read(1)
                if ch2 == '[':
                    if ch3 == 'A':  # Up arrow
                        selected = (selected - 1) % len(options)
                    elif ch3 == 'B':  # Down arrow
                        selected = (selected + 1) % len(options)
            elif ch == '\r' or ch == '\n':  # Enter
                return selected
        except (ValueError, OSError):
            # Fallback for non-terminal input
            return selected


def ask_yes_no(question: str, default: bool = False) -> bool:
    """
    Ask a yes/no question with arrow key navigation.
    
    Args:
        question: The question to ask.
        default: Default answer (True for Yes, False for No).
    
    Returns:
        True for Yes, False for No.
    """
    selected = 0 if default else 1
    
    while True:
        clear_screen()
        console.print(f"[dim]{question}[/dim]\n")
        
        options = ["Yes", "No"]
        for i, option in enumerate(options):
            if i == selected:
                console.print(f"  [green]▶ {option}[/green]")
            else:
                console.print(f"  ○ {option}")
        
        console.print("\n[dim]Use ↑↓ to navigate, Enter to select[/dim]")
        
        try:
            import sys
            import tty
            import termios
            
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            
            if ch == '\x1b':
                ch2 = sys.stdin.read(1)
                ch3 = sys.stdin.read(1)
                if ch2 == '[':
                    if ch3 == 'A':  # Up arrow
                        selected = (selected - 1) % 2
                    elif ch3 == 'B':  # Down arrow
                        selected = (selected + 1) % 2
            elif ch == '\r' or ch == '\n':  # Enter
                return selected == 0
        except (ValueError, OSError):
            return selected == 0


def init_config_interactive() -> Dict[str, Any]:
    """
    Interactive configuration setup with basic and advanced settings.
    
    Returns:
        The configured dictionary after user input.
    """
    console.print()
    console.print(Panel(
        "[bold blue]GitAI Configuration Setup[/bold blue]\n\n"
        "Configure your AI provider and preferences.\n"
        "Use arrow keys to navigate and select options.",
        box=box.ROUNDED,
        border_style="blue"
    ))
    console.print()
    
    config = load_global_config()
    
    # ========== BASIC SETTINGS ==========
    console.print(Panel("[bold]Basic Settings[/bold]", border_style="cyan"))
    console.print()
    
    # API Key
    console.print("[dim]Your API key for the LLM provider (e.g., Google Gemini, OpenAI)[/dim]")
    console.print("[dim]Press Enter to use the default key from GitHub Gist.[/dim]")
    current_key = config.get("api_key", "")
    
    api_key = Prompt.ask(
        "API Key",
        default=current_key if current_key else "",
        password=True
    )
    
    # If user presses Enter (empty), fetch from Gist
    if not api_key:
        console.print("[dim]Using default key...[/dim]")
        remote_key = fetch_default_api_key()
        if remote_key:
            api_key = remote_key
            console.print(f"[green]✓ Default key loaded successfully[/green]")
        else:
            console.print("[red]✗ Failed to fetch default key[/red]")
            console.print("[yellow]⚠ Please provide your API key manually[/yellow]")
            # Ask user to provide API key manually
            api_key = Prompt.ask(
                "API Key",
                password=True
            )
            if not api_key:
                console.print("[red]✗ API key is required[/red]")
                return config
    
    config["api_key"] = api_key
    
    # Track if we're using the default Gemini key
    using_default_key = not current_key and api_key
    
    # Model selection with arrow keys
    console.print()
    model_options = [
        "gemini/gemini-2.5-flash (fast, recommended)",
        "gemini/gemini-1.5-pro (more capable)",
        "openai/gpt-4o",
        "Custom (enter manually)"
    ]
    default_model_idx = 0
    current_model = config.get("model", "")
    if current_model == "gemini/gemini-1.5-pro":
        default_model_idx = 1
    elif current_model == "openai/gpt-4o":
        default_model_idx = 2
    elif current_model and not current_model.startswith("gemini/") and not current_model.startswith("openai/"):
        default_model_idx = 3
    
    console.print("[dim]Choose your preferred model:[/dim]")
    model_idx = select_from_list(model_options, default=default_model_idx)
    
    if model_idx == 3:  # Custom
        custom_model = Prompt.ask("Enter custom model", default=current_model)
        config["model"] = custom_model
    else:
        config["model"] = model_options[model_idx].split(" (")[0]
    
    # Model compatibility check when using default Gemini key
    if using_default_key:
        selected_model = config["model"]
        # Check if the selected model is Gemini-compatible
        if not selected_model.startswith("gemini/"):
            console.print()
            console.print("[yellow]⚠ The default API key is for Google Gemini models only.[/yellow]")
            console.print("[yellow]  Your selected model is not compatible with this key.[/yellow]")
            console.print()
            
            # Offer options using arrow key selection
            compatibility_options = [
                f"Switch to gemini/gemini-2.5-flash (recommended)",
                f"Keep {selected_model} and provide a different API key"
            ]
            
            console.print("[dim]What would you like to do?[/dim]")
            choice_idx = select_from_list(
                compatibility_options, 
                default=0,
                title="Model Compatibility"
            )
            
            if choice_idx == 0:
                # Switch to Gemini model
                config["model"] = "gemini/gemini-2.5-flash"
                console.print(f"[green]✓ Model switched to gemini/gemini-2.5-flash[/green]")
            else:
                # User wants to keep their model and provide a different API key
                console.print()
                console.print(f"[dim]Please provide your API key for {selected_model}:[/dim]")
                new_api_key = Prompt.ask(
                    "API Key",
                    password=True
                )
                if new_api_key:
                    config["api_key"] = new_api_key
                    console.print(f"[green]✓ API key updated[/green]")
                else:
                    console.print("[yellow]⚠ No API key provided. Using default Gemini key.[/yellow]")
                    config["model"] = "gemini/gemini-2.5-flash"
                    console.print(f"[green]✓ Model switched to gemini/gemini-2.5-flash[/green]")
    
    # Commit style with arrow keys
    console.print()
    style_options = [
        "conventional (feat, fix, refactor, etc.)",
        "simple (plain text)"
    ]
    default_style_idx = 0 if config.get("style", "conventional") == "conventional" else 1
    
    console.print("[dim]Commit message style:[/dim]")
    style_idx = select_from_list(style_options, default=default_style_idx)
    config["style"] = "conventional" if style_idx == 0 else "simple"
    
    # Ask if user wants to configure advanced settings
    console.print()
    console.print("[dim]Would you like to configure advanced settings?[/dim]")
    show_advanced = ask_yes_no("Configure advanced settings?", default=False)
    
    if show_advanced:
        # ========== ADVANCED SETTINGS ==========
        console.print()
        console.print(Panel("[bold]Advanced Settings[/bold]", border_style="cyan"))
        console.print()
        
        # Max title length
        max_title = Prompt.ask(
            "Maximum commit title length",
            default=str(config.get("max_title_length", 72))
        )
        config["max_title_length"] = int(max_title)
        
        # Include body
        console.print()
        config["include_body"] = ask_yes_no(
            "Include commit body in generated messages?",
            default=config.get("include_body", True)
        )
        
        # Auto commit
        console.print()
        config["auto_commit"] = ask_yes_no(
            "Automatically commit without confirmation?",
            default=config.get("auto_commit", False)
        )
        
        # Auto push
        console.print()
        config["auto_push"] = ask_yes_no(
            "Automatically push after commit?",
            default=config.get("auto_push", False)
        )
        
        # Retry count
        console.print()
        retry = Prompt.ask(
            "Number of retry attempts for generation",
            default=str(config.get("retry", 3))
        )
        config["retry"] = int(retry)
        
        # Max tokens
        console.print()
        max_tokens = Prompt.ask(
            "Maximum output tokens for commit messages",
            default=str(config.get("llm_max_tokens", 2048))
        )
        config["llm_max_tokens"] = int(max_tokens)
        
        # Verbose logging
        console.print()
        config["verbose_log"] = ask_yes_no(
            "Enable verbose logging?",
            default=config.get("verbose_log", False)
        )
        
        # Custom instructions
        console.print()
        console.print("[dim]Custom instructions for the AI (optional, press Enter to skip)[/dim]")
        custom_instructions = Prompt.ask(
            "Custom instructions",
            default=config.get("custom_instructions", "")
        )
        config["custom_instructions"] = custom_instructions
    
    # Save configuration
    console.print()
    save_global_config(config)
    
    # Show summary
    console.print()
    summary_lines = [
        f"  [bold]Model:[/bold] [cyan]{config['model']}[/cyan]",
        f"  [bold]Style:[/bold] [cyan]{config['style']}[/cyan]",
    ]
    if show_advanced:
        summary_lines.extend([
            f"  [bold]Max Title:[/bold] [cyan]{config['max_title_length']}[/cyan] chars",
            f"  [bold]Include Body:[/bold] [cyan]{'Yes' if config['include_body'] else 'No'}[/cyan]",
            f"  [bold]Auto Commit:[/bold] [cyan]{'Yes' if config['auto_commit'] else 'No'}[/cyan]",
            f"  [bold]Auto Push:[/bold] [cyan]{'Yes' if config['auto_push'] else 'No'}[/cyan]",
            f"  [bold]Retry:[/bold] [cyan]{config['retry']}[/cyan]",
        ])
    summary_lines.append(f"  [dim]Config: {CONFIG_FILE}[/dim]")
    
    console.print(Panel(
        f"[green]✓ Configuration initialized![/green]\n\n" + "\n".join(summary_lines),
        box=box.ROUNDED,
        border_style="green"
    ))
    
    return config


def show_config() -> None:
    """Display the current configuration in a formatted way."""
    config = get_effective_config()
    
    # Mask API key for display
    api_key = config.get("api_key", "")
    if api_key:
        masked_key = api_key[:4] + "•" * min(8, len(api_key) - 4) + api_key[-4:] if len(api_key) > 8 else "•" * 8
    else:
        masked_key = "[yellow]Not set[/yellow]"
    
    # Build config display
    config_lines = [
        f"[bold]API Key:[/bold]        {masked_key}",
        f"[bold]Model:[/bold]          [cyan]{config.get('model', 'Not set')}[/cyan]",
        f"[bold]Style:[/bold]          [cyan]{config.get('style', 'conventional')}[/cyan]",
        f"[bold]Max Title:[/bold]      [cyan]{config.get('max_title_length', 72)}[/cyan] chars",
        f"[bold]Max Tokens:[/bold]     [cyan]{config.get('llm_max_tokens', 2048)}[/cyan]",
        f"[bold]Include Body:[/bold]   [cyan]{'Yes' if config.get('include_body', True) else 'No'}[/cyan]",
        f"[bold]Auto Commit:[/bold]    [cyan]{'Yes' if config.get('auto_commit', False) else 'No'}[/cyan]",
        f"[bold]Auto Push:[/bold]      [cyan]{'Yes' if config.get('auto_push', False) else 'No'}[/cyan]",
        f"[bold]Verbose Log:[/bold]    [cyan]{'Yes' if config.get('verbose_log', False) else 'No'}[/cyan]",
        f"[bold]Retry:[/bold]          [cyan]{config.get('retry', 3)}[/cyan]",
    ]
    
    if config.get('custom_instructions'):
        config_lines.append(f"[bold]Custom:[/bold]         [dim]{config['custom_instructions'][:50]}...[/dim]")
    
    config_lines.append(f"\n[dim]Config file: {get_config_path()}[/dim]")
    
    console.print()
    console.print(Panel(
        "\n".join(config_lines),
        title="[bold blue]GitAI Configuration[/bold blue]",
        box=box.ROUNDED,
        border_style="blue"
    ))


def update_config(key: str, value: str) -> None:
    """
    Update a specific configuration key.
    
    Args:
        key: The configuration key to update.
        value: The new value.
    """
    config = load_global_config()
    
    # Type conversion for known keys
    if key in ("max_title_length", "retry", "llm_max_tokens"):
        value = int(value)
    elif key in ("include_body", "auto_commit", "auto_push", "verbose_log"):
        value = value.lower() in ("true", "yes", "1")
    
    if key not in DEFAULT_CONFIG:
        console.print(f"[red]✗ Unknown configuration key: {key}[/red]")
        console.print(f"  Valid keys: {', '.join(DEFAULT_CONFIG.keys())}")
        return
    
    config[key] = value
    save_global_config(config)
    
    console.print(f"[green]✓ Updated {key} to {value}[/green]")