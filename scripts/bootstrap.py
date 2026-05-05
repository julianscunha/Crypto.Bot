import os
import sys

ROOT = os.getcwd()

REQUIRED_DIRS = [
    "apps",
    "apps/api",
    "apps/trader",
    "core",
    "core/workroom",
    "core/agents",
    "core/orchestrator",
    "core/contracts",
    "data",
    "data/ingestion",
    "infra",
]

REQUIRED_FILES = [
    "requirements.txt",
    "apps/api/main.py",
]

def warn(msg):
    print(f"[WARN] {msg}")

def error(msg):
    print(f"[ERROR] {msg}")
    sys.exit(1)

def ensure_dirs():
    for d in REQUIRED_DIRS:
        path = os.path.join(ROOT, d)
        if not os.path.exists(path):
            os.makedirs(path)
            warn(f"Created missing directory: {d}")

def ensure_init_files():
    for root, dirs, files in os.walk(ROOT):
        if "__pycache__" in root:
            continue

        if any(x in root for x in ["scripts", ".git"]):
            continue

        init_file = os.path.join(root, "__init__.py")

        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("")
            warn(f"Created __init__.py in {root}")

def validate_files():
    for f in REQUIRED_FILES:
        path = os.path.join(ROOT, f)
        if not os.path.exists(path):
            error(f"Missing required file: {f}")

def validate_requirements():
    path = os.path.join(ROOT, "requirements.txt")
    if not os.path.exists(path):
        error("requirements.txt not found")

def main():
    ensure_dirs()
    ensure_init_files()
    validate_files()
    validate_requirements()

    print("[OK] Environment ready")

if __name__ == "__main__":
    main()