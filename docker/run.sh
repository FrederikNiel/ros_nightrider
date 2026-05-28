#!/usr/bin/env bash

# Enhanced run script for Docker Compose services
# Runs the ros_event_camera service using the stored Docker Compose config.

# --- Configuration ---
COMPOSE_FILE="docker-compose.yaml"
COMPOSE_PROJECT_NAME="ros_event_camera"

# --- Functions ---
print_usage() {
    echo "Usage: $0 [SERVICE]"
    echo ""
    echo "This script runs the ros_event_camera service using Docker Compose."
    echo "If no service is provided, ros_event_camera is started."
    echo ""
    echo "OPTIONS:"
    echo "  --help, -h        Show this help message."
    echo ""
    echo "EXAMPLES:"
    echo "  $0"
    echo "  $0 ros_event_camera"
}

# --- Argument Parsing ---
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    print_usage
    exit 0
fi

# --- Main Logic ---
SERVICE_NAME="${1:-ros_event_camera}"
if [[ "$SERVICE_NAME" == "event_cam" ]]; then
    SERVICE_NAME="ros_event_camera"
fi
CONTAINER_NAME="ros_event_camera"
SERVICES="$SERVICE_NAME"


# --- Service Assembly & Execution ---

echo "[INFO] Running service '$SERVICE_NAME'..."

echo "[INFO] Starting services: $SERVICES"

# Ensure iptable_raw module is loaded (often needed for Docker networking)
sudo modprobe iptable_raw 2>/dev/null || true

# Execute docker compose
COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" docker compose -f "$COMPOSE_FILE" up $SERVICES --detach --build --remove-orphans

# --- Post-run Information ---
echo ""
echo "[INFO] ✅ Launch complete!"
echo "[INFO] Use 'COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME docker compose -f $COMPOSE_FILE logs -f' to view logs of all running services."
echo "[INFO] Use 'COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME docker compose -f $COMPOSE_FILE down' to stop all services."
echo "[INFO] To access the main container, run: docker exec -it ${CONTAINER_NAME} bash"