# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

pyRheem is a Python library and CLI for controlling Rheem water heaters via the EcoNet API. It provides both programmatic access through a Python API and a command-line interface with interactive mode.

## Development Commands

```bash
# Install for development (editable mode)
pip install -e .

# Install with dev dependencies (pytest, python-dotenv)
pip install -e ".[dev]"

# Run CLI
rheem --list
rheem --help

# Run tests
pytest
```

## Architecture

### Module Structure

- **`pyrheem/api.py`** - Core API client (`RheemEcoNetAPI` class). Handles REST authentication via ClearBlade platform and MQTT for real-time device control. All device commands (temperature, mode, enable/disable) go through MQTT.

- **`pyrheem/models.py`** - Dataclasses: `RheemSession` (auth state), `Location` (home/site), `WaterHeater` (device with setpoint, mode, status).

- **`pyrheem/cli.py`** - CLI entry point with argparse. Supports single commands (`--temp`, `--mode`, etc.) and interactive mode with REPL.

### Key Patterns

- **Authentication flow**: REST call to `/user/auth` returns `user_token`, then MQTT uses token + system key for pub/sub.
- **Device lookup**: Locations and devices can be referenced by index, ID/serial, or partial name match (see `get_location()` and `get_device()` methods).
- **MQTT compatibility**: Handles both paho-mqtt v1 and v2 API versions.
- **Quiet mode**: Library defaults to `quiet=True` (no console output); CLI enables output for interactive use.

### API Endpoints (ClearBlade)

- Base URL: `https://rheem.rheemconnect.com/api/v/1/`
- MQTT broker: `rheemprod.rheemcert.com:1884` (TLS)
- Topics: `user/{account_id}/device/desired` (commands), `user/{account_id}/device/reported` (status)

## Configuration

Credentials via environment variables or `.env` file:
```
RHEEM_EMAIL=your_email
RHEEM_PASSWORD=your_password
```
