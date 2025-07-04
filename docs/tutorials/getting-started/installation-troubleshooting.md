# Installation Troubleshooting Guide

This guide helps you solve common installation and setup issues with Watchtower. Follow the sections relevant to your specific problem.

## 🚨 Common Error Categories

- [Python Installation Issues](#python-installation-issues)
- [Dependency Installation Problems](#dependency-installation-problems)
- [Playwright Browser Issues](#playwright-browser-issues)
- [Permission and Access Problems](#permission-and-access-problems)
- [Network and Firewall Issues](#network-and-firewall-issues)
- [Virtual Environment Problems](#virtual-environment-problems)
- [Operating System Specific Issues](#operating-system-specific-issues)

---

## 🐍 Python Installation Issues

### Problem: "python: command not found" or "python3: command not found"

**Symptoms:**
```bash
$ python --version
bash: python: command not found
```

**Solutions:**

**On Windows:**
1. **Install Python from official site:**
   - Go to [python.org/downloads](https://python.org/downloads/)
   - Download Python 3.10+ installer
   - **Important**: Check "Add Python to PATH" during installation

2. **Verify installation:**
   ```cmd
   python --version
   # Should show: Python 3.10.x or higher
   ```

3. **If still not found:**
   ```cmd
   # Try python3 instead
   python3 --version
   
   # Or check if py launcher works
   py --version
   ```

**On macOS:**
```bash
# Install using Homebrew (recommended)
brew install python@3.10

# Or install from python.org
# Download installer from https://python.org/downloads/macos/

# Add to PATH if needed
echo 'export PATH="/usr/local/opt/python@3.10/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**On Linux (Ubuntu/Debian):**
```bash
# Update package list
sudo apt update

# Install Python 3.10+
sudo apt install python3.10 python3.10-venv python3.10-dev

# Create symlink if needed
sudo ln -s /usr/bin/python3.10 /usr/bin/python
```

### Problem: "Python version too old"

**Check your version:**
```bash
python --version
```

**Requirements:** Watchtower requires Python 3.10 or higher.

**Solutions:**
- **Windows/macOS**: Install newer Python from [python.org](https://python.org/downloads/)
- **Linux**: Use version managers like `pyenv`:
  ```bash
  # Install pyenv
  curl https://pyenv.run | bash
  
  # Install Python 3.11
  pyenv install 3.11.0
  pyenv global 3.11.0
  ```

---

## 📦 Dependency Installation Problems

### Problem: "pip: command not found"

**Solutions:**

**Windows:**
```cmd
# Reinstall Python with pip included
# Or download get-pip.py
python -m ensurepip --upgrade
```

**macOS/Linux:**
```bash
# Install pip
python3 -m ensurepip --upgrade

# Or use package manager
# Ubuntu/Debian:
sudo apt install python3-pip

# macOS:
brew install python3
```

### Problem: Poetry installation fails

**Install Poetry properly:**

**Method 1 - Official installer:**
```bash
# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -
```

**Method 2 - pip (alternative):**
```bash
pip install poetry
```

**Add Poetry to PATH:**
```bash
# macOS/Linux
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Windows - Add to PATH manually or restart terminal
```

**Verify Poetry installation:**
```bash
poetry --version
```

### Problem: "poetry install" fails with dependency conflicts

**Solutions:**

1. **Clear Poetry cache:**
   ```bash
   poetry cache clear pypi --all
   ```

2. **Update Poetry:**
   ```bash
   poetry self update
   ```

3. **Force reinstall:**
   ```bash
   poetry install --no-cache
   ```

4. **Use pip as fallback:**
   ```bash
   pip install -r requirements.txt
   ```

### Problem: pip packages fail to install

**Common solutions:**

1. **Upgrade pip:**
   ```bash
   python -m pip install --upgrade pip
   ```

2. **Install with user flag:**
   ```bash
   pip install --user -r requirements.txt
   ```

3. **Clear pip cache:**
   ```bash
   pip cache purge
   pip install -r requirements.txt
   ```

4. **Install with no cache:**
   ```bash
   pip install --no-cache-dir -r requirements.txt
   ```

---

## 🎭 Playwright Browser Issues

### Problem: "Playwright executable doesn't exist"

**Symptoms:**
```
playwright._impl._api_structures.Error: Playwright executable doesn't exist
```

**Solutions:**

1. **Install Playwright browsers:**
   ```bash
   playwright install
   ```

2. **Install specific browsers:**
   ```bash
   # Install only needed browsers
   playwright install chromium
   playwright install firefox
   playwright install webkit
   ```

3. **Check installation:**
   ```bash
   playwright --version
   ```

### Problem: Browser installation fails on Linux

**Install system dependencies:**

**Ubuntu/Debian:**
```bash
# Install system dependencies for browsers
sudo apt-get update
sudo apt-get install -y \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxss1 \
    libasound2 \
    libatspi2.0-0 \
    libgtk-3-0

# Then install browsers
playwright install
```

**CentOS/RHEL/Fedora:**
```bash
sudo dnf install -y \
    nss \
    atk \
    at-spi2-atk \
    gtk3 \
    alsa-lib \
    drm \
    libxkbcommon \
    libXScrnSaver

playwright install
```

### Problem: "Permission denied" during browser installation

**Solutions:**

1. **Run with proper permissions:**
   ```bash
   # Linux/macOS - don't use sudo with playwright
   playwright install
   
   # If needed, fix ownership
   sudo chown -R $USER:$USER ~/.cache/ms-playwright/
   ```

2. **Windows - Run as Administrator:**
   - Right-click Command Prompt or PowerShell
   - Select "Run as Administrator"
   - Run `playwright install`

### Problem: Browsers fail to launch in Docker/CI

**Add browser launch arguments:**
```python
# In your ETL/watcher code
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--single-process',
            '--disable-gpu'
        ]
    )
```

---

## 🔐 Permission and Access Problems

### Problem: "Permission denied" errors

**Windows solutions:**

1. **Run as Administrator:**
   - Right-click Command Prompt/PowerShell
   - Select "Run as Administrator"

2. **Fix execution policy:**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

3. **Check file permissions:**
   ```cmd
   # Make sure you have write access to the project directory
   icacls watchtower /grant %USERNAME%:F /T
   ```

**Linux/macOS solutions:**

1. **Fix ownership:**
   ```bash
   sudo chown -R $USER:$USER /path/to/watchtower
   ```

2. **Fix permissions:**
   ```bash
   chmod -R 755 /path/to/watchtower
   ```

3. **Don't use sudo with pip/poetry:**
   ```bash
   # Wrong
   sudo pip install poetry
   
   # Right
   pip install --user poetry
   ```

### Problem: Cannot write to data directory

**Create data directory manually:**
```bash
mkdir -p data/{etl,watchers,logs}
chmod 755 data/
```

**Check disk space:**
```bash
df -h  # Linux/macOS
dir   # Windows
```

---

## 🌐 Network and Firewall Issues

### Problem: "SSL: CERTIFICATE_VERIFY_FAILED"

**Solutions:**

1. **Update certificates:**
   ```bash
   # macOS
   /Applications/Python\ 3.11/Install\ Certificates.command
   
   # Linux
   sudo apt-get update && sudo apt-get install ca-certificates
   
   # Windows - update Windows or reinstall Python
   ```

2. **Temporary workaround (not recommended for production):**
   ```python
   import ssl
   ssl._create_default_https_context = ssl._create_unverified_context
   ```

### Problem: Corporate firewall blocking downloads

**Solutions:**

1. **Configure pip to use proxy:**
   ```bash
   pip install --proxy http://proxy.company.com:8080 -r requirements.txt
   ```

2. **Configure Poetry for proxy:**
   ```bash
   poetry config http-basic.pypi username password
   poetry config repositories.pypi https://pypi.org/simple/
   ```

3. **Use internal PyPI mirror:**
   ```bash
   pip install -i https://internal-pypi.company.com/simple/ -r requirements.txt
   ```

### Problem: DNS resolution failures

**Test connectivity:**
```bash
# Test DNS
nslookup pypi.org

# Test connectivity
ping pypi.org

# Test HTTPS
curl -I https://pypi.org
```

---

## 🐣 Virtual Environment Problems

### Problem: Virtual environment not activating

**Poetry issues:**
```bash
# Check Poetry environment
poetry env info

# Create new environment
poetry env remove python
poetry install

# Activate manually
poetry shell
```

**venv issues:**
```bash
# Windows
.venv\Scripts\activate.bat   # CMD
.venv\Scripts\Activate.ps1   # PowerShell

# Linux/macOS
source .venv/bin/activate
```

### Problem: "No module named 'src'"

**Symptoms:**
```
ModuleNotFoundError: No module named 'src'
```

**Solutions:**

1. **Run from project root:**
   ```bash
   cd /path/to/watchtower
   python my_first_etl.py
   ```

2. **Install in development mode:**
   ```bash
   pip install -e .
   ```

3. **Add to PYTHONPATH:**
   ```bash
   export PYTHONPATH="${PYTHONPATH}:/path/to/watchtower"
   ```

### Problem: Wrong Python version in virtual environment

**Check and fix:**
```bash
# Check which Python is being used
which python
python --version

# Recreate with specific Python
poetry env remove python
poetry env use python3.10
poetry install
```

---

## 💻 Operating System Specific Issues

### Windows Specific

**PowerShell Execution Policy:**
```powershell
# Check current policy
Get-ExecutionPolicy

# Set policy to allow script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Long path support:**
```cmd
# Enable long paths in Windows (requires admin)
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

**Windows Defender exclusions:**
- Add the watchtower directory to Windows Defender exclusions
- Go to Settings > Update & Security > Windows Security > Virus & threat protection
- Add folder exclusion for your project directory

### macOS Specific

**Xcode Command Line Tools:**
```bash
xcode-select --install
```

**macOS Gatekeeper issues:**
```bash
# If browsers are blocked by Gatekeeper
sudo spctl --master-disable  # Not recommended
# Or approve individual applications in System Preferences > Security & Privacy
```

**M1/M2 Mac specific:**
```bash
# Install Rosetta if needed
softwareupdate --install-rosetta

# Use x86_64 Python if having issues
arch -x86_64 pip install -r requirements.txt
```

### Linux Specific

**Missing development packages:**
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev python3-pip python3-venv build-essential

# CentOS/RHEL/Fedora
sudo dnf install python3-devel python3-pip gcc

# Alpine
apk add python3-dev py3-pip gcc musl-dev
```

**SELinux issues:**
```bash
# Check if SELinux is causing issues
getenforce

# Temporarily disable (not recommended for production)
sudo setenforce 0
```

---

## 🔍 Diagnostic Commands

Use these commands to gather information when reporting issues:

### System Information
```bash
# Python version and location
python --version
which python

# pip version and packages
pip --version
pip list

# Poetry version and environment
poetry --version
poetry env info

# System information
uname -a  # Linux/macOS
ver       # Windows
```

### Project Status
```bash
# Check project structure
ls -la
tree . -L 2  # if tree is installed

# Check permissions
ls -la data/

# Check logs
ls -la logs/  # if logs directory exists
```

### Network Diagnostics
```bash
# Test connectivity
ping pypi.org
curl -I https://pypi.org

# Check proxy settings
echo $HTTP_PROXY
echo $HTTPS_PROXY
```

---

## 🆘 Getting Additional Help

### Before Asking for Help

1. **Try the quick fixes** in this guide
2. **Search existing issues** on [GitHub](https://github.com/josmerod/watchtower/issues)
3. **Gather diagnostic information** using commands above

### Where to Get Help

1. **GitHub Issues**: [Create a new issue](https://github.com/josmerod/watchtower/issues/new)
   - Use the bug report template
   - Include diagnostic information
   - Describe what you tried

2. **Documentation**: Check other guides:
   - [Complete Beginner's Guide](complete-beginners-guide.md)
   - [Quick Start for Developers](quick-start-developers.md)
   - [Main README](../../../README.md)

### Information to Include

When asking for help, please include:

```
**Environment:**
- OS: [e.g., Windows 10, macOS 12.6, Ubuntu 20.04]
- Python version: [output of `python --version`]
- Installation method: [Poetry, pip, etc.]
- Error message: [full error traceback]

**What I tried:**
- List the steps you followed
- What you expected to happen
- What actually happened

**Diagnostic output:**
- Output of diagnostic commands above
- Relevant log files
```

---

## ✅ Verification Checklist

After resolving issues, verify your installation:

- [ ] Python 3.10+ is installed and accessible
- [ ] Virtual environment is created and activated
- [ ] All dependencies are installed without errors
- [ ] Playwright browsers are installed
- [ ] Can run: `python src/etl/news/news_get_ycombinator.py`
- [ ] Can start dashboard: `streamlit run src/web/fullstreamlit/app.py`
- [ ] Data directory is writable
- [ ] No permission errors

If all items are checked, you're ready to use Watchtower! 🎉

---

## 🚀 Next Steps

Once you've resolved installation issues:

1. **Return to the [Complete Beginner's Guide](complete-beginners-guide.md)**
2. **Try the [Quick Start for Developers](quick-start-developers.md)**
3. **Explore [Real-World Use Cases](../use-cases/)**

Remember: Installation issues are common and normal. Don't get discouraged! The Watchtower community is here to help. 🤗