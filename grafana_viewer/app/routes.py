# app/routes.py
from flask import current_app, render_template, jsonify, request, abort
import yaml
import os
from urllib.parse import urlencode
from . import app  # use the global app instance from __init__

# --- helpers ---------------------------------------------------------------

def _remote_user() -> str:
    """OOD typically sets REMOTE_USER; fallback to header or 'anonymous'."""
    return (
        request.environ.get("REMOTE_USER")
        or request.headers.get("X-Forwarded-User")
        or "anonymous"
    )

def _load_rbac():
    path = current_app.config["RBAC_FILE"]
    if os.path.exists(path):
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}

def _allowed_for(user: str, dashboards):
    """
    Optional minimal RBAC via config/rbac.yaml.
    If file missing/empty -> allow all.
    Structure:
      users:
        alice:
          dashboards: [uid1, uid2]
          folders: [folderUidX]
          tags: [public]
      default:
        tags: [public]
    """
    rbac = _load_rbac()
    users = rbac.get("users", {})
    rules = users.get(user, rbac.get("default", {}))
    uids = set(rules.get("dashboards", []) or [])
    folders = set(rules.get("folders", []) or [])
    tags = set(rules.get("tags", []) or [])

    if not (uids or folders or tags):
        return dashboards

    allowed = []
    for d in dashboards:
        if (
            (d.get("uid") in uids)
            or (d.get("folderUid") in folders)
            or (tags and set(d.get("tags", [])).intersection(tags))
        ):
            allowed.append(d)
    return allowed

# --- routes ----------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", title=current_app.config["APP_TITLE"])


@app.route("/embed/<uid>")
def embed(uid: str):
    """Render a wrapper page with an iframe pointing to Grafana."""
    base = current_app.config["GRAFANA_EMBED_BASE_URL"]
    org = current_app.config["GRAFANA_ORG_ID"]
    refresh = request.args.get("refresh", current_app.config["DEFAULT_REFRESH"])
    nfrom = request.args.get("from", current_app.config["DEFAULT_FROM"])
    nto = request.args.get("to", current_app.config["DEFAULT_TO"])
    title = request.args.get("title", f"Dashboard {uid}")

    q = urlencode({"orgId": org, "refresh": refresh, "from": nfrom, "to": nto})
    url = f"{base}/d/{uid}?{q}"
    #page_title = f"Dashboard {uid}"
    return render_template("embed.html", title=title, iframe_src=url)


@app.route("/embed/img/<uid>")
def embed_image_grid(uid: str):
    """
    Render PNG images for each panel.
    """
    base = current_app.config["GRAFANA_EMBED_BASE_URL"]
    org = current_app.config["GRAFANA_ORG_ID"]
    title = request.args.get("title", f"Dashboard {uid}")
  
    panel_ids = request.args.get("panelIds", "")
    images = []
    if panel_ids:
        for pid in [p for p in panel_ids.split(",") if p.isdigit()]:
            images.append({
                "panel_id": int(pid),
                "url": f"{base}/render/d-solo/{uid}?orgId={org}&panelId={pid}&width=1100&height=500&scale=1"
            })
    else:
        images.append({
            "panel_id": None,
            "url": f"{base}/render/d/{uid}?orgId={org}&width=1920&height=1080&scale=1"
        })

    return render_template(
        "image_grid.html",
        title=title,
        images=images,
        uid=uid,
        full_url=f"{base}/d/{uid}?orgId={org}"
    )


@app.route("/debug/env")
def debug_env():
    keys = [
        "REMOTE_USER",
        "HTTP_X_FORWARDED_USER",
        "HTTP_X_REMOTE_USER",
        "HTTP_REMOTE_USER",
        "HTTP_OIDC_CLAIM_PREFERRED_USERNAME",
        "HTTP_OIDC_CLAIM_EMAIL",
        "HTTP_AUTHORIZATION",
    ]
    out = {k: request.environ.get(k) for k in keys}
    out.update({
        "hdr_X-Forwarded-User": request.headers.get("X-Forwarded-User"),
        "hdr_X-Remote-User": request.headers.get("X-Remote-User"),
    })
    return jsonify(out)

