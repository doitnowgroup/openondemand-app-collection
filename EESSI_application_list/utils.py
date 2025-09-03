# utils.py
import subprocess
import re
import yaml
import os

#YML_PATH = os.path.join(os.path.dirname(__file__), "data", "eessi-modules.yaml")

def fetch_and_save_modules(YML_PATH):
    try:
        os.makedirs(os.path.dirname(YML_PATH), exist_ok=True)
        
        load_env = "source /cvmfs/software.eessi.io/versions/2023.06/init/bash > /dev/null 2>&1"

        list_modules_cmd = f"{load_env} && module --terse avail 2>&1"
        result = subprocess.run(list_modules_cmd, shell=True, executable="/bin/bash",
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        lines = result.stdout.splitlines()
        module_entries = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("/") or line.endswith("/"):
                # Skip empty, path lines, or just category entries like Abseil/
                continue

            if "/" in line:
                try:
                    name, version = line.split("/", 1)
                    module_entries.append((name, version))
                except ValueError:
                    print(f"[WARN] Invalid module format: {line}")
                    continue
        packages = []
        for name,version in module_entries:
            packages.append({
                "name": name,
                "version": version,
            })
        
        print(packages)
        # YAML quoting

        with open(YML_PATH, "w") as f:
            yaml.dump({"packages": packages}, f, sort_keys=False)

    except Exception as e:
        print(f"[ERROR] Module fetch failed: {e}")
#if __name__ == "__main__":
#    fetch_and_save_modules()
#    print("Module data has been written to ./data/")
