# Docker Run Scripts for SPM Analysis App

This repository contains scripts to manage the Docker container for the 
`cris1022/spm-docker-app:latest` image. Scripts are provided for 
both **Windows** and **Linux (Ubuntu)** systems.

---

## 🔧 Prerequisites
- Docker must be installed and running on your system.
- Port '8052' should be free and Exposed.
- Check Docker Version:- docker --version
- Docker Running Status :- docker ps


---

## 📂 Files Included

| File Name                              | Platform | Description                                      |
|----------------------------------------|-------------------------------------------------------------|
| `spm_CICD_docker.bat`                  | Windows  | Stops, removes, pulls latest image, and runs it. |
| `Pull_&_install_spm_docker.sh`         | Ubuntu   | Same as above, but for Ubuntu/Linux.             |
| `run_existing_spm_docker.sh`           | Ubuntu   | Runs container from existing local image only.   |

### ✅ Download Files
"Pull_&_install_spm_docker.sh":- https://drive.google.com/file/d/1z85OTABQ-Oluiq-j2p9rqas232lGp8WX/view?usp=sharing
"run_existing_spm_docker.sh":- https://drive.google.com/file/d/1nIvKIW8m-bdiqksiMFijE6G6AKNYmfax/view?usp=sharing
"spm_CICD_docker.bat":-        https://drive.google.com/file/d/1jx7nIu7GnfIqc1d03tFevAFSFq3ytpya/view?usp=sharing

---

✅ 🖥️ Windows Usage (`spm_CICD_docker.bat`)
### Steps:
1. Double-click or run the script in Command Prompt:

-----------------------------------------------------------------
✅🐧 Ubuntu/Linux Usage (Initial Installation or Update App)
### 1. `Pull_&_install_spm_docker.sh` – Pull new Version & Run
#### Steps:

1) chmod +x Pull_&_install_spm_docker.sh
2) ./Pull_&_install_spm_docker.sh

# -----------------------------------------------------------------

✅🐧 Ubuntu/Linux Usage (Restart App)
### 1. `run_existing_spm_docker.sh` – Run Exiting App
#### Steps:

1) chmod +x run_existing_spm_docker.sh
2) ./run_existing_spm_docker.sh


✅ Run Script Daily at on an Ubuntu server using cron at 17:00 (Step-by-Step): ----------------------------------------------------------
1. Download "Pull_&_install_spm_docker.sh" File
    a. Install gdown on Ubuntu
    b. sudo apt update
    c. sudo apt install python3-pip
    d. cd /Desktop
    e. pip install gdown
    f. Download with gdown :- gdown https://drive.google.com/uc?id=1z85OTABQ-Oluiq-j2p9rqas232lGp8WX
    g. Rename Downloaded File :- mv 'Pull_&_install_spm_docker.sh' pull_install_spm_docker.sh
    h. rm deploy_dhub.sh (To Remove any Another file)


2. Open your terminal and navigate to the folder where your script is Located "Pull_&_install_spm_docker.sh"
    a. cd /path/to/your/script
    b. sudo chmod +x pull_install_spm_docker.sh

3. Open the Crontab Editor
    a. Edit the crontab for your current user:
    b. bash >>>> sudo crontab -e & Select option [1] 
    c. The first time, it might ask you to choose an editor. You can choose nano Option-1 (easy to use).

4. Add the Cron Job
    a. At the bottom of the crontab file, add this line:
    b. 0 19 * * * /path/to/your/script/pull_install_spm_docker.sh >> /var/log/pull_install.log 2>&1

5. Save and Exit
    a. If using nano: Press CTRL + O (save), then Enter, then CTRL + X (exit).

6. Test it Manually First
    a. /home/ubuntu/pull_install_spm_docker.sh

7. Check if Cron is Scheduled
    a. bash >>>> crontab -l

8. Check Output (Optional)
    a. After 19:00 runs, check your log:
    b. bash >>>>> cat /var/log/pull_install.log