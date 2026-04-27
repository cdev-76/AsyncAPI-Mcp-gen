#!/bin/bash

if [ -z "$1" ]; then
    echo "Error: no YAML file specified."
    echo "Usage: ./run_asyncapi_generator.sh <spec.yaml> [serverName]"
    echo "Example: ./run_asyncapi_generator.sh streets-lights.yaml scram-connections"
    exit 1
fi

YAML_FILE="$1"
SERVER_NAME="$2"

echo "Generating MCP server from $YAML_FILE ..."

if [ -n "$SERVER_NAME" ]; then
    echo "Using AsyncAPI server: $SERVER_NAME"
    asyncapi generate fromTemplate "$YAML_FILE" ./ \
        -o ./generated-code \
        --force-write \
        --param server="$SERVER_NAME"
else
    echo "No server specified — using first server in the spec"
    asyncapi generate fromTemplate "$YAML_FILE" ./ \
        -o ./generated-code \
        --force-write
fi

echo "Generation complete."
