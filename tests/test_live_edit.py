"""Drive the app with a fake PLC to prove live updates and edit-writes work."""

from __future__ import annotations

from typing import Any

from textual.widgets import DataTable, Input

from tuivisu.app import TuivisuApp, _SubHandler
from tuivisu.plc import PlcConfig, VariableInfo


class _FakeNode:
    def __init__(self, node_id: str) -> None:
        self.nodeid = _FakeNodeId(node_id)


class _FakeNodeId:
    def __init__(self, node_id: str) -> None:
        self._id = node_id

    def to_string(self) -> str:
        return self._id


class _FakeSub:
    async def delete(self) -> None:
        pass


class FakePlc:
    """Stands in for PlcConnection with the surface the app uses."""

    def __init__(self, variables: list[VariableInfo]) -> None:
        self._variables = variables
        self.config = PlcConfig(url="opc.tcp://fake:4840")
        self.handler: Any = None
        self.written: list[tuple[str, Any]] = []

    async def connect(self) -> None:
        pass

    async def browse_variables(self, **_: Any) -> list[VariableInfo]:
        return self._variables

    async def subscribe(self, node_ids: list[str], handler: Any, period_ms: int = 500) -> _FakeSub:
        self.handler = handler
        return _FakeSub()

    async def write(self, node_id: str, value: Any) -> None:
        self.written.append((node_id, value))

    async def disconnect(self) -> None:
        pass


def _sample_vars() -> list[VariableInfo]:
    return [
        VariableInfo(
            node_id="ns=4;s=Speed",
            browse_path="GVL.Speed",
            value=0,
            data_type="Int32",
            writable=True,
        ),
        VariableInfo(
            node_id="ns=4;s=Name",
            browse_path="GVL.Name",
            value="x",
            data_type="String",
            writable=False,
        ),
    ]


def _app_with_fake() -> tuple[TuivisuApp, FakePlc]:
    app = TuivisuApp(PlcConfig(url="opc.tcp://fake:4840"))
    fake = FakePlc(_sample_vars())
    app.plc = fake  # type: ignore[assignment]
    return app, fake


async def test_live_value_updates_cell() -> None:
    app, fake = _app_with_fake()
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        assert fake.handler is not None  # subscription was created
        table = app.query_one("#variables", DataTable)
        assert table.get_cell("ns=4;s=Speed", "Value") == "0"
        # simulate a PLC-side change through the real subscription handler
        assert isinstance(fake.handler, _SubHandler)
        fake.handler.datachange_notification(_FakeNode("ns=4;s=Speed"), 123, None)
        await pilot.pause()
        assert table.get_cell("ns=4;s=Speed", "Value") == "123"


async def test_edit_writes_value_after_confirm() -> None:
    app, fake = _app_with_fake()
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        table = app.query_one("#variables", DataTable)
        app.set_focus(table)
        table.move_cursor(row=0)  # the writable Int32 row
        await pilot.pause()
        await pilot.press("enter")  # opens the edit modal
        await pilot.pause()
        await pilot.pause()
        assert len(app.screen_stack) == 2, "edit modal did not open"
        app.screen.query_one("#value", Input).value = "55"
        await pilot.click("#ok")
        await pilot.pause()
        assert fake.written == [("ns=4;s=Speed", 55)]


async def test_readonly_row_is_not_editable() -> None:
    app, fake = _app_with_fake()
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        table = app.query_one("#variables", DataTable)
        table.focus()
        table.move_cursor(row=1)  # the read-only String row
        await pilot.press("enter")
        await pilot.pause()
        # no modal opened, nothing written
        assert fake.written == []
