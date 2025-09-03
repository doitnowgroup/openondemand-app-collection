# EESSI Open OnDemand App
This is an experimental application that integrates with EESSI to expose and visualize available modules on the HPC nodes.

**WARNING:** This project is in very early development stage.

## Requirements
- Open OnDemand server
- Python 3 (tested with Python 3.6.8)
- Flask (tested with flask 2.0.3)

## Setup
Copy this app into your OOD apps directory:
```
/var/www/ood/apps/sys/   # system-wide
$HOME/ondemand/dev/      # personal sandbox
```
Then run the Flask API.
```
cd /var/www/ood/apps/sys/EESSI_APP/flask_exporter
python3 modules_api.py
```
This will start a local HTTPS service (self-signed certificates) on:
```
https://<server-ip>:5000/modules
```
Since self-signed certificates are used, the first time you access the endpoint you may need to manually accept the certificate by opening `https://<server-ip>:5000/modules`. You should then see a JSON response with the list of modules.

## Usage in Open OnDemand
Once the app is installed:
- Go to the OOD Dashboard.
- Select the app, choose the modules you want from the filtered list, and configure the job (e.g., project).
- Submit a Desktop job.
- After the remote desktop session starts, the selected modules will be available in your environment.
