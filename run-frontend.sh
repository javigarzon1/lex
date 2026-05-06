#!/usr/bin/env bash
# Lanza el frontend Java (Spring Boot) en el puerto 8080.
set -e
cd "$(dirname "$0")/frontend-java"
if command -v mvn >/dev/null 2>&1; then
    mvn spring-boot:run
else
    ./mvnw spring-boot:run
fi
