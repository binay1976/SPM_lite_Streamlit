@echo off
echo === Uploading SPM_Docker_GENERAL to Ubuntu Server ===

REM Force CMD mode for SCP

@REM  From UCCC PC to EDPM Server
scp -i "C:\Users\binay\.ssh\EDPM\edpm" -r "C:\Users\binay\Desktop\SPM\EDPM_Server_App_Railnet\SPM_Docker_GENERAL" locospm@10.3.19.46:/home/locospm/MLSPM/Railnet_Docker_Apps
scp -i "C:/Users/tc312/.ssh/edpm_keys/edpm" -r "C:\Users\tc312\Desktop\Python\SPM\Railnet_EDPM-All_in_One\SPM_Docker_GENERAL\*" locospm@10.3.19.46:/home/locospm/MLSPM/Railnet_Docker_Apps


rsync -avz --progress \
-e "ssh -i /c/Users/tc312/.ssh/edpm_keys/edpm" \
/c/Users/tc312/Desktop/Python/SPM/Railnet_EDPM-All_in_One/SPM_Docker_GENERAL/ \
locospm@10.3.19.46:/home/locospm/MLSPM/Railnet_Docker_Apps/


echo === Upload Complete ===
pause






