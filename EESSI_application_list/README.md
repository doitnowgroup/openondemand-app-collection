# EESSI application list 
This is an experimental passenger application that allows users to browse available apps in EESSI project (v2023.06) through Open Ondemand.

**WARNING:** This project is in very early development stage.

## Requirements
- Open OnDemand server
- Python 3 
- Flask

## Setup
Copy this app into your OOD apps directory:
```
/var/www/ood/apps/sys/   # system-wide
$HOME/ondemand/dev/      # personal sandbox
```
Then create virtual env 
```
bash create_python_venv.sh
```
`utils.py` is the script used for fetching module list in EESSI in advance.

## Usage in Open OnDemand
Once the app is installed:
- Go to the OOD Dashboard.
- Open the app, you will be able to browse, search and read details of the applications in EESSI project.

