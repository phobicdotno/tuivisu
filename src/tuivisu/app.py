"""The tuivisu Textual application.

Shows the PLC's published variables (the set you curate via the Symbol
Configuration in the IDE), keeps their values live via an OPC UA subscription,
and lets you edit writable scalar setpoints. Navigation: arrow keys. Edit the
selected row: Enter. Exit: q.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any, ClassVar

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static

from tuivisu import __version__
from tuivisu.edit import coerce, is_editable
from tuivisu.plc import PlcConfig, PlcConnection, VariableInfo


class _SubHandler:
    """asyncua data-change callback that forwards updates to the app."""

    def __init__(self, app: TuivisuApp) -> None:
        self._app = app

    def datachange_notification(self, node: Any, val: Any, data: Any) -> None:
        # Runs on the asyncua task in the same event loop; hop to the app
        # thread-safely so the DataTable is touched from the UI context.
        self._app.call_from_thread(self._app.on_value_change, node.nodeid.to_string(), val)


class EditScreen(ModalScreen[str | None]):
    """Prompt for a new value, then confirm before writing to the PLC."""

    CSS = """
    EditScreen { align: center middle; }
    #box {
        width: 70; height: auto; padding: 1 2;
        background: $surface; border: thick $warning;
    }
    #prompt { margin-bottom: 1; }
    #buttons { height: auto; margin-top: 1; align-horizontal: right; }
    Button { margin-left: 2; }
    """

    def __init__(self, var: VariableInfo) -> None:
        super().__init__()
        self.var = var

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label(
                f"Write to [b]{self.var.browse_path}[/b]  ({self.var.data_type})", id="prompt"
            )
            yield Label(f"current: {self.var.value!r}")
            yield Input(value=str(self.var.value), id="value")
            with Vertical(id="buttons"):
                yield Button("Write to PLC", variant="error", id="ok")
                yield Button("Cancel", id="cancel")

    @on(Button.Pressed, "#ok")
    @on(Input.Submitted, "#value")
    def _confirm(self) -> None:
        self.dismiss(self.query_one("#value", Input).value)

    @on(Button.Pressed, "#cancel")
    def _cancel(self) -> None:
        self.dismiss(None)


class TuivisuApp(App[None]):
    """Terminal view of a CODESYS PLC's published variables."""

    TITLE = f"tuivisu {__version__}"

    BINDINGS: ClassVar = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "edit", "Edit value"),
    ]

    CSS = """
    #status { height: 1; background: $surface; color: $text-muted; padding: 0 1; }
    """

    def __init__(self, config: PlcConfig) -> None:
        super().__init__()
        self.plc = PlcConnection(config)
        self._vars: dict[str, VariableInfo] = {}  # node_id -> info
        self._subscription: Any = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("connecting...", id="status")
            yield DataTable(id="variables", cursor_type="row", zebra_stripes=True)
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
            self._vars[var.node_id] = var
            table.add_row(*self._row_cells(var), key=var.node_id)
        status.update(f"{self.plc.config.url} - {len(variables)} variables - subscribing...")
        try:
            self._subscription = await self.plc.subscribe(list(self._vars), _SubHandler(self))
            status.update(f"{self.plc.config.url} - {len(variables)} variables - live")
        except Exception as exc:  # live is best-effort; static view still works
            status.update(f"{self.plc.config.url} - {len(variables)} variables - static ({exc})")

    @staticmethod
    def _row_cells(var: VariableInfo) -> tuple[str, str, str, str]:
        access = "rw" if var.writable else "r"
        editable = " *" if (var.writable and is_editable(var.data_type, var.value)) else ""
        return (var.browse_path, _fmt(var.value), var.data_type, access + editable)

    def on_value_change(self, node_id: str, value: Any) -> None:
        var = self._vars.get(node_id)
        if var is None:
            return
        var.value = value
        table = self.query_one("#variables", DataTable)
        with suppress(Exception):  # row may not be mounted yet during startup
            table.update_cell(node_id, "Value", _fmt(value))

    async def action_edit(self) -> None:
        table = self.query_one("#variables", DataTable)
        if table.cursor_row < 0:
            return
        cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
        node_id = cell_key.row_key.value
        var = self._vars.get(node_id) if node_id else None
        if var is None:
            return
        if not (var.writable and is_editable(var.data_type, var.value)):
            self.notify(f"{var.browse_path} is not an editable scalar", severity="warning")
            return
        text = await self.push_screen_wait(EditScreen(var))
        if text is None:
            return
        try:
            value = coerce(var.data_type, text)
        except ValueError as exc:
            self.notify(str(exc), severity="error")
            return
        try:
            await self.plc.write(var.node_id, value)
            self.notify(f"wrote {value!r} to {var.browse_path}")
        except Exception as exc:  # surface any PLC-side rejection
            self.notify(f"write failed: {type(exc).__name__}: {exc}", severity="error")

    async def on_unmount(self) -> None:
        if self._subscription is not None:
            with suppress(Exception):
                await self._subscription.delete()
        await self.plc.disconnect()


def _fmt(value: Any) -> str:
    """Compact one-line rendering of a value for a table cell."""
    text = repr(value)
    return text if len(text) <= 60 else text[:57] + "..."
