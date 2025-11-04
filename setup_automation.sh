#!/bin/bash
# ===============================================
# 🔧 Script de Configuración de Automatización
# ===============================================
# Este script te ayuda a configurar el cron job
# para ejecutar automáticamente la descarga de feeds
# ===============================================

set -euo pipefail

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # Sin color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Banner
print_banner() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════╗"
    echo "║  🔧 Setup de Automatización de Feeds          ║"
    echo "╚════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Función para hacer el script ejecutable
make_executable() {
    echo -e "${YELLOW}Haciendo auto_feeds.sh ejecutable...${NC}"
    chmod +x auto_feeds.sh
    echo -e "${GREEN}✓ auto_feeds.sh es ahora ejecutable${NC}\n"
}

# Crear directorio de logs
create_log_dir() {
    echo -e "${YELLOW}Creando directorio de logs...${NC}"
    mkdir -p logs
    echo -e "${GREEN}✓ Directorio logs/ creado${NC}\n"
}

# Verificar configuración de Git
check_git_config() {
    echo -e "${YELLOW}Verificando configuración de Git...${NC}"

    if ! git config user.name > /dev/null 2>&1; then
        echo -e "${RED}✗ Git user.name no configurado${NC}"
        echo -e "${YELLOW}Configura tu nombre con: git config --global user.name \"Tu Nombre\"${NC}\n"
        return 1
    fi

    if ! git config user.email > /dev/null 2>&1; then
        echo -e "${RED}✗ Git user.email no configurado${NC}"
        echo -e "${YELLOW}Configura tu email con: git config --global user.email \"tu@email.com\"${NC}\n"
        return 1
    fi

    echo -e "${GREEN}✓ Git configurado correctamente${NC}"
    echo -e "  Usuario: $(git config user.name)"
    echo -e "  Email: $(git config user.email)\n"
    return 0
}

# Probar ejecución manual
test_execution() {
    echo -e "${BLUE}¿Deseas probar la ejecución manual del script? (s/n)${NC}"
    read -r response

    if [[ "$response" =~ ^[Ss]$ ]]; then
        echo -e "${YELLOW}Ejecutando auto_feeds.sh...${NC}\n"
        ./auto_feeds.sh
        echo -e "\n${GREEN}✓ Ejecución de prueba completada${NC}\n"
    else
        echo -e "${YELLOW}Omitiendo prueba de ejecución${NC}\n"
    fi
}

# Configurar cron job
setup_cron() {
    echo -e "${CYAN}╔════════════════════════════════════════════════╗"
    echo "║  📅 Configuración de Cron Job                 ║"
    echo "╚════════════════════════════════════════════════╝${NC}\n"

    echo -e "${BLUE}¿Con qué frecuencia deseas ejecutar el script?${NC}\n"
    echo -e "  ${GREEN}1)${NC} Cada 1 hora"
    echo -e "  ${GREEN}2)${NC} Cada 2 horas"
    echo -e "  ${GREEN}3)${NC} Cada 3 horas"
    echo -e "  ${GREEN}4)${NC} Cada 6 horas"
    echo -e "  ${GREEN}5)${NC} Cada 12 horas"
    echo -e "  ${GREEN}6)${NC} Una vez al día (a las 8:00 AM)"
    echo -e "  ${GREEN}7)${NC} Personalizado"
    echo -e "  ${GREEN}0)${NC} Omitir configuración de cron"
    echo ""

    read -p "Selecciona una opción: " cron_option
    echo ""

    local cron_schedule=""
    local description=""

    case $cron_option in
        1)
            cron_schedule="0 * * * *"
            description="cada hora"
            ;;
        2)
            cron_schedule="0 */2 * * *"
            description="cada 2 horas"
            ;;
        3)
            cron_schedule="0 */3 * * *"
            description="cada 3 horas"
            ;;
        4)
            cron_schedule="0 */6 * * *"
            description="cada 6 horas"
            ;;
        5)
            cron_schedule="0 */12 * * *"
            description="cada 12 horas"
            ;;
        6)
            cron_schedule="0 8 * * *"
            description="todos los días a las 8:00 AM"
            ;;
        7)
            echo -e "${YELLOW}Ingresa la expresión cron personalizada:${NC}"
            echo -e "${CYAN}Formato: minuto hora día mes día_semana${NC}"
            echo -e "${CYAN}Ejemplo: 0 */4 * * * (cada 4 horas)${NC}"
            read -p "Expresión cron: " cron_schedule
            description="personalizado"
            ;;
        0)
            echo -e "${YELLOW}Omitiendo configuración de cron${NC}\n"
            return 0
            ;;
        *)
            echo -e "${RED}Opción inválida${NC}\n"
            return 1
            ;;
    esac

    # Construir línea de cron
    local cron_line="$cron_schedule cd $SCRIPT_DIR && ./auto_feeds.sh >> $SCRIPT_DIR/logs/cron.log 2>&1"

    echo -e "${YELLOW}Se configurará el siguiente cron job:${NC}"
    echo -e "${CYAN}$cron_line${NC}\n"
    echo -e "${BLUE}Descripción: Ejecutar $description${NC}\n"

    echo -e "${BLUE}¿Deseas continuar? (s/n)${NC}"
    read -r response

    if [[ ! "$response" =~ ^[Ss]$ ]]; then
        echo -e "${YELLOW}Configuración de cron cancelada${NC}\n"
        return 0
    fi

    # Verificar si ya existe un cron job para este script
    local existing_cron=$(crontab -l 2>/dev/null | grep -F "auto_feeds.sh" || true)

    if [ -n "$existing_cron" ]; then
        echo -e "${YELLOW}Ya existe un cron job para auto_feeds.sh:${NC}"
        echo -e "${CYAN}$existing_cron${NC}\n"
        echo -e "${BLUE}¿Deseas reemplazarlo? (s/n)${NC}"
        read -r response

        if [[ "$response" =~ ^[Ss]$ ]]; then
            # Eliminar el cron job existente
            (crontab -l 2>/dev/null | grep -v -F "auto_feeds.sh") | crontab -
            echo -e "${GREEN}✓ Cron job anterior eliminado${NC}\n"
        else
            echo -e "${YELLOW}Conservando cron job existente${NC}\n"
            return 0
        fi
    fi

    # Añadir nuevo cron job
    (crontab -l 2>/dev/null; echo "$cron_line") | crontab -

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Cron job configurado exitosamente${NC}\n"
        echo -e "${GREEN}El script se ejecutará $description${NC}\n"
    else
        echo -e "${RED}✗ Error al configurar cron job${NC}\n"
        return 1
    fi
}

# Mostrar cron jobs actuales
show_cron_jobs() {
    echo -e "${CYAN}╔════════════════════════════════════════════════╗"
    echo "║  📋 Cron Jobs Actuales                        ║"
    echo "╚════════════════════════════════════════════════╝${NC}\n"

    local cron_jobs=$(crontab -l 2>/dev/null || true)

    if [ -z "$cron_jobs" ]; then
        echo -e "${YELLOW}No hay cron jobs configurados${NC}\n"
    else
        echo -e "${GREEN}Cron jobs configurados:${NC}\n"
        echo "$cron_jobs" | nl
        echo ""
    fi
}

# Instrucciones finales
show_final_instructions() {
    echo -e "${CYAN}╔════════════════════════════════════════════════╗"
    echo "║  ✅ Configuración Completada                  ║"
    echo "╚════════════════════════════════════════════════╝${NC}\n"

    echo -e "${GREEN}¡Automatización configurada exitosamente!${NC}\n"

    echo -e "${BLUE}Comandos útiles:${NC}\n"
    echo -e "  ${YELLOW}Ejecutar manualmente:${NC}"
    echo -e "    ./auto_feeds.sh\n"

    echo -e "  ${YELLOW}Ver logs:${NC}"
    echo -e "    tail -f logs/auto_feeds.log\n"

    echo -e "  ${YELLOW}Ver errores:${NC}"
    echo -e "    tail -f logs/auto_feeds_error.log\n"

    echo -e "  ${YELLOW}Ver cron jobs:${NC}"
    echo -e "    crontab -l\n"

    echo -e "  ${YELLOW}Editar cron jobs:${NC}"
    echo -e "    crontab -e\n"

    echo -e "  ${YELLOW}Eliminar cron job:${NC}"
    echo -e "    crontab -l | grep -v 'auto_feeds.sh' | crontab -\n"

    echo -e "${YELLOW}Notas importantes:${NC}"
    echo -e "  • Los logs se guardan en: $SCRIPT_DIR/logs/"
    echo -e "  • Los logs rotan automáticamente cuando superan 10MB"
    echo -e "  • La configuración está en: .auto_feeds.config"
    echo -e "  • Para más información, consulta: AUTOMATION.md\n"
}

# Función principal
main() {
    clear
    print_banner

    echo -e "${BLUE}Este asistente te ayudará a configurar la automatización de feeds${NC}\n"

    # Paso 1: Hacer ejecutable
    make_executable

    # Paso 2: Crear directorio de logs
    create_log_dir

    # Paso 3: Verificar Git
    check_git_config
    git_ok=$?

    # Paso 4: Probar ejecución (opcional)
    if [ $git_ok -eq 0 ]; then
        test_execution
    else
        echo -e "${YELLOW}Configura Git antes de probar la ejecución${NC}\n"
    fi

    # Paso 5: Configurar cron
    setup_cron

    # Paso 6: Mostrar cron jobs actuales
    show_cron_jobs

    # Paso 7: Instrucciones finales
    show_final_instructions
}

# Ejecutar
main "$@"
