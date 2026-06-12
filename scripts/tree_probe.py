"""Dump the OBJECT structure (not values) to locate the IEC variable branch.

Usage: python scripts/tree_probe.py <url> <user> <password> [max_depth]
"""

import asyncio
import sys

from asyncua import Client, Node, ua


async def walk(node: Node, depth: int, max_depth: int, out: list[str]) -> None:
    if depth > max_depth:
        return
    try:
        children = await node.get_children()
    except ua.UaError:
        return
    for child in children:
        try:
            name = (await child.read_browse_name()).Name
            cls = await child.read_node_class()
        except ua.UaError:
            continue
        # skip the big standard Server housekeeping subtree
        if name == "Server" and depth == 0:
            out.append(f"{'  ' * depth}{name} [Object]  (standard - skipped)")
            continue
        marker = ""
        if cls == ua.NodeClass.Variable:
            marker = " <VAR>"
        out.append(f"{'  ' * depth}{name} [{cls.name}]{marker}")
        if cls == ua.NodeClass.Object:
            await walk(child, depth + 1, max_depth, out)


async def main() -> int:
    url, user, password = sys.argv[1], sys.argv[2], sys.argv[3]
    max_depth = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    client = Client(url=url, timeout=10)
    client.set_user(user)
    client.set_password(password)
    await client.connect()
    print(f"CONNECTED {url}")
    try:
        out: list[str] = []
        await walk(client.nodes.objects, 0, max_depth, out)
        print("\n".join(out[:400]))
        if len(out) > 400:
            print(f"... ({len(out) - 400} more)")
    finally:
        await client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
