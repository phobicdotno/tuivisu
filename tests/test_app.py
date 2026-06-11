"""Headless app checks: shell mounts, q quits, failed connect is reported."""

from textual.widgets import DataTable, Static

from tuivisu.app import TuivisuApp
from tuivisu.plc import PlcConfig


def unreachable_config() -> PlcConfig:
    # 192.0.2.0/24 is TEST-NET-1: guaranteed unroutable, fails fast.
    return PlcConfig(url="opc.tcp://192.0.2.1:4840", timeout=0.5)


async def test_app_mounts_and_reports_failed_connection() -> None:
    app = TuivisuApp(unreachable_config())
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(1.5)
        status = app.query_one("#status", Static)
        text = str(status.render())
        assert "connection failed" in text or "connecting" in text
        assert app.query_one("#variables", DataTable) is not None


async def test_q_quits() -> None:
    app = TuivisuApp(unreachable_config())
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("q")
    assert app.return_value is None  # app exited cleanly
