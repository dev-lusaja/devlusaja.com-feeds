import json
from pathlib import Path
from typing import List, Dict, Any
from database.connection import DatabaseConnection
from database.operations import (
    get_all_source_types,
    get_categories_by_source_type,
    get_feeds_by_source_type_and_category,
    get_feed_count_by_source_type_and_category
)
from utils.logger import log

def generate_category_chunks(db: DatabaseConnection, output_dir: str = "assets", items_per_chunk: int = 30) -> bool:
    """
    Genera archivos JSON con chunks de feeds agrupados por sourceType y category.
    Patrón de nombre: {sourceType}-{category}-chunk-{number}.json

    Args:
        db: Objeto de conexión a la base de datos
        output_dir: Directorio donde guardar los archivos (por defecto 'assets')
        items_per_chunk: Número máximo de feeds por chunk (por defecto 30)

    Returns:
        True si se generaron exitosamente, False en caso contrario
    """
    try:
        # Crear directorio si no existe
        assets_dir = Path(output_dir)
        assets_dir.mkdir(exist_ok=True)

        # Obtener todos los tipos de fuentes
        source_types = get_all_source_types(db)

        if not source_types:
            log("⚠️ No se encontraron tipos de fuentes en la base de datos")
            return False

        total_files_generated = 0

        # Procesar cada tipo de fuente
        for source_type in source_types:
            # Obtener todas las categorías para este tipo
            categories = get_categories_by_source_type(db, source_type)

            if not categories:
                log(f"⚠️ No se encontraron categorías para el tipo '{source_type}'")
                continue

            log(f"📦 Procesando tipo '{source_type}' con {len(categories)} categorías")

            # Procesar cada categoría
            for category in categories:
                # Obtener conteo total de feeds para este tipo y categoría
                total_feeds = get_feed_count_by_source_type_and_category(db, source_type, category)

                if total_feeds == 0:
                    log(f"  ⚠️ No hay feeds para {source_type}/{category}")
                    continue

                # Calcular número de chunks necesarios
                total_chunks = (total_feeds + items_per_chunk - 1) // items_per_chunk

                log(f"  📄 Generando {total_chunks} chunks para {source_type}/{category} ({total_feeds} feeds)")

                # Generar cada chunk
                for chunk_number in range(total_chunks):
                    offset = chunk_number * items_per_chunk

                    # Obtener feeds para este chunk
                    feeds = get_feeds_by_source_type_and_category(db, source_type, category, limit=items_per_chunk, offset=offset)

                    if not feeds:
                        continue

                    # Formatear feeds según la estructura requerida
                    feeds_data = []
                    for feed in feeds:
                        feed_item = {
                            "id": feed.get('id', ''),
                            "title": feed.get('title', ''),
                            "link": feed.get('link', ''),
                            "pubDate": feed.get('pubDate', ''),
                            "description": feed.get('description', ''),
                            "author": feed.get('author', 'Desconocido'),
                            "sourceTitle": feed.get('sourceTitle', ''),
                            "sourceUrl": feed.get('sourceUrl', ''),
                            "sourceCategory": feed.get('sourceCategory', ''),
                            "sourceType": feed.get('sourceType', ''),
                            "content": feed.get('content', ''),
                            "image": feed.get('image', '')
                        }
                        feeds_data.append(feed_item)

                    # Nombre del archivo: {sourceType}-{category}-chunk-{number}.json
                    filename = f"{source_type}-{category}-chunk-{chunk_number}.json"
                    filepath = assets_dir / filename

                    # Guardar chunk en archivo JSON
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(feeds_data, f, ensure_ascii=False, indent=2)

                    total_files_generated += 1

        log(f"✅ Total de archivos de categoría generados: {total_files_generated}")
        return True

    except Exception as e:
        log(f"❌ Error al generar chunks de categoría: {e}")
        return False
