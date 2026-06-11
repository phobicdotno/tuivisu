"""Probe a CODESYS OPC UA server: connect anonymously and dump the address space.

Usage: python scripts/browse_probe.py [opc.tcp://host:port] [max_depth]
"""

import asyncio
import sys

from asyncua import Client, ua


async def browse(node, depth, max_depth, lines):
    if depth > max_depth:
        return
    try:
        children = await node.get_children()
    except ua.UaError as exc:
        lines.append(f"{'  ' * depth}<browse failed: {exc}>")
        return
    for child in children:
        try:
            name = (await child.read_browse_name()).Name
            cls = await child.read_node_class()
        except ua.UaError:
            continue
        tag = ""
        if cls == ua.NodeClass.Variable:
            try:
                val = await child.read_value()
                dtype = await child.read_data_type_as_variant_type()
                tag = f" = {val!r} ({dtype.name})"
            except ua.UaError as exc:
                tag = f" <read failed: {type(exc).__name__}>"
        lines.append(f"{'  ' * depth}{name} [{cls.name}]{tag}")
        # only descend into structural nodes, not every variable
        if cls in (ua.NodeClass.Object, ua.NodeClass.Variable):
            await browse(child, depth + 1, max_depth, lines)


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "opc.tcp://localhost:14840"
    max_depth = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    client = Client(url=url, timeout=10)
    try:
        await client.connect()
    except Exception as exc:
        print(f"CONNECT FAILED: {type(exc).__name__}: {exc}")
        return 1
    print(f"CONNECTED to {url}")
    try:
        ns = await client.get_namespace_array()
        for i, n in enumerate(ns):
            print(f"  ns{i}: {n}")
        lines = []
        await browse(client.nodes.objects, 0, max_depth, lines)
        print("\n".join(lines[:300]))
        if len(lines) > 300:
            print(f"... ({len(lines) - 300} more nodes)")
    finally:
        await client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
