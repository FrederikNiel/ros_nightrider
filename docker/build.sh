#!/bin/bash

# build.sh - Build script for ros_event_camera image
# This script builds the Docker image using the ros_event_camera compose service.

set -e

echo "Building ros_event_camera image..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the docker directory
cd "$SCRIPT_DIR"

# Build the image
docker compose --file docker-compose.yaml build ros_event_camera

echo "✅ ros_event_camera image built successfully!"
echo ""
echo "To run the container:"
echo "  docker compose -f docker-compose.yaml up ros_event_camera"
echo ""
echo "To run in detached mode:"
echo "  docker compose -f docker-compose.yaml up -d ros_event_camera"
echo ""
echo "To stop the container:"
echo "  docker compose -f docker-compose.yaml down"
