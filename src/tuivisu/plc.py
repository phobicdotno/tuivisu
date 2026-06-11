"""OPC UA connection to a CODESYS runtime.

Wraps asyncua.Client with the bits tuivisu needs: optional username/password
auth (CODESYS device users), reconnect-friendly connect/disconnect, and
browse/read/write helpers that speak in plain Python values.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Any

from asyncua import Client, Node, ua


@dataclass
class PlcConfig:
    """Where and how to reach the PLC's OPC UA server."""

    url: str = "opc.tcp://localhost:4840"
    username: str | None = None
    password: str | None = None
    timeout: float = 10.0


@dataclass
class VariableInfo:
    """One browsable PLC variable."""

    node_id: str
    browse_path: str
    value: Any = None
    data_type: str = ""
    writable: bool = False
    node: Node | None = field(default=None, repr=False, compare=False)


class PlcConnection:
    """A live OPC UA session against one CODESYS runtime."""

    def __init__(self, config: PlcConfig) -> None:
        self.config = config
        self._client: Client | None = None

    @property
    def connected(self) -> bool:
        return self._client is not None

    async def connect(self) -> None:
        client = Client(url=self.config.url, timeout=self.config.timeout)
        if self.config.username:
            client.set_user(self.config.username)
            client.set_password(self.config.password or "")
        await client.connect()
        self._client = client

    async def disconnect(self) -> None:
        if self._client is not None:
            client, self._client = self._client, None
            with contextlib.suppress(Exception):  # teardown must never raise
                await client.disconnect()

    def _require_client(self) -> Client:
        if self._client is None:
            raise RuntimeError("not connected")
        return self._client

    async def read(self, node_id: str) -> Any:
        return await self._require_client().get_node(node_id).read_value()

    async def write(self, node_id: str, value: Any) -> None:
        node = self._require_client().get_node(node_id)
        dtype = await node.read_data_type_as_variant_type()
        await node.write_value(ua.Variant(value, dtype))

    async def find_application_roots(self) -> list[tuple[str, Node]]:
        """Locate the CODESYS application branches that carry IEC variables.

        A CODESYS runtime publishes symbols under
        ``Objects/DeviceSet/<device>/Resources/<app>/Programs|GlobalVars``.
        Returns ``(label, node)`` pairs for every GlobalVars/Programs branch
        found; empty when the server is not CODESYS-shaped.
        """
        client = self._require_client()
        roots: list[tuple[str, Node]] = []
        queue: list[tuple[Node, str, int]] = [(client.nodes.objects, "", 0)]
        while queue:
            node, path, depth = queue.pop(0)
            if depth > 6:
                continue
            try:
                children = await node.get_children()
            except ua.UaError:
                continue
            for child in children:
                try:
                    name = (await child.read_browse_name()).Name
                    cls = await child.read_node_class()
                except ua.UaError:
                    continue
                if cls != ua.NodeClass.Object:
                    continue
                child_path = f"{path}.{name}" if path else name
                if name in ("GlobalVars", "Programs"):
                    roots.append((child_path, child))
                else:
                    queue.append((child, child_path, depth + 1))
        return roots

    async def browse_variables(
        self, root: Node | None = None, prefix: str = "", max_depth: int = 6
    ) -> list[VariableInfo]:
        """Collect the PLC's exposed variables.

        Prefers the CODESYS ``GlobalVars`` / ``Programs`` branches (the
        symbols published by the Symbol Configuration); falls back to a full
        address-space walk when none are found.
        """
        client = self._require_client()
        found: list[VariableInfo] = []
        if root is not None:
            await self._walk(root, prefix, 0, max_depth, found)
            return found
        for label, branch in await self.find_application_roots():
            await self._walk(branch, label.rsplit(".", 1)[-1], 0, max_depth, found)
        if not found:
            await self._walk(client.nodes.objects, "", 0, max_depth, found)
        return found

    async def _walk(
        self, node: Node, prefix: str, depth: int, max_depth: int, found: list[VariableInfo]
    ) -> None:
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
            path = f"{prefix}.{name}" if prefix else name
            if cls == ua.NodeClass.Variable:
                info = VariableInfo(node_id=child.nodeid.to_string(), browse_path=path, node=child)
                try:
                    info.value = await child.read_value()
                    info.data_type = (await child.read_data_type_as_variant_type()).name
                    access = await child.read_attribute(ua.AttributeIds.AccessLevel)
                    if access.Value is not None:
                        level = access.Value.Value
                        info.writable = bool(level & ua.AccessLevel.CurrentWrite.mask)
                except ua.UaError:
                    pass
                found.append(info)
            if cls in (ua.NodeClass.Object, ua.NodeClass.Variable):
                await self._walk(child, path, depth + 1, max_depth, found)
