#!/bin/bash
# Generates a self-signed CA and a broker certificate for local SASL_SSL testing.
# Only requires openssl. Output goes to docker/certs/.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="$SCRIPT_DIR/certs"
PASSWORD="changeit"
VALIDITY=365

mkdir -p "$CERTS_DIR"

echo "→ Generating CA key and self-signed certificate..."
openssl req -new -x509 \
    -keyout "$CERTS_DIR/ca.key" \
    -out    "$CERTS_DIR/ca.crt" \
    -days $VALIDITY -nodes \
    -subj "/CN=LocalKafkaCA/OU=Dev/O=Test/C=ES"

echo "→ Generating broker private key and CSR..."
openssl req -new \
    -keyout "$CERTS_DIR/broker.key" \
    -out    "$CERTS_DIR/broker.csr" \
    -nodes \
    -subj "/CN=localhost/OU=Dev/O=Test/C=ES"

echo "→ Signing broker certificate with CA..."
openssl x509 -req \
    -in  "$CERTS_DIR/broker.csr" \
    -CA  "$CERTS_DIR/ca.crt" \
    -CAkey "$CERTS_DIR/ca.key" \
    -CAcreateserial \
    -out "$CERTS_DIR/broker.crt" \
    -days $VALIDITY

echo "→ Packaging broker cert + key into PKCS12 keystore..."
openssl pkcs12 -export \
    -in    "$CERTS_DIR/broker.crt" \
    -inkey "$CERTS_DIR/broker.key" \
    -chain -CAfile "$CERTS_DIR/ca.crt" \
    -name broker \
    -out  "$CERTS_DIR/kafka.keystore.p12" \
    -passout pass:$PASSWORD

echo "→ Packaging CA cert into PKCS12 truststore..."
openssl pkcs12 -export \
    -nokeys \
    -in   "$CERTS_DIR/ca.crt" \
    -name ca \
    -out  "$CERTS_DIR/kafka.truststore.p12" \
    -passout pass:$PASSWORD

echo "→ Writing password credential file..."
echo -n "$PASSWORD" > "$CERTS_DIR/keystore.password"

echo "→ Copying JAAS config..."
cp "$(dirname "$0")/kafka_server_jaas.conf" "$CERTS_DIR/kafka_server_jaas.conf"

echo ""
echo "✅ Certificates ready in $CERTS_DIR/"
echo "   Broker keystore  : kafka.keystore.p12   (password: $PASSWORD)"
echo "   Broker truststore: kafka.truststore.p12 (password: $PASSWORD)"
echo "   CA cert (client) : ca.crt"
echo ""
echo "Before running the MCP server, export:"
echo "   export KAFKA_SSL_CA_LOCATION=$CERTS_DIR/ca.crt"
