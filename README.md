# 📰 Devlusaja Feeds

Sistema automatizado de recolección, procesamiento y publicación de feeds de noticias RSS.

## 🚀 Inicio Rápido

### Uso Manual

```bash
# Menú interactivo
./run.sh
```

### Automatización

```bash
# Configurar automatización (cron job)
./setup_automation.sh
```

El sistema ejecutará automáticamente:
- ✅ Descarga de feeds RSS
- ✅ Almacenamiento en MySQL
- ✅ Generación de archivos JSON
- ✅ Commit y push a GitHub
- ✅ Despliegue en Netlify

## 📚 Documentación

- **[AUTOMATION.md](AUTOMATION.md)** - Guía completa de automatización
- **[netlify.toml](netlify.toml)** - Configuración de despliegue
- **[feeds_config.yaml](feeds_config.yaml)** - Configuración de fuentes RSS

## 📂 Estructura del Proyecto

```
.
├── auto_feeds.sh              # Script de automatización
├── setup_automation.sh        # Asistente de configuración
├── run.sh                     # Menú interactivo manual
├── feeds_config.yaml          # Configuración de feeds
├── .auto_feeds.config         # Config de automatización
│
├── docker/
│   ├── docker-compose.yml     # Orquestación de servicios
│   ├── Dockerfile             # Imagen del collector
│   └── init.sql              # Inicialización de BD
│
├── src/                       # Código Python
│   ├── feed_fetcher.py        # Script principal
│   ├── regenerate_assets.py   # Regenerar JSON
│   ├── feed_postprocess_images.py
│   ├── config/                # Configuración
│   ├── database/              # Operaciones MySQL
│   ├── feeds/                 # Lógica de feeds
│   └── utils/                 # Utilidades
│
├── assets/                    # JSON generados (publicados)
│   ├── metadata.json
│   ├── notice-all-chunk-*.json
│   ├── pappers-all-chunk-*.json
│   ├── youtube-all-chunk-*.json
│   └── shorts-all-chunk-*.json
│
├── logs/                      # Logs de automatización
│   ├── auto_feeds.log
│   ├── auto_feeds_error.log
│   └── cron.log
│
└── backups/                   # Backups de MySQL
```

## 🔧 Requisitos

- Docker Desktop (macOS/Windows) o Docker Engine (Linux)
- Git configurado
- Bash 4.0+
- Python 3.11+ (en contenedor)

## ⚙️ Configuración

### Variables de Entorno (.env)

```bash
# MySQL
USE_MYSQL=true
DB_HOST=localhost
DB_PORT=3306
DB_NAME=feeds_db
DB_USER=feeds_user
DB_PASSWORD=feeds_password

# RSSHub
RSSHUB_HOST=localhost
RSSHUB_PORT=1200
RSSHUB_BASE_URL=http://localhost:1200

# TikTok (opcional)
TIKTOK_SESSION_ID=
TIKTOK_COOKIE=
```

### Configuración de Automatización (.auto_feeds.config)

```bash
# Git
GIT_AUTO_PUSH=true               # Push automático a GitHub
GIT_COMMIT_MESSAGE="update feeds"

# Descarga
FORCE_DOWNLOAD=false             # Forzar descarga diaria

# Notificaciones
ENABLE_NOTIFICATIONS=true        # Notificaciones del sistema
```

## 📊 Comandos Útiles

### Manual

```bash
# Menú interactivo
./run.sh

# Descargar feeds
./run.sh  # Opción 1

# Regenerar assets desde BD
./run.sh  # Opción 5

# Post-procesar imágenes
./run.sh  # Opción 3
```

### Automatización

```bash
# Configurar automatización
./setup_automation.sh

# Ejecutar manualmente
./auto_feeds.sh

# Ver logs en tiempo real
tail -f logs/auto_feeds.log

# Ver cron jobs
crontab -l
```

### Docker

```bash
# Iniciar servicios
docker compose -f docker/docker-compose.yml up -d

# Ver logs
docker compose -f docker/docker-compose.yml logs -f

# Detener servicios
docker compose -f docker/docker-compose.yml down
```

### Base de Datos

```bash
# Ver cantidad de feeds
docker exec feeds_mysql mysql -u feeds_user -pfeeds_password \
  -e "SELECT COUNT(*) FROM feeds_db.feeds;"

# Ver feeds por tipo
docker exec feeds_mysql mysql -u feeds_user -pfeeds_password \
  -e "SELECT sourceType, COUNT(*) FROM feeds_db.feeds GROUP BY sourceType;"
```

## 🎯 Flujo de Trabajo

### Automático (Cron)

```
Cron Job → auto_feeds.sh → Docker → MySQL → JSON → Git → GitHub → Netlify
```

### Manual

```
run.sh → Docker → MySQL → JSON
        ↓
    Git commit/push manual → GitHub → Netlify
```

## 📡 Endpoints

Una vez desplegado en Netlify:

```
https://devlusaja-feeds.netlify.app/metadata.json
https://devlusaja-feeds.netlify.app/notice-all-chunk-0.json
https://devlusaja-feeds.netlify.app/pappers-arXiv_AI-chunk-0.json
...
```

## 🤝 Fuentes de Feeds

El proyecto recolecta feeds de:

- 📰 **Noticias**: Xataka, Wired ES, El País, TechCrunch, The Verge, etc.
- 📚 **Papers**: arXiv (AI, ML, Computer Science)
- 🎥 **YouTube**: Canales de tecnología y programación
- 🎬 **TikTok**: Contenido educativo
- 💬 **Foros**: Reddit (r/MachineLearning, r/LocalLLaMA)
- 🎓 **Educación**: Fast.ai, ML Mastery, etc.

Ver [feeds_config.yaml](feeds_config.yaml) para la lista completa.

## 📝 Licencia

[Especifica tu licencia aquí]

## 👤 Autor

DevLusaja
