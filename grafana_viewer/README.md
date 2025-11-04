# Grafana Viewer
Grafana Viewer is an [Open OnDemand Passenger application](https://osc.github.io/ood-documentation/latest/tutorials/tutorials-passenger-apps.html) developed by [DO IT NOW](https://www.doitnowgroup.com/).

DO IT NOW provides advanced supercomputing services for scientists and engineers, offering turnkey solutions and technologies for addressing the most complex challenges in High Performance Computing (HPC).
The DIN team has extensive expertise across multiple fields, delivering best-in-class services in cluster design, supercomputer administration, user support, and more.

This application was originally created to integrate with the Do IT Now Monitoring Stack, a high-performance monitoring suite built on Grafana, Prometheus, and ElasticSearch for unified monitoring of HPC clusters, compute nodes, and service health.
You can watch the DIN Monitoring Stack overview video here: [Job Efficiency Monitoring](https://www.youtube.com/watch?v=vnBTxVuNSEA&t=870s)

Grafana Viewer serves as a bridge between the OOD portal and a shared Grafana instance, providing a simple Flask-based web interface for users to list available dashboards, view embedded Grafana pages, or render panel images.

You can include basic LDAP user mapping for dashboard access control via Grafana teams and folders when using this app.


## Requirements

- **Open OnDemand** server  
- **Python 3.x**
- **Grafana** instance (tested with v9.5.3)  
- **Grafana Image Renderer** plugin (v3.10.1)  
- **LDAP server** required for user mapping and access control 
- **Reverse proxy** for shared authentication between OOD and Grafana

## Setup

### 1. Copy the Application
Copy this app into your OOD apps directory:
```
/var/www/ood/apps/sys/   # system-wide
$HOME/ondemand/dev/      # personal sandbox
```

### 2. Create a Python Virtual Environment
To create the environment, execute the following command the app folder: 
```
bash create_python_venv.sh
```
This will automatically set up a `python-venv` directory, which contains the required Python packages for running the Flask application.

### 3. Configure Environment Variables
Set the necessary environment variables, for example:
```
GRAFANA_EMBED_BASE_URL="https://www.ooddemo.com/_grafana/"
GRAFANA_ORG_ID="1"
```
Here `GRAFANA_EMBED_BASE_URL` is the base URL used by the browser to load embedded Grafana dashboards. 

`GRAFANA_ORG_ID` is the organization defined in Grafana. This app currently supports only a single Grafana organization.

Ensure Grafana is reverse-proxied under the same OOD domain to share the authentication session. You can add the reverse proxy in OOD configuration file `/opt/ood/ood-portal-generator/templates/ood-portal.conf.erb`. 
Below is an example:
```
  <Location "/_grafana/">
    <%- @auth.each do |line| -%>
    <%= line %>
    <%- end -%>

    ProxyPreserveHost On
    RewriteEngine On
    RequestHeader unset X-WEBAUTH-USER early
    RequestHeader unset X-Forwarded-User early
    RequestHeader unset X-Remote-User early
    RewriteCond %{LA-U:REMOTE_USER} ^\s*$ [OR]
    RewriteCond %{LA-U:REMOTE_USER} ^(null|undefined)$ [NC]
    RewriteRule ^ - [E=BAD_USER:1,NS]

    RewriteCond %{LA-U:REMOTE_USER} (.+)
    RewriteRule ^ - [E=PROXY_USER:%1,NS]
    RequestHeader set X-WEBAUTH-USER "%{PROXY_USER}e" env=PROXY_USER
    <RequireAll>
      Require valid-user
      Require env PROXY_USER
    </RequireAll>


    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Prefix "/_grafana"
    RequestHeader set X-Forwarded-Host   "%{Host}i"
    ProxyPass    "http://localhost:3000/"
    ProxyPassReverse  "http://localhost:3000/"

  </Location>
```

### 4. Bootstrap Assets
Bootstrap resources are located under `app/static/vendor/`.  
If you prefer, you can also use Bootstrap directly from a CDN instead of storing the files locally.
For reference, the local directory contains:
```
app/static/vendor/bootstrap.min.css
app/static/vendor/bootstrap.bundle.min.js
```

### 5. Configure Grafana
Enable subpath routing, embedding, authentication proxy, and image rendering in Grafana:
```
# Use subpath under OOD domain
GF_SERVER_ROOT_URL=https://www.ooddemo.com/_grafana/
GF_SERVER_SERVE_FROM_SUB_PATH=true

# Allow embedding
GF_SECURITY_ALLOW_EMBEDDING=true	

# Disable anonymous mode for safety
GF_AUTH_ANONYMOUS_ENABLED=false

# Configure image renderer 
GF_RENDERING_SERVER_URL=http://renderer:8081/render
GF_RENDERING_CALLBACK_URL=http://grafana:3000/
GF_RENDERING_CONCURRENT_RENDER_REQUEST_LIMIT=5

# Enable authentication proxy
GF_AUTH_PROXY_ENABLED=true
GF_AUTH_PROXY_HEADER_NAME=X-WEBAUTH-USER
GF_AUTH_PROXY_HEADER_PROPERTY=username
GF_AUTH_PROXY_AUTO_SIGN_UP=false
GF_AUTH_PROXY_WHITELIST=127.0.0.1,<ood_server_ip_or_network>

# Enable LDAP authentication
GF_AUTH_LDAP_ENABLED=true
GF_AUTH_LDAP_CONFIG_FILE=/etc/grafana/ldap.toml
GF_AUTH_LDAP_ALLOW_SIGN_UP=true
```

### 6. Configure LDAP Authentication
Grafana can integrate with LDAP for user authentication and mapping.  
Below is a minimal example configuration (`/etc/grafana/ldap.toml`):
```
[[servers]]
host = "ldap.example.org"
port = 636
use_ssl = true
ssl_skip_verify = false

search_filter = "(uid=%s)"
search_base_dns = ["ou=People,dc=example,dc=org"]

[servers.attributes]
name      = "cn"
surname   = "sn"
username  = "uid"
email     = "mail"

group_search_filter = "(&(objectClass=posixGroup)(memberUid=%s))"
group_search_base_dns = ["ou=Groups,dc=example,dc=org"]

[[servers.group_mappings]]
group_dn = "cn=grafana-admins,ou=Groups,dc=example,dc=org"
org_role = "Admin"

[[servers.group_mappings]]
group_dn = "*"
org_role = "Viewer"
is_default = true
```
You can adjust these settings according to your directory structure and environment.

After the setup above, dashboard access will follow user account permissions in Grafana.

## Usage in Open OnDemand
Once the app is installed:

1. Go to the OOD Dashboard.

2. Launch and initialize the app.

3. The interface will display a list of Grafana dashboards available to your account.

## Interface Overview

Grafana Viewer provides two modes:

- **Dashboards**: view interactive dashboards in iframes.  
- **Images**: render static PNG panels using the Grafana image renderer.

In Dashboards mode, each item also includes an “Open (Images)” button for quick access to image view.  
You can trim or adjust features as needed based on your environment.

## Caveats

#### 1. Grafana Version Compatibility
- **Grafana 10:** causes a redirect loop when proxied under the OOD subpath. Downgraded to **Grafana 9.5.3** for stability.  
- **Grafana 11 / 12:** not yet tested.

#### 2. Session Handling
- The auth proxy relies on the **OOD session cookie** to assert user identity.  
- It may **not** function correctly in **incognito** or **private browser sessions**.

#### 3. Access Control
- The OOD Grafana Viewer app may support access control via rbac.yaml (not fully implemented yet).  
- Backend authentication: 
    - The app does not use a Grafana service account or API token. 
All Grafana requests are performed in the user’s browser session, relying on the user’s existing authentication (via cookies or reverse proxy headers). 
Therefore, permission enforcement is handled by Grafana itself and optionally by the local config/rbac.yaml.

- LDAP Integration:
    - Open-source Grafana does **not** sync LDAP groups automatically via auth proxy. Manual or scripted group sync is required after first login.  
    - Basic org-level group-to-role mapping is available through `ldap.toml` (Viewer / Editor / Admin).  
    - Enterprise Grafana supports full LDAP → Team synchronization.
  
#### 4. Dashboard and Data Security
- Regular users can **edit queries** in dashboards marked as *editable*.  
    - To prevent cross-access, set dashboards for regular users to **read-only**.  
- To isolate data and queries:
    - Use separate data sources per group.  
    - Manage team access via Grafana folders and team permissions.

#### 5. Organization Scope

- This app currently supports only a single Grafana organization. The organization is defined by the environment variable `GRAFANA_ORG_ID`. 
All dashboards and embeds are loaded using this single org ID. Multi-organization access control or automatic org switching is not yet implemented.