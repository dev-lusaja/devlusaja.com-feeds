#!/bin/bash
# ===============================================
# 🤖 Script de Automatización de Feeds
# ===============================================
# Este script automatiza todo el proceso de:
# 1. Descarga de feeds RSS
# 2. Almacenamiento en MySQL
# 3. Generación de archivos JSON
# 4. Commit y push a GitHub
# 5. Despliegue en Netlify (automático)
#
# Diseñado para ejecutarse con cron job
# ===============================================

set -euo pipefail  # Exit on error, undefined variable, or pipe failure

# ============================================
# CONFIGURACIÓN
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Cargar configuración personalizada si existe
CONFIG_FILE="$SCRIPT_DIR/.auto_feeds.config"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# Variables por defecto (pueden ser sobrescritas por .auto_feeds.config)
LOG_DIR="${LOG_DIR:-$SCRIPT_DIR/logs}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/auto_feeds.log}"
ERROR_LOG="${ERROR_LOG:-$LOG_DIR/auto_feeds_error.log}"
MAX_LOG_SIZE="${MAX_LOG_SIZE:-10485760}"  # 10MB por defecto
DOCKER_STARTUP_TIMEOUT="${DOCKER_STARTUP_TIMEOUT:-60}"
GIT_COMMIT_MESSAGE="${GIT_COMMIT_MESSAGE:-update feeds}"
GIT_AUTO_PUSH="${GIT_AUTO_PUSH:-true}"
FORCE_DOWNLOAD="${FORCE_DOWNLOAD:-false}"
ENABLE_NOTIFICATIONS="${ENABLE_NOTIFICATIONS:-false}"

# ============================================
# FUNCIONES AUXILIARES
# ============================================

# Logging con timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE" "$ERROR_LOG" >&2
}

log_success() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✓ $1" | tee -a "$LOG_FILE"
}

# Rotación de logs
rotate_logs() {
    if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0) -gt $MAX_LOG_SIZE ]; then
        mv "$LOG_FILE" "$LOG_FILE.old"
        log "Log rotado (tamaño excedido)"
    fi
}

# Verificar si Docker está corriendo
check_docker() {
    if docker info > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Iniciar Docker (solo macOS y Linux)
start_docker() {
    log "Intentando iniciar Docker..."

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open -a Docker

        local attempts=0
        local max_attempts=$((DOCKER_STARTUP_TIMEOUT / 2))

        while ! check_docker; do
            attempts=$((attempts + 1))
            if [ $attempts -ge $max_attempts ]; then
                log_error "Timeout esperando a que Docker inicie (${DOCKER_STARTUP_TIMEOUT}s)"
                return 1
            fi
            sleep 2
        done

        log_success "Docker iniciado correctamente"
        return 0

    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo systemctl start docker

        if [ $? -eq 0 ]; then
            log_success "Docker iniciado correctamente"
            return 0
        else
            log_error "No se pudo iniciar Docker"
            return 1
        fi
    else
        log_error "Sistema operativo no soportado para iniciar Docker automáticamente"
        return 1
    fi
}

# Verificar cambios en Git
has_changes() {
    git diff --quiet assets/ 2>/dev/null
    if [ $? -eq 1 ]; then
        return 0  # Hay cambios
    else
        return 1  # No hay cambios
    fi
}

# Verificar si estamos en un repositorio Git
is_git_repo() {
    git rev-parse --is-inside-work-tree > /dev/null 2>&1
}

# Enviar notificación (extensible)
send_notification() {
    local message="$1"
    local status="${2:-info}"  # info, success, error

    if [ "$ENABLE_NOTIFICATIONS" = "true" ]; then
        # macOS notification
        if [[ "$OSTYPE" == "darwin"* ]] && command -v osascript &> /dev/null; then
            osascript -e "display notification \"$message\" with title \"Feeds Automation\" subtitle \"$status\""
        fi

        # Aquí puedes añadir otros métodos de notificación:
        # - Slack webhook
        # - Discord webhook
        # - Email
        # - Telegram bot
    fi
}

# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

main() {
    log "=========================================="
    log "Iniciando proceso automatizado de feeds"
    log "=========================================="

    # Crear directorio de logs si no existe
    mkdir -p "$LOG_DIR"

    # Rotar logs si es necesario
    rotate_logs

    # Verificar que .env existe
    if [ ! -f .env ]; then
        log_error "Archivo .env no encontrado"
        send_notification "Error: Archivo .env no encontrado" "error"
        exit 1
    fi

    # Cargar variables de entorno
    set -a
    source .env
    set +a

    # Verificar Docker
    log "Verificando Docker..."
    if ! check_docker; then
        log "Docker no está corriendo, intentando iniciar..."
        if ! start_docker; then
            log_error "No se pudo iniciar Docker. Abortando."
            send_notification "Error: No se pudo iniciar Docker" "error"
            exit 1
        fi
    else
        log_success "Docker está corriendo"
    fi

    # Paso 1: Iniciar MySQL
    log "Iniciando MySQL..."
    docker compose -f docker/docker-compose.yml up -d mysql >> "$LOG_FILE" 2>&1

    if [ $? -ne 0 ]; then
        log_error "Error al iniciar MySQL"
        send_notification "Error al iniciar MySQL" "error"
        exit 1
    fi

    log "Esperando a que MySQL esté listo..."
    sleep 10
    log_success "MySQL iniciado"

    # Paso 2: Iniciar RSSHub
    log "Iniciando RSSHub..."
    docker compose -f docker/docker-compose.yml up -d rsshub >> "$LOG_FILE" 2>&1

    if [ $? -ne 0 ]; then
        log_error "Error al iniciar RSSHub"
        send_notification "Error al iniciar RSSHub" "error"
        exit 1
    fi

    log "Esperando a que RSSHub esté listo..."
    sleep 10
    log_success "RSSHub iniciado"

    # Paso 3: Construir imagen del feed collector
    log "Construyendo imagen del feed collector..."
    docker compose -f docker/docker-compose.yml build feed_collector >> "$LOG_FILE" 2>&1

    if [ $? -ne 0 ]; then
        log_error "Error al construir imagen del feed collector"
        send_notification "Error al construir imagen" "error"
        exit 1
    fi

    log_success "Imagen construida correctamente"

    # Paso 4: Ejecutar recolector de feeds
    log "Ejecutando recolector de feeds..."

    local force_arg=""
    if [ "$FORCE_DOWNLOAD" = "true" ]; then
        force_arg="--force"
        log "Modo FORCE activado - descargando datos del día nuevamente"
    fi

    FORCE_ARG="$force_arg" docker compose -f docker/docker-compose.yml up feed_collector >> "$LOG_FILE" 2>&1

    local exit_code=$?

    # Limpiar contenedor
    docker compose -f docker/docker-compose.yml rm -f feed_collector >> "$LOG_FILE" 2>&1

    if [ $exit_code -ne 0 ]; then
        log_error "Error al ejecutar el recolector de feeds (exit code: $exit_code)"
        send_notification "Error en recolección de feeds" "error"
        exit 1
    fi

    log_success "Recolector de feeds ejecutado correctamente"

    # Paso 5: Verificar si hay cambios en Git
    if ! is_git_repo; then
        log_error "No estamos en un repositorio Git"
        send_notification "Error: No es un repositorio Git" "error"
        exit 1
    fi

    log "Verificando cambios en Git..."

    if has_changes; then
        log_success "Se detectaron cambios en assets/"

        # Paso 6: Git add
        log "Añadiendo archivos al stage..."
        git add assets/ >> "$LOG_FILE" 2>&1

        if [ $? -ne 0 ]; then
            log_error "Error al hacer git add"
            send_notification "Error en git add" "error"
            exit 1
        fi

        log_success "Archivos añadidos al stage"

        # Paso 7: Git commit
        log "Creando commit..."
        local commit_message="$GIT_COMMIT_MESSAGE - $(date +'%Y-%m-%d %H:%M:%S')"
        git commit -m "$commit_message" >> "$LOG_FILE" 2>&1

        if [ $? -ne 0 ]; then
            log_error "Error al crear commit"
            send_notification "Error en git commit" "error"
            exit 1
        fi

        log_success "Commit creado: $commit_message"

        # Paso 8: Git push (si está habilitado)
        if [ "$GIT_AUTO_PUSH" = "true" ]; then
            log "Haciendo push a GitHub..."
            git push origin main >> "$LOG_FILE" 2>&1

            if [ $? -ne 0 ]; then
                log_error "Error al hacer push a GitHub"
                send_notification "Error en git push" "error"
                exit 1
            fi

            log_success "Push completado exitosamente"
            log_success "Netlify desplegará automáticamente los cambios"
            send_notification "Feeds actualizados y publicados correctamente" "success"
        else
            log "Push automático deshabilitado (GIT_AUTO_PUSH=false)"
            log "Ejecuta 'git push' manualmente para publicar los cambios"
            send_notification "Feeds actualizados (push manual requerido)" "success"
        fi
    else
        log "No se detectaron cambios en assets/ - No hay nada que commitear"
        send_notification "Sin cambios en feeds" "info"
    fi

    log "=========================================="
    log "Proceso completado exitosamente"
    log "=========================================="
}

# ============================================
# MANEJO DE ERRORES
# ============================================

trap 'log_error "Script interrumpido"; send_notification "Script interrumpido" "error"; exit 130' INT TERM

# ============================================
# EJECUCIÓN
# ============================================

main "$@"
exit 0
