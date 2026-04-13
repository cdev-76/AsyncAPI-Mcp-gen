#!/bin/bash

# Comprobamos si el usuario ha introducido el parámetro YAML
if [ -z "$1" ]; then
    echo " Error: No has indicado el archivo YAML."
    echo " Uso: ./run_asyncapi_generator.sh <fichero.yaml> [serverName]"
    echo "Ejemplo: ./run_asyncapi_generator.sh streets-lights.yaml scram-connections"
    exit 1
fi

YAML_FILE="$1"
SERVER_NAME="$2"

echo " Generando servidor MCP usando $YAML_FILE ..."

if [ -n "$SERVER_NAME" ]; then
    echo " Usando servidor AsyncAPI: $SERVER_NAME"
    asyncapi generate fromTemplate "$YAML_FILE" ./ \
        -o ./generated-code \
        --force-write \
        --param server="$SERVER_NAME"
else
    echo " Sin server explícito: se usará el primer servidor del YAML"
    asyncapi generate fromTemplate "$YAML_FILE" ./ \
        -o ./generated-code \
        --force-write
fi

echo " ¡Generación completada con éxito!"