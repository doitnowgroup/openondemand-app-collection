# app.py
from flask import Flask, redirect

# Create Flask application
MyApp = Flask('create_ssh_credentials_app')

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Required for flash messages in Flask

# Define key paths
SSH_DIR = os.path.expanduser("~/.ssh")
PRIVATE_KEY = os.path.join(SSH_DIR, "id_ed25519")
PUBLIC_KEY = PRIVATE_KEY + ".pub"

# Function to create an SSH key pair if it doesn't exist
def create_ssh_key():
    os.makedirs(SSH_DIR, exist_ok=True)
    subprocess.run([
        "ssh-keygen", "-t", "ed25519", "-f", PRIVATE_KEY, "-N", "", "-q"
    ], check=True)  # Run ssh-keygen command
    os.chmod(PRIVATE_KEY, 0o600)  # Set correct permissions
    os.chmod(SSH_DIR, 0o700)

# Function to delete the SSH key pair
def delete_ssh_key():
    if os.path.exists(PRIVATE_KEY):
        os.remove(PRIVATE_KEY)
    if os.path.exists(PUBLIC_KEY):
        os.remove(PUBLIC_KEY)

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
    return render_template("index.html.erb", pubkey=pubkey)

if __name__ == "__main__":
    MyApp.run()

