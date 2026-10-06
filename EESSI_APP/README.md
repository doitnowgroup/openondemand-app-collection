# EESSI Open OnDemand App
This Open OnDemand interactive app integrates with the EESSI project to expose available software modules provided through EESSI.
Users can browse and select desired modules from the EESSI environment, then launch a remote desktop session preloaded with those selected modules.

## Requirements
- Open OnDemand server
- Python 3 (tested with Python 3.6.8)
- Flask (tested with flask 2.0.3)
- EESSI properly set up in both, OOD node and Compute Node

## Setup
Copy this app into your OOD apps directory:
```
/var/www/ood/apps/sys/   # system-wide
$HOME/ondemand/dev/      # personal sandbox
```

# Copy the service unit in the node that will run this service, can be the OOD or other compute node with EESSI available
```
cp modules_service/ood-eessi-modules.service /etc/systemd/system/

# Enable and start the service
systemctl daemon-reload
systemctl enable --now ood-eessi-modules.service

# Verify it is running
systemctl status ood-eessi-modules.service
```
SSL certificates (cert.pem / key.pem) are generated automatically in the modules_service/ working directory on first start. They are reused on subsequent restarts.
This will start a local HTTPS service (self-signed certificates) on:
```
https://<server-ip>:5000/modules
```
Now you will need to configure the IP of the machine running the service in the OOD App. For this you should modify "form.js" and search for *// Load modules* section.
```
url: 'https://X.X.X.X:5000/modules',
```

## Usage in Open OnDemand
Once the app is installed:
- Go to the OOD Dashboard.
- Select the app, choose the modules you want from the filtered list, and configure the job (e.g., project).
- Submit a Desktop job.
- After the remote desktop session starts, the selected modules will be available in your environment.
