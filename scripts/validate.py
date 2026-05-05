import os

required_dirs = [
    "apps",
    "core",
    "infra",
    "data"
]

for d in required_dirs:
    if not os.path.exists(d):
        raise Exception(f"Missing directory: {d}")

print("Structure OK")
