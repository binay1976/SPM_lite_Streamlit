#!/bin/bash
set -e  # exit immediately on error

CONTAINER_NAME="ML-SPM-SQL"
IMAGE_NAME="ml-spm-sql:latest"
PORT=8050

echo "🔍 Checking if container '$CONTAINER_NAME' is running..."
if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo "🛑 Stopping container '$CONTAINER_NAME'..."
    docker stop $CONTAINER_NAME >/dev/null 2>&1 || true
    docker rm $CONTAINER_NAME >/dev/null 2>&1 || true
else
    echo "ℹ️ No running container named '$CONTAINER_NAME'."
fi

echo "🚀 Starting new container '$CONTAINER_NAME' on port $PORT..."
docker run -d \
  -p ${PORT}:${PORT} \
  --env DB_HOST=10.3.19.46 \
  --env DB_PORT=3307 \
  --env DB_USER=spmuser \
  --env DB_PASSWORD=yourpassword \
  --env DB_NAME=ml_spm_app \
  --name ${CONTAINER_NAME} \
  --restart unless-stopped \
  ${IMAGE_NAME}

echo "✅ Container '$CONTAINER_NAME' is now running on port ${PORT}."
