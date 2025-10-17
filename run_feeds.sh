#!/bin/bash
# ===============================================
# 🐳 Script para ejecutar el recolector de feeds
# ===============================================

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Sin color

# Verificar si existe .env, si no, copiar de .env.example
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  No se encontró .env, copiando desde .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ Archivo .env creado. Por favor, revisa y ajusta las variables según tu entorno.${NC}"
fi

# Cargar variables de entorno
if [ -f .env ]; then
    set -a
    source .env
    set +a
    echo -e "${GREEN}✅ Variables de entorno cargadas desde .env${NC}"
fi

echo -e "${GREEN}🐳 Iniciando MySQL...${NC}"
docker compose -f docker/docker-compose.yml up -d mysql

echo -e "${GREEN}⏳ Esperando a que MySQL esté listo...${NC}"
sleep 10

echo -e "${GREEN}📦 Construyendo imagen del feed collector...${NC}"
docker compose -f docker/docker-compose.yml build feed_collector

echo -e "${GREEN}🚀 Ejecutando el recolector de feeds...${NC}"
docker compose -f docker/docker-compose.yml up feed_collector

echo -e "${GREEN}🧹 Limpiando contenedor del feed collector...${NC}"
docker compose -f docker/docker-compose.yml rm -f feed_collector

echo -e "${GREEN}✅ Proceso completado. Los feeds están en ./feeds_data${NC}"
echo -e "${YELLOW}💡 MySQL sigue corriendo. Para detenerlo usa: docker compose -f docker/docker-compose.yml down${NC}"
