import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from pathlib import Path
from mysql.connector import Error
from database.connection import DatabaseConnection
from config.loader import load_exclusions_config
from utils.logger import log

def create_feeds_table(db: DatabaseConnection) -> bool:
    """
    Crea la tabla de feeds si no existe.

    Args:
        db: Objeto de conexión a la base de datos

    Returns:
        True si se creó exitosamente, False en caso contrario
    """
    cursor = db.get_cursor()
    if not cursor:
        return False

    try:
        create_table_query = """
        CREATE TABLE IF NOT EXISTS feeds (
            id VARCHAR(36) PRIMARY KEY,
            title TEXT,
            link TEXT,
            pubDate VARCHAR(255),
            pubDate_parsed DATETIME GENERATED ALWAYS AS (
                STR_TO_DATE(SUBSTRING(pubDate, 1, 19), '%Y-%m-%dT%H:%i:%s')
            ) STORED,
            description TEXT,
            author LONGTEXT,
            sourceTitle VARCHAR(255),
            sourceUrl TEXT,
            sourceCategory VARCHAR(255),
            sourceType VARCHAR(50),
            sourceCountry VARCHAR(100),
            content LONGTEXT,
            image TEXT,
            isShortVideo TINYINT(1) DEFAULT 0,
            raw_data LONGTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_source_category (sourceCategory),
            INDEX idx_source_type (sourceType),
            INDEX idx_source_country (sourceCountry),
            INDEX idx_pub_date (pubDate),
            INDEX idx_pubDate_parsed (pubDate_parsed),
            INDEX idx_sourceType_pubDate (sourceType, pubDate_parsed),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        cursor.execute(create_table_query)
        db.commit()
        log("✅ Tabla 'feeds' verificada/creada exitosamente")

        # Crear tabla de ejecuciones
        create_executions_table_query = """
        CREATE TABLE IF NOT EXISTS executions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            execution_date DATE NOT NULL UNIQUE,
            execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            feeds_processed INT DEFAULT 0,
            feeds_inserted INT DEFAULT 0,
            status VARCHAR(50) DEFAULT 'completed',
            INDEX idx_execution_date (execution_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        cursor.execute(create_executions_table_query)
        db.commit()
        log("✅ Tabla 'executions' verificada/creada exitosamente")

        return True
    except Error as e:
        log(f"❌ Error al crear tablas: {e}")
        db.rollback()
        return False
    finally:
        cursor.close()

def feed_exists(db: DatabaseConnection, feed_id: str) -> bool:
    """
    Verifica si un feed ya existe en la base de datos.

    Args:
        db: Objeto de conexión a la base de datos
        feed_id: ID único del feed

    Returns:
        True si existe, False en caso contrario
    """
    cursor = db.get_cursor()
    if not cursor:
        return False

    try:
        query = "SELECT COUNT(*) as count FROM feeds WHERE id = %s"
        cursor.execute(query, (feed_id,))
        result = cursor.fetchone()
        return result['count'] > 0 if result else False
    except Error as e:
        log(f"❌ Error al verificar existencia de feed {feed_id}: {e}")
        return False
    finally:
        cursor.close()

def insert_feed(db: DatabaseConnection, feed_data: Dict[str, Any]) -> bool:
    """
    Inserta un feed en la base de datos.

    Args:
        db: Objeto de conexión a la base de datos
        feed_data: Diccionario con los datos del feed

    Returns:
        True si se insertó exitosamente, False en caso contrario
    """
    cursor = db.get_cursor()
    if not cursor:
        return False

    try:
        insert_query = """
        INSERT INTO feeds (
            id, title, link, pubDate, description, author,
            sourceTitle, sourceUrl, sourceCategory, sourceType, sourceCountry,
            content, image, isShortVideo, raw_data
        ) VALUES (
            %(id)s, %(title)s, %(link)s, %(pubDate)s, %(description)s, %(author)s,
            %(sourceTitle)s, %(sourceUrl)s, %(sourceCategory)s, %(sourceType)s, %(sourceCountry)s,
            %(content)s, %(image)s, %(isShortVideo)s, %(raw_data)s
        )
        """
        cursor.execute(insert_query, feed_data)
        db.commit()
        return True
    except Error as e:
        log(f"❌ Error al insertar feed {feed_data.get('id', 'unknown')}: {e}")
        db.rollback()
        return False
    finally:
        cursor.close()

def insert_feeds_from_dataframe(db: DatabaseConnection, df: pd.DataFrame) -> Dict[str, int]:
    """
    Inserta múltiples feeds desde un DataFrame.
    Solo inserta los feeds que no existen en la base de datos.

    Args:
        db: Objeto de conexión a la base de datos
        df: DataFrame con los datos de los feeds

    Returns:
        Diccionario con estadísticas: {'inserted': count, 'skipped': count, 'errors': count}
    """
    stats = {'inserted': 0, 'skipped': 0, 'errors': 0}

    if df.empty:
        log("⚠️ DataFrame vacío, no hay feeds para insertar")
        return stats

    log(f"📊 Procesando {len(df)} feeds para inserción en MySQL...")

    for index, row in df.iterrows():
        feed_id = row['id']

        # Verificar si el feed ya existe
        if feed_exists(db, feed_id):
            stats['skipped'] += 1
            continue

        # Preparar datos para inserción
        feed_data = {
            'id': row['id'],
            'title': row['title'] if pd.notna(row['title']) else '',
            'link': row['link'] if pd.notna(row['link']) else '',
            'pubDate': row['pubDate'] if pd.notna(row['pubDate']) else '',
            'description': row['description'] if pd.notna(row['description']) else '',
            'author': row['author'] if pd.notna(row['author']) else '',
            'sourceTitle': row['sourceTitle'] if pd.notna(row['sourceTitle']) else '',
            'sourceUrl': row['sourceUrl'] if pd.notna(row['sourceUrl']) else '',
            'sourceCategory': row['sourceCategory'] if pd.notna(row['sourceCategory']) else '',
            'sourceType': row['sourceType'] if pd.notna(row['sourceType']) else '',
            'sourceCountry': row['sourceCountry'] if pd.notna(row['sourceCountry']) else '',
            'content': row['content'] if pd.notna(row['content']) else '',
            'image': row['image'] if pd.notna(row['image']) else '',
            'isShortVideo': row['isShortVideo'] if pd.notna(row['isShortVideo']) else 0,
            'raw_data': row['raw_data'] if pd.notna(row['raw_data']) else ''
        }

        # Intentar insertar
        if insert_feed(db, feed_data):
            stats['inserted'] += 1
        else:
            stats['errors'] += 1

    log(f"✅ Inserción completada: {stats['inserted']} nuevos, {stats['skipped']} existentes, {stats['errors']} errores")
    return stats

def get_feeds_by_category(db: DatabaseConnection, category: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Obtiene feeds por categoría.

    Args:
        db: Objeto de conexión a la base de datos
        category: Categoría del feed
        limit: Número máximo de resultados

    Returns:
        Lista de diccionarios con los datos de los feeds
    """
    cursor = db.get_cursor()
    if not cursor:
        return []

    try:
        query = """
        SELECT * FROM feeds
        WHERE sourceCategory = %s
        ORDER BY created_at DESC
        LIMIT %s
        """
        cursor.execute(query, (category, limit))
        results = cursor.fetchall()
        return results
    except Error as e:
        log(f"❌ Error al obtener feeds de categoría {category}: {e}")
        return []
    finally:
        cursor.close()

def get_feed_count(db: DatabaseConnection) -> int:
    """
    Obtiene el número total de feeds en la base de datos.

    Args:
        db: Objeto de conexión a la base de datos

    Returns:
        Número total de feeds
    """
    cursor = db.get_cursor()
    if not cursor:
        return 0

    try:
        query = "SELECT COUNT(*) as count FROM feeds"
        cursor.execute(query)
        result = cursor.fetchone()
        return result['count'] if result else 0
    except Error as e:
        log(f"❌ Error al contar feeds: {e}")
        return 0
    finally:
        cursor.close()

def was_executed_today(db: DatabaseConnection) -> bool:
    """
    Verifica si el proceso ya se ejecutó hoy.

    Args:
        db: Objeto de conexión a la base de datos

    Returns:
        True si ya se ejecutó hoy, False en caso contrario
    """
    cursor = db.get_cursor()
    if not cursor:
        return False

    try:
        today = date.today()
        query = "SELECT COUNT(*) as count FROM executions WHERE execution_date = %s"
        cursor.execute(query, (today,))
        result = cursor.fetchone()
        return result['count'] > 0 if result else False
    except Error as e:
        log(f"❌ Error al verificar ejecución del día: {e}")
        return False
    finally:
        cursor.close()

def register_execution(db: DatabaseConnection, feeds_processed: int, feeds_inserted: int, status: str = 'completed') -> bool:
    """
    Registra una ejecución del proceso en la base de datos.

    Args:
        db: Objeto de conexión a la base de datos
        feeds_processed: Número de feeds procesados
        feeds_inserted: Número de feeds insertados
        status: Estado de la ejecución (completed, error, etc.)

    Returns:
        True si se registró exitosamente, False en caso contrario
    """
    cursor = db.get_cursor()
    if not cursor:
        return False

    try:
        today = date.today()

        # Intentar insertar o actualizar si ya existe
        query = """
        INSERT INTO executions (execution_date, feeds_processed, feeds_inserted, status)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            execution_time = CURRENT_TIMESTAMP,
            feeds_processed = %s,
            feeds_inserted = %s,
            status = %s
        """
        cursor.execute(query, (today, feeds_processed, feeds_inserted, status, feeds_processed, feeds_inserted, status))
        db.commit()
        log(f"✅ Ejecución registrada: {feeds_processed} procesados, {feeds_inserted} insertados")
        return True
    except Error as e:
        log(f"❌ Error al registrar ejecución: {e}")
        db.rollback()
        return False
    finally:
        cursor.close()

def get_metadata_from_db(db: DatabaseConnection, feeds_config: List[Dict[str, Any]], config_path: str = None, months_back: Optional[int] = None, max_chunks: Optional[int] = None) -> Dict[str, Any]:
    """
    Genera metadata desde la base de datos con estadísticas de feeds.
    Las exclusiones de categorías se configuran en feeds_config.yaml.

    Args:
        db: Objeto de conexión a la base de datos
        feeds_config: Lista de configuración de feeds del YAML
        config_path: Ruta al archivo de configuración YAML (por defecto 'feeds_config.yaml')
        months_back: Si se especifica, solo cuenta feeds de los últimos N meses (usa pubDate_parsed)
        max_chunks: Número máximo de chunks por categoría (None = sin límite)

    Returns:
        Diccionario con metadata en el formato requerido
    """
    # Si no se proporciona config_path, usar el path por defecto
    if config_path is None:
        config_path = str(Path(__file__).parent.parent.parent / "feeds_config.yaml")

    cursor = db.get_cursor()
    if not cursor:
        return {}

    try:
        # Cargar configuración de exclusiones
        exclusions_config = load_exclusions_config(config_path)
        chunks_all_exclusions = exclusions_config.get('chunks_all', {})

        # Determinar si aplicar filtro de fecha
        date_filter = ""
        if months_back is not None:
            date_filter = f" WHERE pubDate_parsed >= DATE_SUB(NOW(), INTERVAL {months_back} MONTH)"

        # Obtener total de items
        total_query = f"SELECT COUNT(*) as count FROM feeds{date_filter}"
        cursor.execute(total_query)
        total_items = cursor.fetchone()['count']

        # Construir query dinámico para exclusiones basadas en la configuración
        where_conditions = []

        # Agregar filtro de fecha si aplica
        if months_back is not None:
            where_conditions.append(f"pubDate_parsed >= DATE_SUB(NOW(), INTERVAL {months_back} MONTH)")

        # Agregar exclusiones configuradas
        for source_type, excluded_categories in chunks_all_exclusions.items():
            if excluded_categories:
                placeholders = ', '.join([f"'{cat}'" for cat in excluded_categories])
                where_conditions.append(f"NOT (sourceType = '{source_type}' AND sourceCategory IN ({placeholders}))")

        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)

        # Obtener conteo por tipo (aplicando exclusiones configuradas y filtro de fecha)
        type_query = f"""
        SELECT sourceType as type, COUNT(*) as count
        FROM feeds
        {where_clause}
        GROUP BY sourceType
        """
        cursor.execute(type_query)
        type_counts = {row['type']: row['count'] for row in cursor.fetchall()}

        # Obtener conteo por categoría y tipo (con filtro de fecha si aplica)
        category_query = f"""
        SELECT sourceCategory as category, sourceTitle as title, sourceType as type, COUNT(*) as count
        FROM feeds
        {date_filter}
        GROUP BY sourceCategory, sourceTitle, sourceType
        ORDER BY sourceType, count DESC
        """
        cursor.execute(category_query)
        category_data = cursor.fetchall()

        # Crear estructura de sources
        sources = []
        for feed in feeds_config:
            sources.append({
                "title": feed['title'],
                "category": feed['category'],
                "type": feed['sourceType']
            })

        # Crear estructura byType
        by_type = {}
        for source_type, count in type_counts.items():
            items_per_chunk = 30
            total_chunks = (count + items_per_chunk - 1) // items_per_chunk

            # Aplicar límite de chunks si está configurado
            if max_chunks is not None and max_chunks > 0:
                total_chunks = min(total_chunks, max_chunks)

            by_type[source_type] = {
                "totalItems": count,
                "totalChunks": total_chunks,
                "itemsPerChunk": items_per_chunk,
                "chunkPrefix": f"{source_type}-all"
            }

        # Crear estructura categories
        categories = {}
        for row in category_data:
            source_type = row['type']
            if source_type not in categories:
                categories[source_type] = []

            items_per_chunk = 30
            total_chunks = (row['count'] + items_per_chunk - 1) // items_per_chunk

            # Aplicar límite de chunks si está configurado
            if max_chunks is not None and max_chunks > 0:
                total_chunks = min(total_chunks, max_chunks)

            categories[source_type].append({
                "category": row['category'],
                "title": row['title'],
                "count": row['count'],
                "isPriority": True,
                "totalChunks": total_chunks,
                "chunkPrefix": f"{source_type}-{row['category']}"
            })

        # Obtener estadísticas de shorts (videos cortos) con filtro de fecha si aplica
        shorts_date_filter = ""
        if months_back is not None:
            shorts_date_filter = f" AND pubDate_parsed >= DATE_SUB(NOW(), INTERVAL {months_back} MONTH)"

        shorts_query = f"SELECT COUNT(*) as count FROM feeds WHERE isShortVideo = 1{shorts_date_filter}"
        cursor.execute(shorts_query)
        shorts_count = cursor.fetchone()['count']

        # Calcular chunks de shorts
        items_per_chunk = 30
        shorts_chunks = (shorts_count + items_per_chunk - 1) // items_per_chunk if shorts_count > 0 else 0

        # Aplicar límite de chunks si está configurado
        if max_chunks is not None and max_chunks > 0 and shorts_chunks > 0:
            shorts_chunks = min(shorts_chunks, max_chunks)

        shorts_info = {
            "totalItems": shorts_count,
            "totalChunks": shorts_chunks,
            "itemsPerChunk": items_per_chunk,
            "chunkPrefix": "shorts-all"
        }

        # Construir metadata completo
        metadata = {
            "totalItems": total_items,
            "generatedAt": datetime.now().isoformat() + "Z",
            "sources": sources,
            "byType": by_type,
            "categories": categories,
            "shorts": shorts_info
        }

        return metadata

    except Error as e:
        log(f"❌ Error al generar metadata: {e}")
        return {}
    finally:
        cursor.close()

def get_all_source_types(db: DatabaseConnection) -> List[str]:
    """
    Obtiene todos los tipos de fuentes (sourceType) únicos de la base de datos.

    Args:
        db: Objeto de conexión a la base de datos

    Returns:
        Lista de sourceTypes únicos
    """
    cursor = db.get_cursor()
    if not cursor:
        return []

    try:
        query = "SELECT DISTINCT sourceType FROM feeds WHERE sourceType IS NOT NULL AND sourceType != ''"
        cursor.execute(query)
        results = cursor.fetchall()
        return [row['sourceType'] for row in results]
    except Error as e:
        log(f"❌ Error al obtener tipos de fuentes: {e}")
        return []
    finally:
        cursor.close()

def get_feeds_by_source_type(db: DatabaseConnection, source_type: str, limit: int = None, offset: int = 0, exclude_shorts: bool = False, exclude_categories: List[str] = None, months_back: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Obtiene feeds por tipo de fuente (sourceType).

    Args:
        db: Objeto de conexión a la base de datos
        source_type: Tipo de fuente (notice, forum, pappers, youtube, tiktok, etc.)
        limit: Número máximo de resultados (None = todos)
        offset: Offset para paginación
        exclude_shorts: Si es True, excluye videos cortos (isShortVideo=1) para sourceType='youtube' o 'tiktok'
        exclude_categories: Lista de categorías a excluir (opcional)
        months_back: Si se especifica, solo devuelve feeds de los últimos N meses (usa pubDate_parsed)

    Returns:
        Lista de diccionarios con los datos de los feeds
    """
    cursor = db.get_cursor()
    if not cursor:
        return []

    try:
        # Determinar si aplicar filtro de shorts
        short_filter = ""
        if exclude_shorts and source_type in ['youtube', 'tiktok']:
            short_filter = " AND isShortVideo = 0"

        # Determinar si aplicar filtro de categorías
        category_filter = ""
        if exclude_categories:
            placeholders = ', '.join(['%s'] * len(exclude_categories))
            category_filter = f" AND sourceCategory NOT IN ({placeholders})"

        # Determinar si aplicar filtro de fecha
        date_filter = ""
        if months_back is not None:
            date_filter = f" AND pubDate_parsed >= DATE_SUB(NOW(), INTERVAL {months_back} MONTH)"

        if limit:
            query = f"""
            SELECT id, title, link, pubDate, description, author,
                   sourceTitle, sourceUrl, sourceCategory, sourceType, sourceCountry,
                   content, image, isShortVideo, created_at
            FROM feeds
            WHERE sourceType = %s{short_filter}{category_filter}{date_filter}
            ORDER BY pubDate_parsed DESC
            LIMIT %s OFFSET %s
            """
            params = [source_type]
            if exclude_categories:
                params.extend(exclude_categories)
            params.extend([limit, offset])
            cursor.execute(query, tuple(params))
        else:
            query = f"""
            SELECT id, title, link, pubDate, description, author,
                   sourceTitle, sourceUrl, sourceCategory, sourceType, sourceCountry,
                   content, image, isShortVideo, created_at
            FROM feeds
            WHERE sourceType = %s{short_filter}{category_filter}{date_filter}
            ORDER BY pubDate_parsed DESC
            """
            params = [source_type]
            if exclude_categories:
                params.extend(exclude_categories)
            cursor.execute(query, tuple(params))

        results = cursor.fetchall()
        return results
    except Error as e:
        log(f"❌ Error al obtener feeds de tipo {source_type}: {e}")
        return []
    finally:
        cursor.close()

def get_feed_count_by_source_type(db: DatabaseConnection, source_type: str, exclude_shorts: bool = False, exclude_categories: List[str] = None, months_back: Optional[int] = None) -> int:
    """
    Obtiene el número de feeds de un sourceType específico.

    Args:
        db: Objeto de conexión a la base de datos
        source_type: Tipo de fuente
        exclude_shorts: Si es True, excluye videos cortos (isShortVideo=1) para sourceType='youtube' o 'tiktok'
        exclude_categories: Lista de categorías a excluir (opcional)
        months_back: Si se especifica, solo cuenta feeds de los últimos N meses (usa pubDate_parsed)

    Returns:
        Número de feeds del tipo especificado
    """
    cursor = db.get_cursor()
    if not cursor:
        return 0

    try:
        # Determinar si aplicar filtro de shorts
        short_filter = ""
        if exclude_shorts and source_type in ['youtube', 'tiktok']:
            short_filter = " AND isShortVideo = 0"

        # Determinar si aplicar filtro de categorías
        category_filter = ""
        params = [source_type]
        if exclude_categories:
            placeholders = ', '.join(['%s'] * len(exclude_categories))
            category_filter = f" AND sourceCategory NOT IN ({placeholders})"
            params.extend(exclude_categories)

        # Determinar si aplicar filtro de fecha
        date_filter = ""
        if months_back is not None:
            date_filter = f" AND pubDate_parsed >= DATE_SUB(NOW(), INTERVAL {months_back} MONTH)"

        query = f"SELECT COUNT(*) as count FROM feeds WHERE sourceType = %s{short_filter}{category_filter}{date_filter}"
        cursor.execute(query, tuple(params))
        result = cursor.fetchone()
        return result['count'] if result else 0
    except Error as e:
        log(f"❌ Error al contar feeds de tipo {source_type}: {e}")
        return 0
    finally:
        cursor.close()

def get_categories_by_source_type(db: DatabaseConnection, source_type: str) -> List[str]:
    """
    Obtiene todas las categorías únicas para un sourceType específico.

    Args:
        db: Objeto de conexión a la base de datos
        source_type: Tipo de fuente

    Returns:
        Lista de categorías únicas
    """
    cursor = db.get_cursor()
    if not cursor:
        return []

    try:
        query = """
        SELECT DISTINCT sourceCategory
        FROM feeds
        WHERE sourceType = %s
        AND sourceCategory IS NOT NULL
        AND sourceCategory != ''
        ORDER BY sourceCategory
        """
        cursor.execute(query, (source_type,))
        results = cursor.fetchall()
        return [row['sourceCategory'] for row in results]
    except Error as e:
        log(f"❌ Error al obtener categorías de tipo {source_type}: {e}")
        return []
    finally:
        cursor.close()

def get_feeds_by_source_type_and_category(db: DatabaseConnection, source_type: str, category: str, limit: int = None, offset: int = 0, exclude_shorts: bool = False, months_back: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Obtiene feeds filtrados por sourceType y category.

    Args:
        db: Objeto de conexión a la base de datos
        source_type: Tipo de fuente (notice, forum, pappers, youtube, tiktok, etc.)
        category: Categoría específica
        limit: Número máximo de resultados (None = todos)
        offset: Offset para paginación
        exclude_shorts: Si es True, excluye videos cortos (isShortVideo=1) para sourceType='youtube' o 'tiktok'
        months_back: Si se especifica, solo devuelve feeds de los últimos N meses (usa pubDate_parsed)

    Returns:
        Lista de diccionarios con los datos de los feeds
    """
    cursor = db.get_cursor()
    if not cursor:
        return []

    try:
        # Determinar si aplicar filtro de shorts
        short_filter = ""
        if exclude_shorts and source_type in ['youtube', 'tiktok']:
            short_filter = " AND isShortVideo = 0"

        # Determinar si aplicar filtro de fecha
        date_filter = ""
        if months_back is not None:
            date_filter = f" AND pubDate_parsed >= DATE_SUB(NOW(), INTERVAL {months_back} MONTH)"

        if limit:
            query = f"""
            SELECT id, title, link, pubDate, description, author,
                   sourceTitle, sourceUrl, sourceCategory, sourceType, sourceCountry,
                   content, image, isShortVideo, created_at
            FROM feeds
            WHERE sourceType = %s AND sourceCategory = %s{short_filter}{date_filter}
            ORDER BY pubDate_parsed DESC
            LIMIT %s OFFSET %s
            """
            cursor.execute(query, (source_type, category, limit, offset))
        else:
            query = f"""
            SELECT id, title, link, pubDate, description, author,
                   sourceTitle, sourceUrl, sourceCategory, sourceType, sourceCountry,
                   content, image, isShortVideo, created_at
            FROM feeds
            WHERE sourceType = %s AND sourceCategory = %s{short_filter}{date_filter}
            ORDER BY pubDate_parsed DESC
            """
            cursor.execute(query, (source_type, category))

        results = cursor.fetchall()
        return results
    except Error as e:
        log(f"❌ Error al obtener feeds de tipo {source_type} y categoría {category}: {e}")
        return []
    finally:
        cursor.close()

def get_feed_count_by_source_type_and_category(db: DatabaseConnection, source_type: str, category: str, exclude_shorts: bool = False, months_back: Optional[int] = None) -> int:
    """
    Obtiene el número de feeds para un sourceType y category específicos.

    Args:
        db: Objeto de conexión a la base de datos
        source_type: Tipo de fuente
        category: Categoría específica
        exclude_shorts: Si es True, excluye videos cortos (isShortVideo=1) para sourceType='youtube' o 'tiktok'
        months_back: Si se especifica, solo cuenta feeds de los últimos N meses (usa pubDate_parsed)

    Returns:
        Número de feeds
    """
    cursor = db.get_cursor()
    if not cursor:
        return 0

    try:
        # Determinar si aplicar filtro de shorts
        short_filter = ""
        if exclude_shorts and source_type in ['youtube', 'tiktok']:
            short_filter = " AND isShortVideo = 0"

        # Determinar si aplicar filtro de fecha
        date_filter = ""
        if months_back is not None:
            date_filter = f" AND pubDate_parsed >= DATE_SUB(NOW(), INTERVAL {months_back} MONTH)"

        query = f"SELECT COUNT(*) as count FROM feeds WHERE sourceType = %s AND sourceCategory = %s{short_filter}{date_filter}"
        cursor.execute(query, (source_type, category))
        result = cursor.fetchone()
        return result['count'] if result else 0
    except Error as e:
        log(f"❌ Error al contar feeds de tipo {source_type} y categoría {category}: {e}")
        return 0
    finally:
        cursor.close()

def update_feed_image(db: DatabaseConnection, feed_id: str, image_url: str) -> bool:
    """
    Actualiza el campo image de un feed específico.

    Args:
        db: Objeto de conexión a la base de datos
        feed_id: ID del feed a actualizar
        image_url: URL de la imagen a guardar

    Returns:
        True si se actualizó exitosamente, False en caso contrario
    """
    cursor = db.get_cursor()
    if not cursor:
        return False

    try:
        query = "UPDATE feeds SET image = %s WHERE id = %s"
        cursor.execute(query, (image_url, feed_id))
        db.commit()
        return True
    except Error as e:
        log(f"❌ Error al actualizar imagen del feed {feed_id}: {e}")
        db.rollback()
        return False
    finally:
        cursor.close()

def get_short_videos_count(db: DatabaseConnection, months_back: Optional[int] = None) -> int:
    """
    Obtiene el número total de videos cortos (isShortVideo=1) en la base de datos.

    Args:
        db: Objeto de conexión a la base de datos
        months_back: Si se especifica, solo cuenta videos de los últimos N meses (usa pubDate_parsed)

    Returns:
        Número de videos cortos
    """
    cursor = db.get_cursor()
    if not cursor:
        return 0

    try:
        # Determinar si aplicar filtro de fecha
        date_filter = ""
        if months_back is not None:
            date_filter = f" AND pubDate_parsed >= DATE_SUB(NOW(), INTERVAL {months_back} MONTH)"

        query = f"SELECT COUNT(*) as count FROM feeds WHERE isShortVideo = 1{date_filter}"
        cursor.execute(query)
        result = cursor.fetchone()
        return result['count'] if result else 0
    except Error as e:
        log(f"❌ Error al contar videos cortos: {e}")
        return 0
    finally:
        cursor.close()

def get_short_videos(db: DatabaseConnection, limit: int = None, offset: int = 0, months_back: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Obtiene todos los videos cortos (isShortVideo=1) de la base de datos.

    Args:
        db: Objeto de conexión a la base de datos
        limit: Número máximo de resultados (None = todos)
        offset: Offset para paginación
        months_back: Si se especifica, solo devuelve videos de los últimos N meses (usa pubDate_parsed)

    Returns:
        Lista de diccionarios con los datos de los videos cortos
    """
    cursor = db.get_cursor()
    if not cursor:
        return []

    try:
        # Determinar si aplicar filtro de fecha
        date_filter = ""
        if months_back is not None:
            date_filter = f" AND pubDate_parsed >= DATE_SUB(NOW(), INTERVAL {months_back} MONTH)"

        if limit:
            query = f"""
            SELECT id, title, link, pubDate, description, author,
                   sourceTitle, sourceUrl, sourceCategory, sourceType, sourceCountry,
                   content, image, isShortVideo, created_at
            FROM feeds
            WHERE isShortVideo = 1{date_filter}
            ORDER BY pubDate_parsed DESC
            LIMIT %s OFFSET %s
            """
            cursor.execute(query, (limit, offset))
        else:
            query = f"""
            SELECT id, title, link, pubDate, description, author,
                   sourceTitle, sourceUrl, sourceCategory, sourceType, sourceCountry,
                   content, image, isShortVideo, created_at
            FROM feeds
            WHERE isShortVideo = 1{date_filter}
            ORDER BY pubDate_parsed DESC
            """
            cursor.execute(query)

        results = cursor.fetchall()
        return results
    except Error as e:
        log(f"❌ Error al obtener videos cortos: {e}")
        return []
    finally:
        cursor.close()
