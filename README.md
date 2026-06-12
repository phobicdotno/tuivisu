# tuivisu

Terminal UI for CODESYS PLCs — a TUI take on the WebVisu, readable and editable
over SSH. Connects to the PLC's **OPC UA** server (the supported, documented
channel; the WebVisu wire protocol itself is proprietary binary paint commands
and deliberately not used).

## Install

```bash
pipx install tuivisu
```

## Run

```bash
tuivisu --url opc.tcp://<plc>:4840 --user <device-user> --password <pw>
```

Keys: `q` quit - arrow keys browse - **Enter** edit the selected value.

Values are **live** (OPC UA subscription) and update in place. Rows whose
Access shows `rw *` are editable scalars; Enter opens an input and **confirms
before writing** to the PLC. Which variables appear is whatever the project's
**Symbol Configuration** publishes — curate the set in the IDE, exactly like
binding a WebVisu to specific GVLs / program variables.

## PLC prerequisites

- A **Symbol Configuration** object with *Support OPC UA features* enabled
  (Application → Add Object → Symbol Configuration), variables published,
  application downloaded.
- A device user (or anonymous access explicitly allowed in the device's
  Communication Policy).

## Development

```bash
py -m venv .venv
.venv/Scripts/pip install -e . --group dev
.venv/Scripts/python -m pytest -q
ruff check . && ruff format --check . && mypy src
```
