# app/__init__.py
import os
from flask import Flask
import logging
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse
from pathlib import Path

app = Flask(__name__, template_folder="templates")
app.config['TEMPLATES_AUTO_RELOAD'] = True

app.config["APP_TITLE"] = os.environ.get("APP_TITLE", "Grafana Viewer")
#app.config["GRAFANA_API_BASE_URL"] = os.environ.get("GRAFANA_API_BASE_URL").rstrip("/")
app.config["GRAFANA_EMBED_BASE_URL"] = os.environ.get("GRAFANA_EMBED_BASE_URL").rstrip("/")

app.config["GRAFANA_ORG_ID"] = int(os.environ.get("GRAFANA_ORG_ID", "1"))
app.config["RBAC_FILE"] = os.environ.get("RBAC_FILE", os.path.join(os.path.dirname(__file__), "..", "config", "rbac.yaml"))
app.config["DEFAULT_REFRESH"] = os.environ.get("DEFAULT_REFRESH", "10s")
app.config["DEFAULT_FROM"] = os.environ.get("DEFAULT_FROM", "now-1h")
app.config["DEFAULT_TO"] = os.environ.get("DEFAULT_TO", "now")

# For debugging
logger = logging.getLogger(__name__)
LOG_PATH = str(Path.home() / "grafana_viewer.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3)
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)

app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("werkzeug").addHandler(handler)

app.logger.info("==== Grafana Viewer config summary ====")
for key in [
    "GRAFANA_ORG_ID",
    "RBAC_FILE",
    "DEFAULT_REFRESH",
    "DEFAULT_FROM",
    "DEFAULT_TO",
]:
    app.logger.info("%s = %s", key, app.config.get(key))
app.logger.info("========================================")


@app.after_request
def set_csp(resp):
    o = urlparse(app.config["GRAFANA_EMBED_BASE_URL"])
    origin = f"{o.scheme}://{o.hostname}" + (f":{o.port}" if o.port else "")
    csp = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        f"img-src 'self' data: {origin}; "
        f"frame-src 'self' {origin}; "
        f"connect-src 'self' {origin};"
    )
    resp.headers["Content-Security-Policy"] = csp
    return resp

# Register routes
from . import routes  # noqa: E402,F401

