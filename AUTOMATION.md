# 🤖 Automatización de Feeds

Esta documentación explica cómo usar el sistema de automatización para descargar, procesar y publicar feeds de noticias automáticamente cada X horas.

## 📋 Tabla de Contenidos

- [Descripción General](#-descripción-general)
- [Requisitos](#-requisitos)
- [Instalación Rápida](#-instalación-rápida)
- [Configuración](#-configuración)
- [Uso](#-uso)
- [Logs y Monitoreo](#-logs-y-monitoreo)
- [Solución de Problemas](#-solución-de-problemas)
- [Preguntas Frecuentes](#-preguntas-frecuentes)

---

## 🎯 Descripción General

El sistema de automatización ejecuta automáticamente el siguiente flujo:

```
┌─────────────────┐
│  Cron Job       │
│  (cada X horas) │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  auto_feeds.sh              │
│  1. Verifica Docker         │
│  2. Inicia MySQL            │
│  3. Inicia RSSHub           │
│  4. Ejecuta feed_collector  │
│  5. Descarga feeds RSS      │
│  6. Guarda en MySQL         │
│  7. Genera archivos JSON    │
│  8. Git add + commit        │
│  9. Git push (opcional)     │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  GitHub Repository          │
│  (trigger Netlify deploy)   │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Netlify CDN                │
│  (feeds disponibles)        │
└─────────────────────────────┘
```

**Ventajas:**
- ✅ Totalmente automatizado
- ✅ No requiere intervención manual
- ✅ Logs detallados de cada ejecución
- ✅ Notificaciones del sistema (macOS)
- ✅ Manejo robusto de errores
- ✅ Rotación automática de logs

---

## 📦 Requisitos

### Software Necesario

- **Docker Desktop** (para macOS/Windows) o **Docker Engine** (para Linux)
- **Git** configurado con credenciales
- **Cron** (incluido por defecto en macOS y Linux)
- **Bash** 4.0 o superior

### Permisos Necesarios

- Permisos de ejecución en el directorio del proyecto
- Acceso SSH o HTTPS a GitHub (para push automático)
- Docker debe poder iniciarse sin `sudo` (Linux)

### Verificación de Requisitos

```bash
# Verificar Docker
docker --version

# Verificar Git
git --version

# Verificar configuración de Git
git config user.name
git config user.email

# Verificar Bash
bash --version
```

---

## 🚀 Instalación Rápida

### Paso 1: Hacer Scripts Ejecutables

```bash
chmod +x auto_feeds.sh
chmod +x setup_automation.sh
```

### Paso 2: Ejecutar el Asistente de Configuración

```bash
./setup_automation.sh
```

El asistente te guiará a través de:
1. ✅ Verificación de permisos
2. ✅ Creación del directorio de logs
3. ✅ Verificación de configuración de Git
4. ✅ Prueba de ejecución manual (opcional)
5. ✅ Configuración del cron job

### Paso 3: ¡Listo!

El sistema está configurado y se ejecutará automáticamente según la frecuencia que elegiste.

---

## ⚙️ Configuración

### Archivo de Configuración: `.auto_feeds.config`

Todas las opciones de configuración están en este archivo:

```bash
# Logs
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/auto_feeds.log"
ERROR_LOG="$LOG_DIR/auto_feeds_error.log"
MAX_LOG_SIZE=10485760  # 10MB

# Docker
DOCKER_STARTUP_TIMEOUT=60

# Git
GIT_COMMIT_MESSAGE="update feeds"
GIT_AUTO_PUSH=true

# Descarga
FORCE_DOWNLOAD=false

# Notificaciones
ENABLE_NOTIFICATIONS=true
```

### Opciones Importantes

#### `GIT_AUTO_PUSH` (true/false)
- **`true`**: Hace push automático a GitHub después de cada commit
- **`false`**: Crea el commit pero NO hace push (debes hacerlo manualmente)

**Recomendado:** `true` para automatización completa

#### `FORCE_DOWNLOAD` (true/false)
- **`true`**: Descarga feeds incluso si ya se ejecutó hoy
- **`false`**: Salta la descarga si ya se ejecutó hoy (ahorra recursos)

**Recomendado:** `false` para uso normal

#### `ENABLE_NOTIFICATIONS` (true/false)
- **`true`**: Muestra notificaciones del sistema (solo macOS por ahora)
- **`false`**: No muestra notificaciones

**Recomendado:** `true` si usas macOS

#### `MAX_LOG_SIZE` (bytes)
- Tamaño máximo del log antes de rotarlo
- Por defecto: `10485760` (10MB)
- Cuando se supera, el log se renombra a `.old` y se crea uno nuevo

---

## 🎮 Uso

### Ejecución Manual

```bash
./auto_feeds.sh
```

Útil para:
- Probar que todo funciona correctamente
- Forzar una actualización inmediata
- Debugging

### Ver Logs en Tiempo Real

```bash
# Log principal
tail -f logs/auto_feeds.log

# Log de errores
tail -f logs/auto_feeds_error.log

# Log de cron
tail -f logs/cron.log
```

### Modificar el Cron Job

#### Ver cron jobs actuales
```bash
crontab -l
```

#### Editar cron jobs
```bash
crontab -e
```

#### Eliminar el cron job de feeds
```bash
crontab -l | grep -v 'auto_feeds.sh' | crontab -
```

### Expresiones Cron Comunes

```bash
# Cada hora
0 * * * *

# Cada 2 horas
0 */2 * * *

# Cada 3 horas
0 */3 * * *

# Cada 6 horas
0 */6 * * *

# Cada 12 horas
0 */12 * * *

# Una vez al día a las 8:00 AM
0 8 * * *

# Una vez al día a las 8:00 PM
0 20 * * *

# Dos veces al día (8 AM y 8 PM)
0 8,20 * * *

# De lunes a viernes a las 9 AM
0 9 * * 1-5
```

---

## 📊 Logs y Monitoreo

### Tipos de Logs

#### 1. **auto_feeds.log** - Log Principal
Contiene toda la información de las ejecuciones:
- Timestamp de cada paso
- Estado de Docker
- Descarga de feeds
- Operaciones de Git
- Éxitos y errores

**Ejemplo:**
```
[2025-11-04 08:00:01] ==========================================
[2025-11-04 08:00:01] Iniciando proceso automatizado de feeds
[2025-11-04 08:00:01] ==========================================
[2025-11-04 08:00:01] Verificando Docker...
[2025-11-04 08:00:02] ✓ Docker está corriendo
[2025-11-04 08:00:02] Iniciando MySQL...
[2025-11-04 08:00:15] ✓ MySQL iniciado
[2025-11-04 08:00:15] Iniciando RSSHub...
[2025-11-04 08:00:27] ✓ RSSHub iniciado
[2025-11-04 08:00:27] Construyendo imagen del feed collector...
[2025-11-04 08:00:45] ✓ Imagen construida correctamente
[2025-11-04 08:00:45] Ejecutando recolector de feeds...
[2025-11-04 08:05:32] ✓ Recolector de feeds ejecutado correctamente
[2025-11-04 08:05:32] Verificando cambios en Git...
[2025-11-04 08:05:33] ✓ Se detectaron cambios en assets/
[2025-11-04 08:05:33] Añadiendo archivos al stage...
[2025-11-04 08:05:34] ✓ Archivos añadidos al stage
[2025-11-04 08:05:34] Creando commit...
[2025-11-04 08:05:35] ✓ Commit creado: update feeds - 2025-11-04 08:05:35
[2025-11-04 08:05:35] Haciendo push a GitHub...
[2025-11-04 08:05:42] ✓ Push completado exitosamente
[2025-11-04 08:05:42] ✓ Netlify desplegará automáticamente los cambios
[2025-11-04 08:05:42] ==========================================
[2025-11-04 08:05:42] Proceso completado exitosamente
[2025-11-04 08:05:42] ==========================================
```

#### 2. **auto_feeds_error.log** - Log de Errores
Solo contiene errores críticos que requieren atención.

#### 3. **cron.log** - Log de Cron
Contiene la salida estándar y errores cuando cron ejecuta el script.

### Rotación de Logs

Los logs se rotan automáticamente cuando superan `MAX_LOG_SIZE`:
- El log actual se renombra a `.old`
- Se crea un nuevo log vacío
- Esto evita que los logs crezcan indefinidamente

### Monitoreo de Ejecuciones

#### Ver últimas 50 líneas del log
```bash
tail -n 50 logs/auto_feeds.log
```

#### Buscar errores en los logs
```bash
grep "ERROR" logs/auto_feeds.log
```

#### Ver solo ejecuciones exitosas
```bash
grep "Proceso completado exitosamente" logs/auto_feeds.log
```

#### Ver estadísticas de commits
```bash
git log --oneline --grep="update feeds" | head -n 20
```

---

## 🔧 Solución de Problemas

### Problema: Docker no inicia automáticamente

**Síntoma:**
```
ERROR: Docker no está corriendo
ERROR: No se pudo iniciar Docker
```

**Solución:**
1. Verifica que Docker Desktop esté instalado (macOS/Windows)
2. Intenta iniciar Docker manualmente
3. Aumenta `DOCKER_STARTUP_TIMEOUT` en `.auto_feeds.config`

```bash
# En .auto_feeds.config
DOCKER_STARTUP_TIMEOUT=120  # 2 minutos
```

---

### Problema: Error al hacer push a GitHub

**Síntoma:**
```
ERROR: Error al hacer push a GitHub
```

**Causas comunes:**
1. No estás autenticado en Git
2. No tienes permisos de escritura en el repositorio
3. La rama `main` está protegida

**Solución:**

#### Verificar autenticación SSH
```bash
ssh -T git@github.com
```

Debería mostrar:
```
Hi username! You've successfully authenticated...
```

#### Si usas HTTPS, configura un token
```bash
git remote set-url origin https://TOKEN@github.com/usuario/repo.git
```

#### Alternativa: Deshabilitar push automático
```bash
# En .auto_feeds.config
GIT_AUTO_PUSH=false
```

Luego puedes hacer push manualmente:
```bash
git push origin main
```

---

### Problema: Cron job no se ejecuta

**Síntoma:**
El script no se ejecuta automáticamente según el horario configurado.

**Verificación:**
```bash
# Ver cron jobs
crontab -l

# Ver logs de cron
tail -f logs/cron.log

# Ver logs del sistema (macOS)
log show --predicate 'process == "cron"' --last 1h
```

**Solución:**
1. Verifica que el cron job esté configurado:
```bash
crontab -l | grep auto_feeds.sh
```

2. Asegúrate de que el path sea absoluto en el cron:
```bash
0 */2 * * * cd /Users/tu_usuario/ruta/completa && ./auto_feeds.sh >> logs/cron.log 2>&1
```

3. Verifica permisos de ejecución:
```bash
ls -l auto_feeds.sh
# Debe mostrar: -rwxr-xr-x
```

4. En macOS, asegúrate de que Terminal/cron tenga permisos de "Full Disk Access":
   - System Preferences > Security & Privacy > Privacy > Full Disk Access
   - Añade `/usr/sbin/cron`

---

### Problema: MySQL no se conecta

**Síntoma:**
```
ERROR: Error al iniciar MySQL
```

**Solución:**
1. Verifica que el puerto 3306 no esté ocupado:
```bash
lsof -i :3306
```

2. Verifica el estado de MySQL:
```bash
docker ps | grep feeds_mysql
```

3. Ver logs de MySQL:
```bash
docker logs feeds_mysql
```

4. Reiniciar MySQL:
```bash
docker compose -f docker/docker-compose.yml restart mysql
```

---

### Problema: No se detectan cambios en Git

**Síntoma:**
```
No se detectaron cambios en assets/ - No hay nada que commitear
```

**Causas:**
- No se generaron nuevos feeds
- Los feeds son idénticos a la ejecución anterior
- El proceso ya se ejecutó hoy (sin `--force`)

**Solución:**
Si quieres forzar la descarga cada vez:
```bash
# En .auto_feeds.config
FORCE_DOWNLOAD=true
```

---

## ❓ Preguntas Frecuentes

### ¿Puedo ejecutar el script manualmente?

Sí:
```bash
./auto_feeds.sh
```

### ¿Cómo cambio la frecuencia de ejecución?

Edita el cron job:
```bash
crontab -e
```

O ejecuta de nuevo el asistente:
```bash
./setup_automation.sh
```

### ¿Puedo deshabilitar el push automático?

Sí, en `.auto_feeds.config`:
```bash
GIT_AUTO_PUSH=false
```

### ¿Puedo ejecutar el script sin hacer commit?

No directamente, pero puedes modificar `auto_feeds.sh` comentando las líneas de Git (líneas 189-214).

### ¿Los logs crecen indefinidamente?

No, se rotan automáticamente cuando superan `MAX_LOG_SIZE` (10MB por defecto).

### ¿Puedo recibir notificaciones por Slack/Discord/Email?

Sí, edita la función `send_notification()` en `auto_feeds.sh` y añade tu webhook:

```bash
send_notification() {
    local message="$1"
    local status="${2:-info}"

    # Slack
    curl -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"$message\"}" \
      YOUR_SLACK_WEBHOOK_URL

    # Discord
    curl -H "Content-Type: application/json" \
      -d "{\"content\": \"$message\"}" \
      YOUR_DISCORD_WEBHOOK_URL
}
```

### ¿Funciona en Windows?

No directamente. Necesitas:
- WSL2 (Windows Subsystem for Linux)
- Docker Desktop con integración WSL2
- Ejecutar todo desde WSL2

O usar la **Opción 3** (GitHub Actions) que es multiplataforma.

### ¿Qué pasa si mi máquina se apaga?

El cron job no se ejecutará. Opciones:
1. Mantén tu máquina siempre encendida
2. Usa un servidor dedicado (VPS)
3. Migra a **Opción 3** (GitHub Actions)

### ¿Puedo ver los feeds antes de que se publiquen?

Sí, los archivos JSON se generan en `./assets/` antes del commit. Puedes revisarlos antes del push.

### ¿Cómo detengo la automatización?

Elimina el cron job:
```bash
crontab -l | grep -v 'auto_feeds.sh' | crontab -
```

### ¿Puedo ejecutar en un horario específico?

Sí, usa una expresión cron personalizada:
```bash
# Todos los días a las 3:00 AM
0 3 * * *

# Lunes a viernes a las 9 AM
0 9 * * 1-5
```

---

## 📚 Recursos Adicionales

### Archivos Importantes

- `auto_feeds.sh` - Script principal de automatización
- `.auto_feeds.config` - Archivo de configuración
- `setup_automation.sh` - Asistente de configuración
- `logs/` - Directorio de logs
- `run.sh` - Script manual original (aún funciona)

### Comandos Útiles

```bash
# Ver estado de Docker
docker ps

# Ver logs de MySQL
docker logs feeds_mysql

# Ver logs de RSSHub
docker logs feeds_rsshub

# Ver tamaño de la base de datos
docker exec feeds_mysql mysql -u feeds_user -pfeeds_password -e "SELECT table_schema AS 'Database', ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)' FROM information_schema.tables WHERE table_schema = 'feeds_db' GROUP BY table_schema;"

# Ver cantidad de feeds en la BD
docker exec feeds_mysql mysql -u feeds_user -pfeeds_password -e "SELECT COUNT(*) FROM feeds_db.feeds;"

# Ver últimos 10 commits
git log --oneline -n 10

# Ver archivos generados
ls -lh assets/
```

---

## 🆘 Soporte

Si encuentras algún problema:

1. **Revisa los logs:**
   ```bash
   tail -f logs/auto_feeds.log
   tail -f logs/auto_feeds_error.log
   ```

2. **Ejecuta manualmente para debugging:**
   ```bash
   ./auto_feeds.sh
   ```

3. **Verifica la configuración:**
   ```bash
   cat .auto_feeds.config
   ```

4. **Consulta esta documentación**

5. **Revisa el código fuente** - Está bien documentado

---

## 📝 Notas Finales

- ✅ El sistema está diseñado para ser robusto y manejar errores
- ✅ Los logs te ayudarán a diagnosticar cualquier problema
- ✅ Puedes personalizar todo en `.auto_feeds.config`
- ✅ El script `run.sh` original sigue funcionando para uso manual
- ✅ La automatización es completamente transparente y auditable

**¡Disfruta de tus feeds automáticos! 🚀**
