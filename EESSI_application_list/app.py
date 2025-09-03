from flask import Flask, render_template, jsonify,request
import yaml
import os
import subprocess
#from utils import fetch_and_save_modules


app = Flask(__name__)

YML_PATH = os.path.join(os.path.dirname(__file__), "data", "eessi-modules.yaml")

@app.route("/")
def index():
    try:
        # Only admin have permission to update this yml file. Updating can also be done in a cron job.
        # Lmod cache file can be used for getting module info. We'll work on that in the future.
        # if not os.path.exists(YML_PATH):
        #    fetch_and_save_modules(YML_PATH)

        with open(YML_PATH, "r") as f:
            yml_data = yaml.safe_load(f)
            packages = yml_data.get("packages", [])
    except Exception as e:
        packages = []
        error = str(e)
        return render_template("index.html", packages=packages, error=error)

    return render_template("index.html", packages=packages)

@app.route("/whatis", endpoint="module_whatis")
def module_whatis():
    mod = request.args.get("mod")
    version = request.args.get("version")
    
    if not mod or not version:
        return jsonify({"error": "Missing parameters"}), 400
    try:
        #cmd = f"source /cvmfs/software.eessi.io/versions/2023.06/init/bash > /dev/null 2>&1 && module whatis {mod}/{version} 2>&1 | sed -E 's/^[^:]+:[[:space:]]*//'"
        #cmd = f"module whatis {mod}/{version}"
        cmd = f"""source /cvmfs/software.eessi.io/versions/2023.06/init/bash > /dev/null 2>&1 && module whatis {mod}/{version} 2>&1 | awk \'
/^[^:]+:[[:space:]]*Description:/ {{ desc = substr($0, index($0, "Description:") + 12); collecting = 1; next }}
/^[^:]+:[[:space:]]*Homepage:/ {{ collecting = 0; print "Description: " desc; print $0 | "sed -E s/^[^:]+:[[:space:]]*//"; next }}
collecting {{ desc = desc " " $0 }}\'"""

        result = subprocess.run(cmd, shell=True, executable="/bin/bash",
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        output = (result.stdout + result.stderr).strip()
        print("[DEBUG] Return code:", result.returncode)
        print("[DEBUG] STDOUT:", repr(result.stdout))
        print("[DEBUG] STDERR:", repr(result.stderr))
        return jsonify({"mod": mod, "version": version, "info": output})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run()
    print("[DEBUG] Serving template from:", os.path.abspath("templates/index.html"))

