"""The tuivisu Textual application shell.

v0.1: connects to the PLC's OPC UA server, shows connection state, and lists
browsable variables. Navigation: arrow keys. Exit: q (the only shortcut).
"""

from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Footer, Header, Static

from tuivisu import __version__
from tuivisu.plc import PlcConfig, PlcConnection


class TuivisuApp(App[None]):
    """Terminal view of a CODESYS PLC."""

    TITLE = f"tuivisu {__version__}"

    BINDINGS: ClassVar = [
        Binding("q", "quit", "Quit"),
    ]

    CSS = """
    #status {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, config: PlcConfig) -> None:
        super().__init__()
        self.plc = PlcConnection(config)

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("connecting...", id="status")
            yield DataTable(id="variables", cursor_type="row")
        yield Footer()

    async def on_mount(self) -> None:
        table = self.query_one("#variables", DataTable)
        table.add_columns("Variable", "Value", "Type", "Access")
        self.run_worker(self._connect_and_load(), exclusive=True)

    async def _connect_and_load(self) -> None:
        status = self.query_one("#status", Static)
        try:
            await self.plc.connect()
        except Exception as exc:  # show every failure in the UI
            status.update(f"connection failed: {type(exc).__name__}: {exc}")
            return
        status.update(f"connected to {self.plc.config.url} - browsing...")
        variables = await self.plc.browse_variables()
        table = self.query_one("#variables", DataTable)
        for var in variables:
            access = "rw" if var.writable else "r"
            table.add_row(var.browse_path, repr(var.value), var.data_type, access, key=var.node_id)
        status.update(f"connected to {self.plc.config.url} - {len(variables)} variables")

    async def on_unmount(self) -> None:
        await self.plc.disconnect()
