# Installation

## Prerequisites

- **Linux**: Python 3.10+ (usually pre-installed)
- **macOS**: Python 3.10+ (install via `brew install python` if needed)
- **Windows**: Python 3.10+ (download from [python.org](https://www.python.org/downloads/) — check "Add Python to PATH" during installation)

## Clone the Repository

```bash
git clone https://github.com/rammelhof/uptime-kuma-satellite.git
cd uptime-kuma-satellite
```

---

## Linux (Debian/Ubuntu)

### Recommended: Install via `pipx` (isolated, system-wide)

`pipx` creates a private virtual environment and makes the `uks` command globally available:

```bash
# Install pipx
sudo apt install pipx
pipx ensurepath

# Install Uptime Kuma Satellite system-wide
pipx install --global .

# Verify
uks --help
```

### Alternative: System-wide install with `--break-system-packages`

```bash
pip3 install --break-system-packages .
uks --help
```

> **Note:** This bypasses PEP 668 protection. Fine for personal servers, but may conflict with `apt`-managed Python packages.

### Alternative: Dedicated system venv

```bash
sudo python3 -m venv /opt/uptime-kuma-satellite
sudo /opt/uptime-kuma-satellite/bin/pip install .
```

The service will use `/opt/uptime-kuma-satellite/bin/uks` which is stable across venv lifetimes.

---

## Linux (Fedora)

```bash
sudo dnf install python3-pip
pip3 install --user .
```

---

## Linux (Arch)

```bash
sudo pacman -S python-pip
pip install --user .
```

---

## macOS

```bash
# 1. Install Python (if not already installed)
brew install python

# 2. Install the package
pip3 install .

# 3. Verify installation
uks --help
```

---

## Windows (PowerShell)

```powershell
# 1. Install Python (if not already installed)
# Download from https://www.python.org/downloads/ and check "Add Python to PATH"

# 2. Install the package
pip install .

# 3. Verify installation
uks --help
```

---

## Verify Installation

After installation, verify the `uks` command is available:

```bash
uks --help
```

Expected output shows all available commands: `setup`, `add-monitor`, `remove-monitor`, `list-monitors`, `run-once`, `run`, `tui`, `service`, etc.

## Config Path

All commands use the system-wide config by default:

| Platform | Config Path |
|----------|-------------|
| Linux | `/etc/uptime-kuma-satellite/config.yaml` |
| macOS | `/opt/uptime-kuma-satellite/config.yaml` |
| Windows | `%ProgramData%\uptime-kuma-satellite\config.yaml` |

Override with `-c`:

```bash
uks setup -c /path/to/custom/config.yaml -u "http://your-uptime-kuma/api/push/YOUR_API_KEY"
```
