"""Connect to a PLC's OPC UA server and dump its GlobalVars via PlcConnection.

Usage: python scripts/browse_plc.py <url> [user] [password] [max_depth]
"""

import asyncio
import sys

from tuivisu.plc import PlcConfig, PlcConnection


async def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "opc.tcp://localhost:4840"
    user = sys.argv[2] if len(sys.argv) > 2 else None
    password = sys.argv[3] if len(sys.argv) > 3 else None
    max_depth = int(sys.argv[4]) if len(sys.argv) > 4 else 3

    plc = PlcConnection(PlcConfig(url=url, username=user, password=password, timeout=10))
    try:
        await plc.connect()
    except Exception as exc:  # probe wants the failure reason
        print(f"CONNECT FAILED: {type(exc).__name__}: {exc}")
        return 1
    print(f"CONNECTED to {url}" + (f" as {user}" if user else " (anonymous)"))
    try:
        roots = await plc.find_application_roots()
        print("app roots:", [label for label, _ in roots] or "none")
        variables = await plc.browse_variables(max_depth=max_depth)
        print(f"TOTAL VARS: {len(variables)}")
        for var in variables[:60]:
            access = "rw" if var.writable else "r"
            print(f"  {var.browse_path} = {var.value!r} ({var.data_type}, {access})")
        if len(variables) > 60:
            print(f"  ... ({len(variables) - 60} more)")
    finally:
        await plc.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
