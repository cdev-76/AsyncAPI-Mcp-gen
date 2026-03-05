#!/bin/bash
# Registers a SCRAM-SHA-256 user in Kafka once the broker is ready.
# Runs inside the kafka-init container using the INTERNAL (plaintext) listener.
set -e

echo "Waiting for Kafka to be ready..."
until /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9094 --list > /dev/null 2>&1; do
    sleep 2
done

echo "Registering SCRAM-SHA-256 credentials for user: $KAFKA_USERNAME"
/opt/kafka/bin/kafka-configs.sh \
    --bootstrap-server kafka:9094 \
    --alter \
    --add-config "SCRAM-SHA-256=[iterations=8192,password=$KAFKA_PASSWORD]" \
    --entity-type users \
    --entity-name "$KAFKA_USERNAME"

echo "✅ SCRAM user '$KAFKA_USERNAME' registered successfully"
