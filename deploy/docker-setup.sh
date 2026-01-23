#!/bin/bash
# Docker setup script for backend-api production deployment
# Run this script once on the server to prepare Docker environment

set -e

# Configuration
CONFIG_DIR="/home/funq/config/backend-api"
PROJECT_DIR="/home/funq/dev/backend-api"
NETWORK_NAME="funq-network"
POSTGRES_CONTAINER="postgres"

echo "=== Backend-API Docker Setup ==="

# 1. Create Docker network if not exists
echo "1. Setting up Docker network..."
if ! docker network ls | grep -q "$NETWORK_NAME"; then
    docker network create "$NETWORK_NAME"
    echo "   Created network: $NETWORK_NAME"
else
    echo "   Network $NETWORK_NAME already exists"
fi

# 2. Connect postgres to the network if not already connected
echo "2. Connecting PostgreSQL container to network..."
if docker ps -q -f name="$POSTGRES_CONTAINER" | grep -q .; then
    if ! docker network inspect "$NETWORK_NAME" | grep -q "$POSTGRES_CONTAINER"; then
        docker network connect "$NETWORK_NAME" "$POSTGRES_CONTAINER"
        echo "   Connected $POSTGRES_CONTAINER to $NETWORK_NAME"
    else
        echo "   $POSTGRES_CONTAINER already connected to $NETWORK_NAME"
    fi
else
    echo "   Warning: $POSTGRES_CONTAINER container not running"
fi

# 3. Create configuration directory
echo "3. Creating configuration directory..."
mkdir -p "$CONFIG_DIR/firebase"
echo "   Created: $CONFIG_DIR"

# 4. Check for Firebase credentials
echo "4. Checking Firebase credentials..."
if [ -f "$CONFIG_DIR/firebase/firebase-credentials.json" ]; then
    echo "   Firebase credentials found"
else
    echo "   Warning: Firebase credentials not found!"
    echo "   Please copy your firebase-credentials.json to:"
    echo "   $CONFIG_DIR/firebase/firebase-credentials.json"
fi

# 5. Create production .env file if not exists
echo "5. Setting up environment file..."
ENV_FILE="$CONFIG_DIR/.env.prod"
if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << 'EOF'
# Production environment variables for backend-api
# IMPORTANT: Replace placeholder values with actual secrets

# Database
DATABASE_URL=postgresql://postgres:YOUR_DB_PASSWORD@postgres:5432/backend_api

# CORS
CORS_ORIGINS=["https://blog.funq.kr","https://chat.funq.kr","https://calendar.funq.kr"]

# Firebase
GOOGLE_APPLICATION_CREDENTIALS=/app/firebase/firebase-credentials.json

# Anthropic API (Claude)
ANTHROPIC_API_KEY=YOUR_ANTHROPIC_API_KEY
EOF
    echo "   Created $ENV_FILE"
    echo "   IMPORTANT: Edit the file and replace placeholder values!"
else
    echo "   Environment file already exists"
fi

# 6. Authenticate with GHCR (if not already)
echo "6. GitHub Container Registry authentication..."
echo "   To authenticate with GHCR, run:"
echo "   echo \$GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin"

# 7. Print summary
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit $ENV_FILE with your actual credentials"
echo "2. Copy Firebase credentials to $CONFIG_DIR/firebase/"
echo "3. Authenticate with GHCR"
echo "4. Deploy with: cd $PROJECT_DIR && docker compose -f docker-compose.prod.yml up -d"
echo ""
echo "To check status:"
echo "  docker ps"
echo "  docker logs backend-api"
echo "  curl http://localhost:8000/health"
