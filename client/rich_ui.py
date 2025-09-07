from __future__ import annotations

from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table


class RichUI:
    """Minimal Rich UI components preserved from v1 style.

    Phase 1: Only what's needed for the status command.
    """

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()

    def show_banner(self, subtitle: str = "") -> None:
        title = Text("MeetingScribe v2 (Client)", style="bold blue")
        if subtitle:
            title.append(f"\n{subtitle}", style="dim")
        self.console.print(Panel(title, border_style="blue"))

    def show_status(self, message: str, style: str = "blue") -> None:
        self.console.print(f"[{style}]• {message}[/{style}]")

    def show_success(self, message: str) -> None:
        self.console.print(f"[green]✓ {message}[/green]")

    def show_error(self, message: str) -> None:
        self.console.print(f"[red]✗ {message}[/red]")

    def kv_table(self, title: str, data: dict[str, str]) -> None:
        table = Table(title=title, show_header=False, expand=True)
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Value")
        for k, v in data.items():
            table.add_row(str(k), str(v))
        self.console.print(table)

