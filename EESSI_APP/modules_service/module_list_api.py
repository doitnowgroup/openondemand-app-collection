"""
modules_api.py — Flask API to list available EESSI modules on HPC systems.
Designed to run under Gunicorn as a systemd service.

Module discovery strategy
--------------------------
Instead of parsing the text output of 'module avail' (fragile and slow),
$MODULEPATH is obtained directly from the EESSI environment and the
filesystem is scanned for .lua files (Lmod format).

Each MODULEPATH entry is automatically classified into one of these
origin categories:
  - "eessi"            → /cvmfs/software.eessi.io/versions/*/…/modules/all
  - "host_injections"  → /cvmfs/software.eessi.io/host_injections/…
  - "site"             → any other path (cluster-local modules)

Lmod module directory structure:
  <modulepath>/
    Python/
      3.12.3-GCCcore-13.3.0.lua   → module "Python/3.12.3-GCCcore-13.3.0"
    GCC/
      13.3.0.lua                  → module "GCC/13.3.0"
    lmod.lua                      → root module "lmod" (no version subdirectory)
"""

import logging
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Optional, Union

from flask import Flask, jsonify, request
from flask_cors import CORS

# ---------------------------------------------------------------------------
# Configuration via environment variables
# ---------------------------------------------------------------------------

EESSI_INIT         = os.getenv("EESSI_INIT", "/cvmfs/software.eessi.io/versions/2025.06/init/bash")
CACHE_TTL          = int(os.getenv("CACHE_TTL", "3600"))   # 1 hour — modules rarely change
SUBPROCESS_TIMEOUT = int(os.getenv("SUBPROCESS_TIMEOUT", "60"))
ALLOWED_ORIGINS    = os.getenv("ALLOWED_ORIGINS", "*")
LOG_LEVEL          = os.getenv("LOG_LEVEL", "INFO")
MAX_SEARCH_LEN     = 100

# Origin classification rules for MODULEPATH entries.
# Order matters: evaluated top-to-bottom, first match wins.
_ORIGIN_RULES: list[tuple[str, str]] = [
    ("/cvmfs/software.eessi.io/host_injections", "host_injections"),
    ("/cvmfs/software.eessi.io",                 "eessi"),
]

# ---------------------------------------------------------------------------
# Logging (Gunicorn redirects this to its own log)
# ---------------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
)
log = logging.getLogger("modules_api")

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app, origins=ALLOWED_ORIGINS)

# ---------------------------------------------------------------------------
# In-memory cache with TTL
# ---------------------------------------------------------------------------

_cache: dict = {}


def cache_get(key: str):
    entry = _cache.get(key)
    if entry and time.monotonic() < entry["expires_at"]:
        return entry["data"]
    return None


def cache_set(key: str, data, ttl: int = CACHE_TTL):
    if ttl > 0:
        _cache[key] = {"data": data, "expires_at": time.monotonic() + ttl}


def cache_invalidate(key: str = None):
    if key:
        _cache.pop(key, None)
    else:
        _cache.clear()

# ---------------------------------------------------------------------------
# Module discovery — filesystem-based
# ---------------------------------------------------------------------------

def _classify_origin(path: str) -> str:
    """Returns the origin category for a given MODULEPATH entry."""
    for prefix, label in _ORIGIN_RULES:
        if path.startswith(prefix):
            return label
    return "site"


def _get_modulepath() -> list:
    """
    Sources EESSI and captures $MODULEPATH.
    Returns a list of dicts: [{"path": str, "origin": str}, ...]
    Only includes paths that exist on the filesystem.
    """
    command = (
        f"source {EESSI_INIT} > /dev/null 2>&1 && "
        f"echo \"$MODULEPATH\""
    )
    log.info("Fetching MODULEPATH from EESSI...")

    try:
        result = subprocess.run(
            command,
            shell=True,
            executable="/bin/bash",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=SUBPROCESS_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"EESSI source command exceeded timeout of {SUBPROCESS_TIMEOUT}s.")

    raw = result.stdout.strip()
    if not raw:
        raise RuntimeError("MODULEPATH is empty after sourcing EESSI. Check EESSI_INIT.")

    paths = []
    for p in raw.split(":"):
        p = p.strip()
        if not p:
            continue
        origin = _classify_origin(p)
        exists = Path(p).is_dir()
        log.debug("MODULEPATH entry: %s [origin=%s, exists=%s]", p, origin, exists)
        if exists:
            paths.append({"path": p, "origin": origin})
        else:
            log.warning("MODULEPATH entry does not exist on filesystem: %s", p)

    if not paths:
        raise RuntimeError("No accessible MODULEPATH entries found.")

    log.info("Active module paths: %d", len(paths))
    return paths


def _scan_modulepath(entry: dict) -> list:
    """
    Scans an Lmod module directory and returns the list of modules found.

    Expected structure (Lmod):
      <modulepath>/
        <name>/
          <version>.lua    →  module "<name>/<version>"
        <name>.lua         →  root module "<name>" (no version subdirectory)

    Each returned module dict contains:
      {
        "name":    str,        # base name (e.g. "Python")
        "version": str|None,
        "full":    str,        # "Python/3.12.3-GCCcore-13.3.0"
        "origin":  str,        # "eessi" | "host_injections" | "site"
        "path":    str,        # source MODULEPATH entry
      }
    """
    root = Path(entry["path"])
    origin = entry["origin"]
    modules = []

    for item in root.iterdir():
        if item.is_dir():
            # Directory → each .lua file inside is a version
            for lua in item.glob("*.lua"):
                version = lua.stem  # filename without .lua extension
                modules.append({
                    "name":    item.name,
                    "version": version,
                    "full":    f"{item.name}/{version}",
                    "origin":  origin,
                    "path":    str(root),
                })
        elif item.suffix == ".lua":
            # .lua file at root level → module with no version subdirectory
            modules.append({
                "name":    item.stem,
                "version": None,
                "full":    item.stem,
                "origin":  origin,
                "path":    str(root),
            })

    return modules


def _discover_all_modules() -> dict:
    """
    Main entry point. Returns the full module catalogue:
    {
      "modules":   [{"full", "name", "version", "origin", "path"}, ...],
      "sources":   [{"path", "origin", "count"}, ...],
    }
    Duplicate modules (same 'full' name across multiple paths) are kept only
    once, giving priority to MODULEPATH order (first = highest priority,
    matching Lmod behaviour).
    """
    entries  = _get_modulepath()
    seen     = set()
    modules  = []
    sources  = []

    for entry in entries:
        batch = _scan_modulepath(entry)
        count = 0
        for mod in batch:
            key = mod["full"].lower()
            if key not in seen:
                seen.add(key)
                modules.append(mod)
                count += 1
        sources.append({
            "path":   entry["path"],
            "origin": entry["origin"],
            "count":  count,
        })
        log.info("  %s [%s] → %d modules", entry["path"], entry["origin"], count)

    modules.sort(key=lambda m: m["full"].lower())
    log.info("Total unique modules discovered: %d", len(modules))

    if not modules:
        raise RuntimeError("No modules found in any MODULEPATH entry.")

    return {"modules": modules, "sources": sources}


# ---------------------------------------------------------------------------
# Cache — full catalogue
# ---------------------------------------------------------------------------

def _get_catalog_cached() -> dict:
    cached = cache_get("catalog")
    if cached is not None:
        log.debug("Serving catalogue from cache.")
        return cached
    catalog = _discover_all_modules()
    cache_set("catalog", catalog)
    return catalog


def _warm_cache():
    """
    Pre-warms the cache in a background thread and refreshes it automatically
    before expiry, so no HTTP request ever has to wait for the costly
    'source EESSI_INIT' subprocess.
    """
    # Brief delay to let Flask finish starting up
    time.sleep(2)
    while True:
        try:
            log.info("Cache warmer: discovering modules in background...")
            catalog = _discover_all_modules()
            cache_set("catalog", catalog)
            log.info("Cache warmer: cache updated (%d modules).", len(catalog["modules"]))
        except Exception as e:
            log.error("Cache warmer: failed to update cache: %s", e)

        # Refresh at 80% of TTL to never serve an expired cache
        sleep_for = max(60, int(CACHE_TTL * 0.8))
        log.info("Cache warmer: next refresh in %ds.", sleep_for)
        time.sleep(sleep_for)


def _get_modules_cached() -> list:
    return _get_catalog_cached()["modules"]


def _base(module: Union[dict, str]) -> str:
    if isinstance(module, dict):
        return module["name"]
    return module.split("/")[0]


def _version(module: Union[dict, str]) -> Optional[str]:
    if isinstance(module, dict):
        return module.get("version")
    parts = module.split("/", 1)
    return parts[1] if len(parts) > 1 else None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def api_response(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 400
        except RuntimeError as e:
            return jsonify({"success": False, "error": str(e)}), 404
        except Exception:
            log.exception("Unexpected error in %s", f.__name__)
            return jsonify({"success": False, "error": "Internal server error."}), 500
    return wrapper


def _meta(items: list) -> dict:
    return {
        "total": len(items),
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "cached_until": (
            datetime.fromtimestamp(
                _cache["catalog"]["expires_at"], tz=timezone.utc
            ).isoformat()
            if "catalog" in _cache else None
        ),
    }

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """API index — useful for checking the service is up from a browser."""
    return jsonify({
        "service": "EESSI Modules API",
        "status":  "ok",
        "endpoints": [
            "GET  /health",
            "GET  /modules",
            "GET  /modules/search?q=<term>",
            "GET  /modules/categories",
            "GET  /modules/sources",
            "GET  /modules/<name>",
            "POST /cache/invalidate",
        ],
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now(tz=timezone.utc).isoformat()})


@app.route("/modules")
@api_response
def get_modules():
    """
    Lists all available modules.
    Optional query params:
      - category (str): filter by exact base name  (e.g. ?category=Python)
      - origin   (str): filter by origin           (eessi | host_injections | site)
    """
    category = request.args.get("category", "").strip()
    origin   = request.args.get("origin",   "").strip()

    for param, val in [("category", category), ("origin", origin)]:
        if len(val) > MAX_SEARCH_LEN:
            raise ValueError(f"'{param}' cannot exceed {MAX_SEARCH_LEN} characters.")

    modules = _get_modules_cached()

    if category:
        modules = [m for m in modules if m["name"].lower() == category.lower()]
    if origin:
        modules = [m for m in modules if m["origin"].lower() == origin.lower()]

    return jsonify({
        "success": True,
        "modules": [m["full"] for m in modules],
        "meta":    _meta(modules),
    })


@app.route("/modules/search")
@api_response
def search_modules():
    """
    Partial case-insensitive search across full module names.
    Query params:
      - q      (str, required): search term
      - origin (str, optional): filter by origin
    """
    query  = request.args.get("q",      "").strip()
    origin = request.args.get("origin", "").strip()

    if not query:
        raise ValueError("Parameter 'q' is required.")
    if len(query) > MAX_SEARCH_LEN:
        raise ValueError(f"'q' cannot exceed {MAX_SEARCH_LEN} characters.")

    modules = _get_modules_cached()
    results = [m for m in modules if query.lower() in m["full"].lower()]
    if origin:
        results = [m for m in results if m["origin"].lower() == origin.lower()]

    return jsonify({
        "success": True,
        "query":   query,
        "modules": [m["full"] for m in results],
        "meta":    _meta(results),
    })


@app.route("/modules/categories")
@api_response
def get_categories():
    """
    Returns unique base names (without version). Useful for building UI filters.
    Optional query params:
      - origin (str): filter by origin before grouping
    """
    origin  = request.args.get("origin", "").strip()
    modules = _get_modules_cached()
    if origin:
        modules = [m for m in modules if m["origin"].lower() == origin.lower()]
    cats = sorted({m["name"] for m in modules})
    return jsonify({
        "success":    True,
        "categories": cats,
        "meta": {"total": len(cats), "timestamp": datetime.now(tz=timezone.utc).isoformat()},
    })


@app.route("/modules/sources")
@api_response
def get_sources():
    """
    Returns active MODULEPATH entries, their classified origin,
    and how many unique modules each one contributes.
    Useful for debugging and auditing active module paths.
    """
    catalog = _get_catalog_cached()
    return jsonify({
        "success": True,
        "sources": catalog["sources"],
        "meta": {
            "total_paths":   len(catalog["sources"]),
            "total_modules": len(catalog["modules"]),
            "timestamp":     datetime.now(tz=timezone.utc).isoformat(),
        },
    })


@app.route("/modules/<path:name>")
@api_response
def get_module_info(name: str):
    """
    Returns information about a module or module family.
      /modules/Python                           → all versions of Python
      /modules/Python/3.12.3-GCCcore-13.3.0    → exact module match
    """
    if len(name) > MAX_SEARCH_LEN:
        raise ValueError(f"Module name cannot exceed {MAX_SEARCH_LEN} characters.")

    modules = _get_modules_cached()

    # Exact match first
    exact = [m for m in modules if m["full"].lower() == name.lower()]
    if exact:
        return jsonify({"success": True, "module": exact[0]})

    # Fall back to family match by base name
    family = [m for m in modules if m["name"].lower() == name.lower()]
    if not family:
        raise RuntimeError(f"Module '{name}' not found.")

    return jsonify({
        "success":  True,
        "base":     name,
        "versions": family,
        "meta":     _meta(family),
    })


@app.route("/cache/invalidate", methods=["POST"])
@api_response
def invalidate_cache():
    cache_invalidate()
    log.info("Cache invalidated manually.")
    return jsonify({"success": True, "message": "Cache cleared."})


# ---------------------------------------------------------------------------
# Entry point (direct execution: python3 modules_api.py)
# When running under Gunicorn this block is never executed.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ssl_cert = os.getenv("SSL_CERT", "cert.pem")
    ssl_key  = os.getenv("SSL_KEY",  "key.pem")
    port     = int(os.getenv("PORT", "5000"))

    # Option 1: use existing certificates on disk
    if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        ssl_context = (ssl_cert, ssl_key)
        log.info("SSL: using certificates at %s / %s", ssl_cert, ssl_key)

    # Option 2: generate a self-signed certificate with openssl
    else:
        log.info("SSL: certificates not found, generating self-signed...")
        try:
            import subprocess as _sp
            _sp.run([
                "openssl", "req", "-x509", "-nodes",
                "-newkey", "rsa:2048",
                "-keyout", ssl_key,
                "-out",    ssl_cert,
                "-days",   "3650",
                "-subj",   "/C=ES/ST=Galicia/O=HPC/CN=localhost",
                "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
            ], check=True, capture_output=True)
            ssl_context = (ssl_cert, ssl_key)
            log.info("SSL: certificates generated → %s / %s", ssl_cert, ssl_key)
        except Exception as e:
            log.warning("SSL: could not generate certificate (%s) — falling back to 'adhoc'", e)
            ssl_context = "adhoc"   # requires: pip install pyopenssl

    # Background cache warmer thread
    # daemon=True → thread dies automatically when the main process exits
    t = threading.Thread(target=_warm_cache, daemon=True, name="cache-warmer")
    t.start()
    log.info("Cache warmer started in background.")

    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=port,
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
        use_reloader=False,   # debug reloader interferes with systemd
        ssl_context=ssl_context,
    )
