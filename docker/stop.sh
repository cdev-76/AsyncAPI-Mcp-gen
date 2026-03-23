#!/bin/bash

echo "Select the stack to stop:"
echo "  1) SCRAM / mTLS  (docker-compose.yml)"
echo "  2) OAuth2        (docker-compose-oauth.yml)"
read -rp "Option [1/2]: " option

case "$option" in
  1)
    COMPOSE_FILE="docker-compose.yml"
    ;;
  2)
    COMPOSE_FILE="docker-compose-oauth.yml"
    ;;
  *)
    echo "Invalid option. Exiting."
    exit 1
    ;;
esac

echo "Stopping $COMPOSE_FILE..."
docker compose -f "./$COMPOSE_FILE" down
