import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from mysql.connector import Error
from database.connection import DatabaseConnection
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
            description TEXT,
            author LONGTEXT,
            sourceTitle VARCHAR(255),
            sourceUrl TEXT,
            sourceCategory VARCHAR(255),
            sourceType VARCHAR(50),
            content LONGTEXT,
            image TEXT,
            raw_data LONGTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_source_category (sourceCategory),
            INDEX idx_source_type (sourceType),
            INDEX idx_pub_date (pubDate),
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
            sourceTitle, sourceUrl, sourceCategory, sourceType,
            content, image, raw_data
        ) VALUES (
            %(id)s, %(title)s, %(link)s, %(pubDate)s, %(description)s, %(author)s,
            %(sourceTitle)s, %(sourceUrl)s, %(sourceCategory)s, %(sourceType)s,
            %(content)s, %(image)s, %(raw_data)s
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
            'content': row['content'] if pd.notna(row['content']) else '',
            'image': row['image'] if pd.notna(row['image']) else '',
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
