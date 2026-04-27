#!/bin/bash

echo "Select the stack to launch:"
echo "  1) No security   (docker-compose-plain.yml) — for local testing"
echo "  2) SCRAM / mTLS  (docker-compose.yml)"
echo "  3) OAuth2        (docker-compose-oauth.yml)"
read -rp "Option [1/2/3]: " option

case "$option" in
  1)
    COMPOSE_FILE="docker-compose-plain.yml"
    ;;
  2)
    COMPOSE_FILE="docker-compose.yml"
    ;;
  3)
    COMPOSE_FILE="docker-compose-oauth.yml"
    ;;
  *)
    echo "Invalid option. Exiting."
    exit 1
    ;;
esac

echo "Launching $COMPOSE_FILE..."
docker compose -f "./$COMPOSE_FILE" down -v
docker compose -f "./$COMPOSE_FILE" up -d
