#!/bin/bash

echo "Select the stack to launch:"
echo "  1) No security  (docker-compose-plain.yml)  — PLAINTEXT, for local testing"
echo "  2) SCRAM        (docker-compose.yml)         — SASL_SSL with SCRAM-SHA-256"
echo "  3) mTLS         (docker-compose-mtls.yml)    — mutual TLS with client certificates"
echo "  4) OAuth2       (docker-compose-oauth.yml)   — OAUTHBEARER via Keycloak"
read -rp "Option [1/2/3/4]: " option

case "$option" in
  1)
    COMPOSE_FILE="docker-compose-plain.yml"
    ;;
  2)
    COMPOSE_FILE="docker-compose.yml"
    ;;
  3)
    COMPOSE_FILE="docker-compose-mtls.yml"
    ;;
  4)
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
