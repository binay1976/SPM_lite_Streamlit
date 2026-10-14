#!/bin/bash
set -e  # exit immediately on error

REPO="git@github.com:binay1976/SPM_Docker_GENERAL.git"
DIR="SPM_Docker_GENERAL"

# Clone if not exists, else pull latest
if [ ! -d "$DIR" ]; then
    echo "📥 Cloning repository..."
    git clone "$REPO"
else
    echo "🔄 Repository exists, pulling latest changes..."
    cd "$DIR"
    git reset --hard
    git pull origin main || git pull
    cd ..
fi

# Move into repo directory
cd "$DIR"

# Ensure script is executable (needs sudo only if required by permissions)
echo "🔧 Making build script executable..."
chmod +x x_Build_Run_ML_docker.sh

# Run the build + run script
echo "🚀 Running Docker build + run..."
# Use sudo only if Docker requires it
sudo ./x_Build_Run_ML_docker.sh
