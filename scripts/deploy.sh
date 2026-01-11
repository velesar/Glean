#!/bin/bash
# Deployment script for Fly.io
# Usage: ./scripts/deploy.sh [--first-time]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Glean Deployment Script ===${NC}"
echo ""

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo -e "${RED}Error: fly CLI is not installed${NC}"
    echo "Install it from: https://fly.io/docs/hands-on/install-flyctl/"
    exit 1
fi

# Check if logged in
if ! fly auth whoami &> /dev/null; then
    echo -e "${YELLOW}Not logged in to Fly.io. Running fly auth login...${NC}"
    fly auth login
fi

# First-time setup
if [ "$1" == "--first-time" ]; then
    echo -e "${YELLOW}First-time deployment setup${NC}"
    echo ""

    # Launch app (creates app and volume)
    echo "Creating Fly.io app..."
    fly launch --no-deploy --copy-config

    # Create persistent volume for SQLite
    echo ""
    echo "Creating persistent volume for database..."
    fly volumes create glean_data --region iad --size 1

    # Generate and set secret key
    echo ""
    echo "Setting secret key..."
    SECRET_KEY=$(openssl rand -hex 32)
    fly secrets set GLEAN_SECRET_KEY="$SECRET_KEY"

    echo ""
    echo -e "${GREEN}First-time setup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Run './scripts/deploy.sh' to deploy the app"
    echo "  2. Optionally set API keys:"
    echo "     fly secrets set ANTHROPIC_API_KEY='your-key'"
    echo ""
    exit 0
fi

# Build and deploy
echo "Building and deploying to Fly.io..."
echo ""

# Run deployment
fly deploy

echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo ""

# Get app URL
APP_URL=$(fly status --json | grep -o '"Hostname":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -n "$APP_URL" ]; then
    echo -e "App URL: ${GREEN}https://${APP_URL}${NC}"
fi

echo ""
echo "Useful commands:"
echo "  fly status       - Check app status"
echo "  fly logs         - View app logs"
echo "  fly ssh console  - SSH into the app"
echo "  fly secrets list - List configured secrets"
