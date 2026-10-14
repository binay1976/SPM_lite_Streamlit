#!/bin/bash
set -e  # exit immediately on error

CONTAINER_NAME="Railnet-ML-SPM-GENERAL"
IMAGE_NAME="ml-spm-general:latest"
PORT=8050
HOST_DATA_PATH="/home/locospm/MLSPM/RAw_Data"

echo "🔨 Building Docker image..."
docker build -t $IMAGE_NAME .

echo "🛑 Stopping container '$CONTAINER_NAME'..."
docker stop $CONTAINER_NAME >/dev/null 2>&1 || true
docker rm $CONTAINER_NAME >/dev/null 2>&1 || true

echo "ℹ️ No running container named '$CONTAINER_NAME'."

echo "🚀 Starting new container '$CONTAINER_NAME' on port $PORT..."
docker run -d \
  -p ${PORT}:8050 \
  --env-file .env \
  --name ${CONTAINER_NAME} \
  --restart unless-stopped \
  -v ${HOST_DATA_PATH}:/app/data \
  ${IMAGE_NAME}

echo "✅ Container '$CONTAINER_NAME' is now running on port ${PORT}."

# sudo systemctl restart nginx
# echo "✅ Nginx restarted successfully."

docker exec -it Railnet-ML-SPM-GENERAL env | grep DB_
