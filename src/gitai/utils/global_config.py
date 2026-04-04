# global_config.py
#
# This module manages GitAI's global configuration stored in ~/.config/gitai/config.json
# It provides a fallback mechanism when environment variables are not set.

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box

console = Console()

# Configuration paths
CONFIG_DIR = Path.home() / ".config" / "gitai"
CONFIG_FILE = CONFIG_DIR / "config.json"
FALLBACK_CONFIG = Path.home() / ".gitai.json"

# Default configuration values
DEFAULT_CONFIG = {
    "api_key": "",
    "model": "gemini/gemini-2.5-flash",
    "style": "conventional",
    "max_title_length": 72,
    "include_body": True,
    "custom_instructions": "",
    "auto_commit": False,
    "retry": 3
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


def get_effective_config() -> Dict[str, Any]:
    """
    Get the effective configuration, with environment variables taking precedence.
    
    This function checks:
    1. Environment variables (AI_KEY, LLM_MODEL, etc.)
    2. Global config file (~/.config/gitai/config.json)
    3. Default values
    
    Returns:
        Dict containing the effective configuration.
    """
    # Start with global config
    config = load_global_config()
    
    # Environment variables take precedence
    env_mappings = {
        "AI_KEY": "api_key",
        "LLM_MODEL": "model",
    }
    
    for env_var, config_key in env_mappings.items():
        env_value = os.getenv(env_var)
        if env_value:
            config[config_key] = env_value
    
    return config


def init_config_interactive() -> Dict[str, Any]:
    """
    Interactive configuration setup.
    
    Returns:
        The configured dictionary after user input.
    """
    console.print()
    console.print(Panel(
        "[bold blue]GitAI Configuration Setup[/bold blue]\n\n"
        "Configure your AI provider and preferences.\n"
        "Press Enter to use default values (shown in brackets).",
        box=box.ROUNDED,
        border_style="blue"
    ))
    console.print()
    
    config = load_global_config()
    
    # API Key
    console.print("[dim]Your API key for the LLM provider (e.g., Google Gemini, OpenAI)[/dim]")
    api_key = Prompt.ask(
        "API Key",
        default=config.get("api_key", ""),
        password=True
    )
    config["api_key"] = api_key
    
    # Model selection
    console.print()
    console.print("[dim]Choose your preferred model:[/dim]")
    console.print("  [cyan]1[/cyan]) gemini/gemini-2.5-flash (fast, recommended)")
    console.print("  [cyan]2[/cyan]) gemini/gemini-1.5-pro (more capable)")
    console.print("  [cyan]3[/cyan]) openai/gpt-4o")
    console.print("  [cyan]4[/cyan]) Custom (enter manually)")
    
    model_choice = Prompt.ask("Model", default="1")
    model_map = {
        "1": "gemini/gemini-2.5-flash",
        "2": "gemini/gemini-1.5-pro",
        "3": "openai/gpt-4o",
    }
    
    if model_choice in model_map:
        config["model"] = model_map[model_choice]
    else:
        custom_model = Prompt.ask("Enter custom model", default=config.get("model", ""))
        config["model"] = custom_model
    
    # Commit style
    console.print()
    console.print("[dim]Commit message style:[/dim]")
    console.print("  [cyan]1[/cyan]) conventional (feat, fix, refactor, etc.)")
    console.print("  [cyan]2[/cyan]) simple (plain text)")
    
    style_choice = Prompt.ask("Style", default="1")
    config["style"] = "conventional" if style_choice == "1" else "simple"
    
    # Save configuration
    console.print()
    save_global_config(config)
    
    # Show summary
    console.print()
    console.print(Panel(
        f"[green]✓ Configuration initialized![/green]\n\n"
        f"  Model: [cyan]{config['model']}[/cyan]\n"
        f"  Style: [cyan]{config['style']}[/cyan]\n"
        f"  Config: [dim]{CONFIG_FILE}[/dim]",
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
        f"[bold]API Key:[/bold]     {masked_key}",
        f"[bold]Model:[/bold]       [cyan]{config.get('model', 'Not set')}[/cyan]",
        f"[bold]Style:[/bold]       [cyan]{config.get('style', 'conventional')}[/cyan]",
        f"[bold]Max Title:[/bold]   [cyan]{config.get('max_title_length', 72)}[/cyan] chars",
        f"[bold]Include Body:[/bold] [cyan]{'Yes' if config.get('include_body', True) else 'No'}[/cyan]",
        f"[bold]Auto Commit:[/bold] [cyan]{'Yes' if config.get('auto_commit', False) else 'No'}[/cyan]",
        f"[bold]Retry:[/bold]       [cyan]{config.get('retry', 3)}[/cyan]",
    ]
    
    if config.get('custom_instructions'):
        config_lines.append(f"[bold]Custom:[/bold]      [dim]{config['custom_instructions'][:50]}...[/dim]")
    
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
    if key in ("max_title_length", "retry"):
        value = int(value)
    elif key in ("include_body", "auto_commit"):
        value = value.lower() in ("true", "yes", "1")
    
    if key not in DEFAULT_CONFIG:
        console.print(f"[red]✗ Unknown configuration key: {key}[/red]")
        console.print(f"  Valid keys: {', '.join(DEFAULT_CONFIG.keys())}")
        return
    
    config[key] = value
    save_global_config(config)
    
    console.print(f"[green]✓ Updated {key} to {value}[/green]")