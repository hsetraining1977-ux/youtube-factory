"""
Setup & validation script — run this first!
Checks all dependencies and API keys.
"""
import subprocess
import sys
import os
from pathlib import Path


def check(label, ok, fix=""):
    icon = "✅" if ok else "❌"
    print(f"  {icon}  {label}")
    if not ok and fix:
        print(f"       → {fix}")
    return ok


def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        return r.returncode == 0, r.stdout.strip()
    except Exception:
        return False, ""


print("\n" + "═"*55)
print("  Multi-Channel Factory — Setup Check")
print("═"*55 + "\n")

all_ok = True

# ── Python ─────────────────────────────────────────────
print("🐍 Python:")
ok, ver = run("python --version")
all_ok &= check(f"Python installed ({ver})", ok, "Install Python 3.11+ from python.org")
ok = sys.version_info >= (3, 11)
all_ok &= check("Python version 3.11+", ok, f"Current: {sys.version}. Need 3.11+")

# ── FFmpeg ─────────────────────────────────────────────
print("\n🎬 FFmpeg:")
ok, _ = run("ffmpeg -version")
if not ok:
    ok, _ = run("ffmpeg.exe -version")
ffmpeg_ok = ok
all_ok &= check("FFmpeg installed", ffmpeg_ok,
    "Windows: winget install Gyan.FFmpeg  OR  choco install ffmpeg\n"
    "       Mac: brew install ffmpeg\n"
    "       Linux: sudo apt install ffmpeg")

# ── Python packages ────────────────────────────────────
print("\n📦 Python packages:")
packages = {
    "anthropic": "pip install anthropic",
    "elevenlabs": "pip install elevenlabs",
    "moviepy": "pip install moviepy",
    "PIL": "pip install Pillow",
    "google.oauth2": "pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client",
    "openai": "pip install openai",
    "httpx": "pip install httpx",
    "yaml": "pip install pyyaml",
    "dotenv": "pip install python-dotenv",
    "schedule": "pip install schedule",
    "pydantic": "pip install pydantic",
}

missing = []
for pkg, install_cmd in packages.items():
    try:
        __import__(pkg.split(".")[0])
        check(pkg, True)
    except ImportError:
        check(pkg, False, install_cmd)
        missing.append(install_cmd.split("install ")[1])

if missing:
    print(f"\n  → Run: pip install {' '.join(missing)}")
    all_ok = False

# ── .env file ──────────────────────────────────────────
print("\n🔑 API Keys (.env file):")
env_path = Path(".env")
if not env_path.exists():
    print("  ❌  .env file not found")
    print("     → Copy .env.example to .env and fill in your API keys")
    all_ok = False
else:
    from dotenv import load_dotenv
    load_dotenv()

    keys = {
        "ANTHROPIC_API_KEY": ("Anthropic", "https://console.anthropic.com"),
        "ELEVENLABS_API_KEY": ("ElevenLabs", "https://elevenlabs.io → Profile → API Keys"),
        "OPENAI_API_KEY": ("OpenAI (DALL-E)", "https://platform.openai.com/api-keys"),
        "PEXELS_API_KEY": ("Pexels", "https://www.pexels.com/api/"),
    }

    for env_var, (name, url) in keys.items():
        val = os.getenv(env_var, "")
        ok = bool(val and len(val) > 10 and "your" not in val.lower())
        all_ok &= check(f"{name} key set", ok, f"Get it from: {url}")

# ── YouTube OAuth ──────────────────────────────────────
print("\n📺 YouTube:")
secrets_ok = Path("client_secrets.json").exists()
check("client_secrets.json present", secrets_ok,
    "Download from Google Cloud Console (see GUIDE.md → YouTube Setup)")
if not secrets_ok:
    all_ok = False

# ── Live API tests ─────────────────────────────────────
if os.getenv("ANTHROPIC_API_KEY") and "your" not in os.getenv("ANTHROPIC_API_KEY", "").lower():
    print("\n🧪 API Connectivity Tests:")
    try:
        import anthropic
        c = anthropic.Anthropic()
        r = c.messages.create(
            model="claude-haiku-4-5",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say OK"}]
        )
        check("Claude API reachable", True)
    except Exception as e:
        check("Claude API reachable", False, str(e))
        all_ok = False

    pexels_key = os.getenv("PEXELS_API_KEY", "")
    if pexels_key and "your" not in pexels_key.lower():
        try:
            import httpx
            r = httpx.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": pexels_key},
                params={"query": "nature", "per_page": 1},
                timeout=10
            )
            check("Pexels API reachable", r.status_code == 200)
        except Exception as e:
            check("Pexels API reachable", False, str(e))

# ── Summary ────────────────────────────────────────────
print("\n" + "═"*55)
if all_ok:
    print("✅  Everything ready! Run:")
    print("   python factory.py --channel mystery_history --no-upload")
else:
    print("⚠️   Fix the issues above, then run setup.py again")
    print("\n📋 Quick install command:")
    print("   pip install anthropic elevenlabs moviepy Pillow openai httpx pyyaml python-dotenv schedule pydantic google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
print("═"*55 + "\n")
