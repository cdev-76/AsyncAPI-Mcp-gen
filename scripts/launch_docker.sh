#!/bin/bash
docker compose -f ../docker/docker-compose.yml down -v
docker compose -f ../docker/docker-compose.yml up -d