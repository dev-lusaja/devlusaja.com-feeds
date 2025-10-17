# Sistema de Control de Ejecuciones

## 📋 Descripción

El sistema ahora controla las ejecuciones diarias para evitar descargas duplicadas y mantiene un registro de todas las ejecuciones en la base de datos.

## 🎯 Nuevas Funcionalidades

### 1. Control de Ejecución Diaria

El proceso verifica automáticamente si ya se ejecutó en el día actual:
- Si ya se ejecutó hoy → **No ejecuta** (evita duplicados)
- Si no se ejecutó hoy → **Ejecuta normalmente**

### 2. Parámetro `--force`

Permite forzar la ejecución incluso si ya se ejecutó hoy:

```bash
# Ejecución normal (verifica si ya se ejecutó hoy)
python src/main.py

# Forzar ejecución (ignora verificación)
python src/main.py --force
```

### 3. Limpieza Automática de JSON

Al finalizar exitosamente, el sistema:
- ✅ Guarda los datos en MySQL
- ✅ Crea un backup automático
- ✅ **Elimina todos los archivos JSON individuales** (excepto `feeds_dataframe.csv` y `feeds_dataframe.json`)

Esto mantiene el directorio limpio y solo conserva los archivos consolidados.

### 4. Tabla de Ejecuciones

Nueva tabla `executions` que registra:

| Campo | Descripción |
|-------|-------------|
| execution_date | Fecha de la ejecución (YYYY-MM-DD) |
| execution_time | Timestamp de cuándo se ejecutó |
| feeds_processed | Total de feeds procesados |
| feeds_inserted | Feeds nuevos insertados en MySQL |
| status | Estado: `completed` o `error` |

## 🔄 Flujo de Ejecución

```
┌─────────────────────┐
│  python main.py     │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ MySQL ON?    │
    └──────┬───────┘
           │ Sí
           ▼
    ┌──────────────────┐
    │ ¿Ya ejecutó hoy? │
    └──────┬───────────┘
           │ No (o --force)
           ▼
    ┌──────────────────┐
    │ Descargar Feeds  │
    └──────┬───────────┘
           ▼
    ┌──────────────────┐
    │ Construir DF     │
    └──────┬───────────┘
           ▼
    ┌──────────────────┐
    │ Guardar en MySQL │
    └──────┬───────────┘
           ▼
    ┌──────────────────┐
    │ Registrar Ejec.  │
    └──────┬───────────┘
           ▼
    ┌──────────────────┐
    │ Crear Backup     │
    └──────┬───────────┘
           ▼
    ┌──────────────────┐
    │ Limpiar JSON     │
    └──────────────────┘
```

## 📊 Consultas Útiles

### Ver historial de ejecuciones

```sql
SELECT
    execution_date,
    execution_time,
    feeds_processed,
    feeds_inserted,
    status
FROM executions
ORDER BY execution_date DESC
LIMIT 10;
```

### Ver ejecución de hoy

```sql
SELECT * FROM executions
WHERE execution_date = CURDATE();
```

### Estadísticas de ejecuciones

```sql
SELECT
    COUNT(*) as total_ejecuciones,
    SUM(feeds_inserted) as total_feeds_insertados,
    AVG(feeds_inserted) as promedio_por_dia,
    MAX(feeds_inserted) as max_en_un_dia
FROM executions
WHERE status = 'completed';
```

## 🛠️ Casos de Uso

### Caso 1: Ejecución Diaria Automática

**Configuración recomendada**: Cron job sin `--force`

```bash
# Crontab para ejecutar todos los días a las 8:00 AM
0 8 * * * cd /path/to/project && python src/main.py >> logs/feeds.log 2>&1
```

**Comportamiento**:
- Primera ejecución del día: ✅ Descarga y guarda
- Segunda ejecución del día: ⚠️ Salta (ya ejecutado)
- Tercer intento: ⚠️ Salta (ya ejecutado)

### Caso 2: Re-ejecución Manual

Si necesitas volver a ejecutar en el mismo día:

```bash
python src/main.py --force
```

**Comportamiento**:
- Ignora la verificación de ejecución previa
- Descarga feeds nuevamente (puede sobrescribir datos del día)
- Actualiza el registro de ejecución

### Caso 3: Primera Ejecución con MySQL Deshabilitado

Si `USE_MYSQL=false`:
- No verifica ejecuciones previas
- Solo genera CSV/JSON
- Permite múltiples ejecuciones sin restricción

## 🗑️ Limpieza de Archivos

### Archivos que SE ELIMINAN
- `GoogleNews_AI_feed_2025-10-17.json`
- `Reddit_ClaudeAI_feed_2025-10-17.json`
- Todos los archivos `*_feed_*.json`

### Archivos que SE MANTIENEN
- `feeds_dataframe.csv` ✅
- `feeds_dataframe.json` ✅
- Carpeta `backups/` con backups de MySQL ✅

## 🔧 Configuración

No requiere configuración adicional. El sistema funciona automáticamente cuando:
- `USE_MYSQL=true` en `.env`
- MySQL está corriendo
- Las tablas se crean automáticamente en la primera ejecución

## ⚠️ Notas Importantes

1. **Sin MySQL**: Si MySQL está deshabilitado, NO se controla la ejecución diaria (puedes ejecutar múltiples veces)

2. **Limpieza de JSON**: Los archivos JSON se eliminan SOLO si:
   - MySQL está habilitado
   - La inserción fue exitosa
   - El backup se creó correctamente

3. **Backup antes de limpiar**: Siempre se crea un backup antes de eliminar los JSON, por seguridad

4. **Parámetro --force**: Útil para desarrollo o cuando necesitas re-procesar datos del mismo día

## 🐛 Troubleshooting

### Problema: "El proceso ya se ejecutó hoy"

**Solución 1**: Usar `--force`
```bash
python src/main.py --force
```

**Solución 2**: Eliminar registro del día
```sql
DELETE FROM executions WHERE execution_date = CURDATE();
```

### Problema: Los JSON no se eliminan

**Causas posibles**:
- MySQL está deshabilitado (`USE_MYSQL=false`)
- Hubo un error en la inserción
- No tienes permisos de escritura en `feeds_data/`

**Solución**: Verifica los logs para ver el error exacto

### Problema: Quiero conservar los JSON

**Solución**: Modifica `main.py` y comenta la línea:
```python
# cleanup_json_files()  # Comentar esta línea
```
