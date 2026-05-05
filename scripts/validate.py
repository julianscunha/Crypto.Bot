import os
for d in ["apps","core","infra","data"]:
    if not os.path.exists(d):
        raise Exception(f"Missing {d}")
print("OK")
