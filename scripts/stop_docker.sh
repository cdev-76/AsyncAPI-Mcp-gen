#!/bin/bash
docker container stop kafka-ui
docker container stop kafka_broker
docker container stop schema-registry
yes | docker container prune