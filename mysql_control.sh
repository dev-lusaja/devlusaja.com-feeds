#!/bin/bash
# ===============================================
# 🗄️ Script de control para MySQL
# ===============================================

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

COMPOSE_FILE="docker/docker-compose.yml"

function show_help() {
    echo -e "${GREEN}🗄️ MySQL Control - Gestión de base de datos${NC}"
    echo ""
    echo "Uso: $0 [comando]"
    echo ""
    echo "Comandos disponibles:"
    echo "  start     - Inicia MySQL en segundo plano"
    echo "  stop      - Detiene MySQL"
    echo "  restart   - Reinicia MySQL"
    echo "  status    - Muestra el estado de MySQL"
    echo "  logs      - Muestra los logs de MySQL"
    echo "  connect   - Conecta al cliente MySQL"
    echo "  backup    - Crea un backup de la base de datos"
    echo "  restore   - Restaura un backup (requiere archivo como argumento)"
    echo "  stats     - Muestra estadísticas de la base de datos"
    echo "  clean     - Limpia todo (⚠️ ELIMINA TODOS LOS DATOS)"
    echo "  help      - Muestra esta ayuda"
    echo ""
}

function start_mysql() {
    echo -e "${GREEN}🚀 Iniciando MySQL...${NC}"
    docker compose -f $COMPOSE_FILE up -d mysql

    echo -e "${YELLOW}⏳ Esperando a que MySQL esté listo...${NC}"
    sleep 5

    # Verificar salud
    if docker compose -f $COMPOSE_FILE ps mysql | grep -q "healthy"; then
        echo -e "${GREEN}✅ MySQL está corriendo y saludable${NC}"
    else
        echo -e "${YELLOW}⚠️ MySQL está iniciando... verifica con: $0 logs${NC}"
    fi
}

function stop_mysql() {
    echo -e "${YELLOW}🛑 Deteniendo MySQL...${NC}"
    docker compose -f $COMPOSE_FILE stop mysql
    echo -e "${GREEN}✅ MySQL detenido${NC}"
}

function restart_mysql() {
    echo -e "${YELLOW}🔄 Reiniciando MySQL...${NC}"
    stop_mysql
    start_mysql
}

function show_status() {
    echo -e "${GREEN}📊 Estado de MySQL:${NC}"
    docker compose -f $COMPOSE_FILE ps mysql
}

function show_logs() {
    echo -e "${GREEN}📋 Logs de MySQL:${NC}"
    docker compose -f $COMPOSE_FILE logs -f mysql
}

function connect_mysql() {
    # Cargar variables de entorno
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs)
    fi

    echo -e "${GREEN}🔌 Conectando a MySQL...${NC}"
    docker exec -it feeds_mysql mysql -u${DB_USER:-feeds_user} -p${DB_PASSWORD:-feeds_password} ${DB_NAME:-feeds_db}
}

function backup_db() {
    # Cargar variables de entorno
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs)
    fi

    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"

    echo -e "${GREEN}💾 Creando backup en ${BACKUP_FILE}...${NC}"
    docker exec feeds_mysql mysqldump -u${DB_USER:-feeds_user} -p${DB_PASSWORD:-feeds_password} ${DB_NAME:-feeds_db} > $BACKUP_FILE

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Backup creado exitosamente: ${BACKUP_FILE}${NC}"
    else
        echo -e "${RED}❌ Error al crear backup${NC}"
    fi
}

function restore_db() {
    if [ -z "$1" ]; then
        echo -e "${RED}❌ Error: Debes proporcionar el archivo de backup${NC}"
        echo "Uso: $0 restore <archivo.sql>"
        exit 1
    fi

    if [ ! -f "$1" ]; then
        echo -e "${RED}❌ Error: El archivo $1 no existe${NC}"
        exit 1
    fi

    # Cargar variables de entorno
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs)
    fi

    echo -e "${YELLOW}⚠️  Restaurando desde ${1}...${NC}"
    docker exec -i feeds_mysql mysql -u${DB_USER:-feeds_user} -p${DB_PASSWORD:-feeds_password} ${DB_NAME:-feeds_db} < $1

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Backup restaurado exitosamente${NC}"
    else
        echo -e "${RED}❌ Error al restaurar backup${NC}"
    fi
}

function show_stats() {
    # Cargar variables de entorno
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs)
    fi

    echo -e "${GREEN}📊 Estadísticas de la base de datos:${NC}"

    docker exec feeds_mysql mysql -u${DB_USER:-feeds_user} -p${DB_PASSWORD:-feeds_password} ${DB_NAME:-feeds_db} -e "
        SELECT
            'Total de feeds' as Metrica,
            COUNT(*) as Valor
        FROM feeds
        UNION ALL
        SELECT
            'Feeds por categoría',
            COUNT(DISTINCT sourceCategory)
        FROM feeds
        UNION ALL
        SELECT
            'Feeds hoy',
            COUNT(*)
        FROM feeds
        WHERE DATE(created_at) = CURDATE();
    "

    echo ""
    echo -e "${GREEN}📈 Top 5 categorías:${NC}"
    docker exec feeds_mysql mysql -u${DB_USER:-feeds_user} -p${DB_PASSWORD:-feeds_password} ${DB_NAME:-feeds_db} -e "
        SELECT
            sourceCategory as Categoria,
            COUNT(*) as Total
        FROM feeds
        GROUP BY sourceCategory
        ORDER BY Total DESC
        LIMIT 5;
    "
}

function clean_all() {
    echo -e "${RED}⚠️  ADVERTENCIA: Esto eliminará TODOS los datos de MySQL${NC}"
    read -p "¿Estás seguro? Escribe 'SI' para confirmar: " confirm

    if [ "$confirm" != "SI" ]; then
        echo -e "${YELLOW}Operación cancelada${NC}"
        exit 0
    fi

    echo -e "${RED}🗑️  Eliminando todo...${NC}"

    # Detener y eliminar contenedores
    docker compose -f $COMPOSE_FILE down

    # Eliminar volumen
    docker volume rm docker_mysql_data 2>/dev/null

    echo -e "${GREEN}✅ Todo limpiado. Usa '$0 start' para empezar de nuevo${NC}"
}

# Main
case "$1" in
    start)
        start_mysql
        ;;
    stop)
        stop_mysql
        ;;
    restart)
        restart_mysql
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    connect)
        connect_mysql
        ;;
    backup)
        backup_db
        ;;
    restore)
        restore_db "$2"
        ;;
    stats)
        show_stats
        ;;
    clean)
        clean_all
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        show_help
        exit 1
        ;;
esac
