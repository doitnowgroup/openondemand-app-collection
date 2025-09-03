# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages, send_file
import os
import subprocess

# Create Flask application

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Required for flash messages in Flask

# Define key paths
SSH_DIR = os.path.expanduser("~/.ssh")
PRIVATE_KEY = os.path.join(SSH_DIR, "id_ed25519_test")
PUBLIC_KEY = PRIVATE_KEY + ".pub"
authorized_keys = os.path.join(SSH_DIR, "authorized_keys")

# Function to create an SSH key pair if it doesn't exist
def create_ssh_key():
    os.makedirs(SSH_DIR, exist_ok=True)
    subprocess.run([
        "ssh-keygen", "-t", "ed25519", "-f", PRIVATE_KEY, "-N", "", "-q"
    ], check=True)  # Run ssh-keygen command
    os.chmod(PRIVATE_KEY, 0o600)  # Set correct permissions
    os.chmod(SSH_DIR, 0o700)
    
    # add pub key in authorized_keys
    if os.path.exists(PUBLIC_KEY):
        with open(PUBLIC_KEY, "r") as pub:
            pubkey = pub.read().strip()

        if not os.path.exists(authorized_keys):
            with open(authorized_keys, "w") as f:
                f.write(pubkey + "\n")
        else:
            with open(authorized_keys, "r+") as f:
                keys = f.read()
                if pubkey not in keys:
                    f.write(pubkey + "\n")

        os.chmod(authorized_keys, 0o600)

# Function to delete the SSH key pair
def delete_ssh_key():
    pubkey = None
    if os.path.exists(PUBLIC_KEY):
        with open(PUBLIC_KEY, "r") as f:
            pubkey = f.read().strip()
        os.remove(PUBLIC_KEY)
    if os.path.exists(authorized_keys):
        with open(authorized_keys, "r") as f:
            lines = f.readlines()
        with open(authorized_keys, "w") as f:
            for line in lines:
                if line.strip() != pubkey:
                    f.write(line)

    if os.path.exists(PRIVATE_KEY):
        os.remove(PRIVATE_KEY)

# Function to read the public key content, if it exists
def read_public_key():
    if os.path.exists(PUBLIC_KEY):
        with open(PUBLIC_KEY, "r") as f:
            return f.read()
    return None

# Main route — handles GET (view) and POST (create/delete) actions
@app.route("/", methods=["GET", "POST"])
def index():
    pubkey = read_public_key()

    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "create":
                create_ssh_key()
                flash("SSH key created successfully.")
            elif action == "delete":
                delete_ssh_key()
                flash("SSH key deleted.")
        except subprocess.CalledProcessError:
            flash("Error while processing SSH key operation.", "error")

        # Always redirect after POST to prevent form resubmission
        return redirect(url_for("index"))

    # Re-read key in case it was created or deleted
    pubkey = read_public_key()
    return render_template("index.html", pubkey=pubkey,messages=get_flashed_messages())

@app.route("/download_private_key")
def download_private_key():
    if os.path.exists(PRIVATE_KEY):
        return send_file(PRIVATE_KEY, as_attachment=True)
    else:
        flash("Private key not found.", "error")
        return redirect(url_for("index"))

if __name__ == "__main__":
    app.run()

