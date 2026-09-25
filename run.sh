#!/bin/bash
# ===============================================
# 🎯 Script centralizado para gestionar feeds
# ===============================================

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # Sin color

# Fuerza actualizar yt-dlp una vez al día en el build (ver docker/Dockerfile)
export YTDLP_DATE=$(date +%F)

# Banner
print_banner() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════╗"
    echo "║     🚀 FEEDS MANAGER - Menu Principal         ║"
    echo "╚════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Descargar BD desde Google Drive
download_db() {
    check_env
    echo -e "${YELLOW}⬇️ Descargando feeds.db desde Google Drive...${NC}"
    if rclone copy gdrive:feeds_backup/feeds.db ./data/; then
        echo -e "${GREEN}✅ Base de datos descargada y actualizada localmente.${NC}"
    else
        echo -e "${RED}❌ Error al descargar. Verifica las variables RCLONE_CONFIG_GDRIVE_* en tu .env.${NC}"
    fi
}

# Subir BD a Google Drive
upload_db() {
    check_env
    echo -e "${YELLOW}⬆️ Subiendo feeds.db a Google Drive...${NC}"
    if rclone copy ./data/feeds.db gdrive:feeds_backup/; then
        echo -e "${GREEN}✅ Base de datos subida correctamente a Drive.${NC}"
    else
        echo -e "${RED}❌ Error al subir. Verifica las variables RCLONE_CONFIG_GDRIVE_* en tu .env.${NC}"
    fi
}

# Menú de Sincronización
sync_menu() {
    echo -e "${BLUE}Sincronización con Google Drive:${NC}\n"
    echo -e "  ${GREEN}1)${NC} ⬇️ Descargar BD (Drive -> Local)"
    echo -e "  ${GREEN}2)${NC} ⬆️ Subir BD (Local -> Drive)"
    echo -e "  ${GREEN}0)${NC} 🔙 Volver"
    echo ""
    read -p "Opción: " sync_opt
    case $sync_opt in
        1) download_db ;;
        2) upload_db ;;
        0) return ;;
        *) echo -e "${RED}Opción inválida${NC}" ;;
    esac
}

# Mostrar menú
show_menu() {
    echo -e "${BLUE}Selecciona una opción:${NC}\n"
    echo -e "  ${GREEN}1)${NC} 📥 Recolectar feeds (normal)"
    echo -e "  ${GREEN}2)${NC} 🔄 Recolectar feeds (forzar descarga del día)"
    echo -e "  ${GREEN}3)${NC} 🔄 Publicacion automatica de feeds del día"
    echo -e "  ${GREEN}4)${NC} 🖼️ Post-procesar imágenes (todas las categorías notice)"
    echo -e "  ${GREEN}5)${NC} 🖼️ Post-procesar imágenes (personalizado)"
    echo -e "  ${GREEN}6)${NC} 🔄 Regenerar todos los assets JSON desde BD SQLite"
    echo -e "  ${GREEN}7)${NC} ☁️ Sincronizar BD con Google Drive"
    echo -e "  ${GREEN}0)${NC} ❌ Salir"
    echo ""
}

# Función para verificar si Docker está corriendo
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        return 1
    fi
    return 0
}

# Función para intentar iniciar Docker
start_docker() {
    echo -e "${YELLOW}Intentando iniciar Docker...${NC}"

    # Detectar el sistema operativo
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo -e "${BLUE}Iniciando Docker Desktop en macOS...${NC}"
        open -a Docker

        # Esperar a que Docker esté listo
        echo -e "${YELLOW}Esperando a que Docker esté listo...${NC}"
        local max_attempts=30
        local attempt=0

        while ! docker info > /dev/null 2>&1; do
            attempt=$((attempt + 1))
            if [ $attempt -ge $max_attempts ]; then
                echo -e "${RED}Timeout esperando a que Docker inicie${NC}"
                return 1
            fi
            echo -n "."
            sleep 2
        done
        echo ""
        echo -e "${GREEN}Docker está listo!${NC}"

    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        echo -e "${BLUE}Iniciando Docker en Linux...${NC}"
        sudo systemctl start docker

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Docker iniciado correctamente${NC}"
        else
            echo -e "${RED}Error al iniciar Docker${NC}"
            return 1
        fi
    else
        echo -e "${RED}Sistema operativo no soportado para iniciar Docker automáticamente${NC}"
        echo -e "${YELLOW}Por favor, inicia Docker manualmente${NC}"
        return 1
    fi

    return 0
}

# Verificar .env
check_env() {
    if [ ! -f .env ] && [ -f .env.example ]; then
        echo -e "${YELLOW}⚠️  No se encontró .env, copiando desde .env.example...${NC}"
        cp .env.example .env
        echo -e "${GREEN}✅ Archivo .env creado. Por favor, revisa y ajusta las variables.${NC}"
    fi

    # Cargar variables de entorno
    if [ -f .env ]; then
        set -a
        source .env
        set +a
    fi
}

# Iniciar RSSHub (solo si es necesario)
start_rsshub() {
    echo -e "${GREEN}🐳 Iniciando RSSHub...${NC}"
    docker compose -f docker/docker-compose.yml up -d rsshub
    echo -e "${GREEN}⏳ Esperando a que RSSHub esté listo...${NC}"
    sleep 10
    echo -e "${GREEN}✅ RSSHub iniciado${NC}"
}

# Ejecutar recolector de feeds
run_feeds() {
    local force_arg="$1"

    check_env
    # Solo necesitamos RSSHub, SQLite no requiere Docker
    #start_rsshub

    echo -e "${GREEN}📦 Construyendo imagen del feed collector...${NC}"
    docker compose -f docker/docker-compose.yml build feed_collector

    echo -e "${GREEN}🚀 Ejecutando el recolector de feeds...${NC}"
    
    FORCE_ARG="$force_arg" \
    docker compose -f docker/docker-compose.yml up --abort-on-container-exit --remove-orphans feed_collector

    echo -e "${GREEN}🧹 Limpiando contenedor del feed collector...${NC}"
    docker compose -f docker/docker-compose.yml rm -f feed_collector

    echo -e "${GREEN}✅ Proceso completado. Los feeds están en ./feeds_data${NC}"
    echo -e "${GREEN}📋 Metadata generado en ./assets/metadata.json${NC}"
    echo -e "${CYAN}💾 Base de datos SQLite: ./data/feeds.db${NC}"
}

# Post-procesar imágenes
postprocess_images() {
    local source_type="$1"
    local category="$2"
    local all_flag="$3"
    local limit="$4"

    check_env

    echo -e "${GREEN}📦 Construyendo imagen del feed collector...${NC}"
    docker compose -f docker/docker-compose.yml build feed_collector

    # Construir comando
    local cmd="python src/feed_postprocess_images.py --source-type $source_type"

    if [ "$all_flag" == "true" ]; then
        cmd="$cmd --all"
    elif [ -n "$category" ]; then
        cmd="$cmd --category $category"
    fi

    if [ -n "$limit" ]; then
        cmd="$cmd --limit $limit"
    fi

    echo -e "${GREEN}🖼️  Ejecutando post-procesamiento de imágenes...${NC}"
    echo -e "${CYAN}Comando: $cmd${NC}\n"

    docker compose -f docker/docker-compose.yml run --rm feed_collector sh -c "$cmd"

    echo -e "${GREEN}✅ Post-procesamiento completado${NC}"
}

# Menú de post-procesamiento personalizado
custom_postprocess_menu() {
    echo ""
    echo -e "${BLUE}Post-procesamiento personalizado:${NC}\n"

    read -p "Source Type (por defecto: notice): " source_type
    source_type=${source_type:-notice}

    read -p "Category (deja vacío para todas): " category

    read -p "Límite de feeds (deja vacío para todos): " limit

    echo ""

    if [ -z "$category" ]; then
        postprocess_images "$source_type" "" "true" "$limit"
    else
        postprocess_images "$source_type" "$category" "false" "$limit"
    fi
}

# Regenerar todos los assets JSON desde la BD SQLite
regenerate_assets() {
    check_env

    echo -e "${GREEN}📦 Construyendo imagen del feed collector...${NC}"
    docker compose -f docker/docker-compose.yml build feed_collector

    echo -e "${GREEN}🔄 Regenerando todos los assets JSON desde SQLite...${NC}\n"

    docker compose -f docker/docker-compose.yml run --rm feed_collector python src/regenerate_assets.py

    echo -e "${GREEN}✅ Regeneración completada${NC}"
    echo -e "${CYAN}💾 Base de datos SQLite: ./data/feeds.db${NC}"
}

# Despliega la carpeta assets/ directo a Netlify (sin pasar por git)
deploy_netlify() {
    if [ -z "$NETLIFY_AUTH_TOKEN" ] || [ -z "$NETLIFY_SITE_ID" ]; then
        echo -e "${YELLOW}⚠️  NETLIFY_AUTH_TOKEN / NETLIFY_SITE_ID no configurados en .env, saltando deploy${NC}"
        return 1
    fi

    # Un deploy reemplaza todo el sitio: sin metadata.json se publicaría un sitio vacío
    if [ ! -f assets/metadata.json ]; then
        echo -e "${RED}❌ assets/metadata.json no existe, cancelando deploy para no vaciar el sitio${NC}"
        exit 1
    fi

    echo -e "${YELLOW} Desplegando assets/ a Netlify...${NC}"
    npx --yes netlify-cli deploy --dir=assets --functions=netlify/functions --prod --site="$NETLIFY_SITE_ID" --auth="$NETLIFY_AUTH_TOKEN"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Deploy a Netlify completado${NC}"
    else
        echo -e "${RED}❌ Error al desplegar a Netlify${NC}"
        exit 1
    fi
}

auto_feeds() {
    echo -e "${YELLOW} Ejecutando proceso automatico de publicacion de feeds${NC}"
    run_feeds "--force"
    deploy_netlify
}

# Loop principal
main() {
    # Si se pasa el argumento --auto, ejecutar modo automático
    if [ "$1" == "--auto" ]; then
        echo -e "${YELLOW}🤖 Modo automático iniciado...${NC}"
        
        # En CI/CD (GitHub Actions), Docker ya suele estar listo.
        # Intentamos check_docker, si falla intentamos iniciarlo, pero no es bloqueante si ya estamos en un entorno con Docker.
        if ! check_docker; then
            echo -e "${YELLOW}Docker no detectado, intentando iniciar...${NC}"
            start_docker
        fi

        auto_feeds
        exit $?
    fi

    echo -e "${YELLOW}Verificando Docker...${NC}"

    if ! check_docker; then
        echo -e "${RED}✗ Docker no está corriendo${NC}"
        if ! start_docker; then
            echo -e "${RED}No se pudo iniciar Docker. Saliendo...${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✓ Docker está corriendo${NC}"
    fi

    sleep 1

    while true; do
        clear
        print_banner
        show_menu

        read -p "Opción: " option
        echo ""

        case $option in
            1)
                echo -e "${GREEN}📥 Iniciando recolección de feeds...${NC}\n"
                run_feeds ""
                ;;
            2)
                echo -e "${YELLOW}🔄 Forzando descarga de feeds del día...${NC}\n"
                run_feeds "--force"
                ;;
            3)
                echo -e "${YELLOW}🔄 Publicacion automatica de feeds del día...${NC}\n"
                auto_feeds
                ;;
            4)
                echo -e "${GREEN}🖼️  Post-procesando todas las categorías notice...${NC}\n"
                postprocess_images "notice" "" "true" ""
                ;;
            5)
                custom_postprocess_menu
                ;;
            6)
                echo -e "${CYAN}🔄 Regenerando assets JSON desde SQLite...${NC}\n"
                regenerate_assets
                ;;
            7)
                sync_menu
                ;;
            0)
                echo -e "${CYAN}👋 ¡Hasta luego!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Opción inválida${NC}"
                ;;
        esac

        echo ""
        read -p "Presiona Enter para continuar..."
    done
}

# Ejecutar menú principal pasando argumentos
main "$@"
