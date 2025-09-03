# SSH key manager
This is an experimental passenger application that allows users to manage ssh keys through Open Ondemand.

**WARNING:** This project is in very early development stage.

## Requirements
- Open OnDemand server
- Python 3 

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

## Usage in Open OnDemand
Once the app is installed:
- Go to the OOD Dashboard.
- Open the app, you will be able to add, delete and download the ssh keys.

