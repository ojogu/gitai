# main.py
import sys
from gitai.cli.cli import main
from gitai.utils.global_config import (
    init_config_interactive, show_config, update_config,
    load_global_config, get_config_path
)
from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()


def is_first_time_user() -> bool:
    """Check if this is a first-time user (no valid configuration)."""
    config_path = get_config_path()
    if not config_path.exists():
        return True
    config = load_global_config()
    return not config.get("api_key")


def print_help():
    """Display help information."""
    console.print()
    console.print(Panel(
        "[bold blue]GitAI[/bold blue] - AI-powered Git commit message generator\n\n"
        "[bold]Usage:[/bold] gitai [command]\n\n"
        "[bold]Commands:[/bold]\n"
        "  [cyan]init[/cyan]     Initialize or update GitAI configuration\n"
        "  [cyan]config[/cyan]   View or update configuration settings\n"
        "  [cyan](none)[/cyan]   Generate a commit message from staged changes\n\n"
        "[bold]Examples:[/bold]\n"
        "  gitai                Generate a commit message\n"
        "  gitai init           Interactive configuration setup\n"
        "  gitai config         View current configuration\n"
        "  gitai config model=gemini/gemini-1.5-pro   Update model\n\n"
        "[dim]For more information, see: https://github.com/ojogu/gitai[/dim]",
        box=box.ROUNDED,
        border_style="blue"
    ))
    console.print()


def handle_init():
    """Handle the 'init' command."""
    init_config_interactive()


def handle_config(args):
    """Handle the 'config' command."""
    if args:
        # Update mode: gitai config key=value
        arg = " ".join(args)
        if "=" in arg:
            key, value = arg.split("=", 1)
            update_config(key.strip(), value.strip())
        else:
            console.print("[red]✗ Invalid format. Use: gitai config key=value[/red]")
    else:
        # Show mode: gitai config
        show_config()


def main_entry():
    """Main entry point that handles subcommands."""
    args = sys.argv[1:]
    
    if not args or args[0] in ("help", "--help", "-h"):
        print_help()
        return
    
    command = args[0].lower()
    
    if command == "init":
        handle_init()
    elif command == "config":
        handle_config(args[1:])
    else:
        # Check if first-time user (no valid config) - auto-run init
        if is_first_time_user():
            console.print()
            console.print(Panel(
                "[yellow]⚠ Welcome to GitAI![/yellow]\n\n"
                "It looks like this is your first time. Let's set up your configuration.\n\n"
                "[dim]You can also run 'gitai init' manually at any time.[/dim]",
                box=box.ROUNDED,
                border_style="yellow"
            ))
            console.print()
            init_config_interactive()
        
        # Run the main commit generation
        main()


if __name__ == "__main__":
    main_entry()
