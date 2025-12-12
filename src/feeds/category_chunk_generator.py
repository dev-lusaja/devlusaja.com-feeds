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

def generate_category_chunks(db: DatabaseConnection, output_dir: str = "assets", items_per_chunk: int = 30, months_back: int = 2, max_chunks: int = None) -> dict:
    """
    Genera archivos JSON con chunks de feeds agrupados por sourceType y category.
    Patrón de nombre: {sourceType}-{category}-chunk-{number}.json

    Args:
        db: Objeto de conexión a la base de datos
        output_dir: Directorio donde guardar los archivos (por defecto 'assets')
        items_per_chunk: Número máximo de feeds por chunk (por defecto 30)
        months_back: Número de meses hacia atrás para filtrar feeds (por defecto 2)
        max_chunks: Número máximo de chunks a generar por categoría (None = sin límite)

    Returns:
        Diccionario con estadísticas de generación
    """
    stats = {
        'success': False,
        'total_files': 0,
        'by_source_type': {}
    }

    try:
        # Crear directorio si no existe
        assets_dir = Path(output_dir)
        assets_dir.mkdir(exist_ok=True)

        # Obtener todos los tipos de fuentes
        source_types = get_all_source_types(db)

        if not source_types:
            return stats

        # Procesar cada tipo de fuente
        for source_type in source_types:
            # Obtener todas las categorías para este tipo
            categories = get_categories_by_source_type(db, source_type)

            if not categories:
                continue

            # Excluir shorts (isShortVideo=1) para YouTube y TikTok
            # Estos tienen sus propios chunks separados (shorts-all-chunk-*)
            exclude_shorts = source_type in ['youtube', 'tiktok']
            stats['by_source_type'][source_type] = {}

            # Procesar cada categoría
            for category in categories:
                # Obtener conteo total de feeds para este tipo y categoría (últimos N meses)
                total_feeds = get_feed_count_by_source_type_and_category(db, source_type, category, exclude_shorts=exclude_shorts, months_back=months_back)

                if total_feeds == 0:
                    continue

                # Calcular número de chunks necesarios
                total_chunks = (total_feeds + items_per_chunk - 1) // items_per_chunk

                # Aplicar límite de chunks si está configurado
                if max_chunks is not None and max_chunks > 0:
                    total_chunks = min(total_chunks, max_chunks)

                # Generar cada chunk
                for chunk_number in range(total_chunks):
                    offset = chunk_number * items_per_chunk

                    # Obtener feeds para este chunk (últimos N meses)
                    feeds = get_feeds_by_source_type_and_category(db, source_type, category, limit=items_per_chunk, offset=offset, exclude_shorts=exclude_shorts, months_back=months_back)

                    if not feeds:
                        continue

                    # Formatear feeds según la estructura requerida
                    feeds_data = []
                    for feed in feeds:
                        feed_item = {
                            "id": feed['id'],
                            "title": feed['title'],
                            "link": feed['link'],
                            "pubDate": feed['pubDate'],
                            "description": feed['description'],
                            "author": feed['author'],
                            "sourceTitle": feed['sourceTitle'],
                            "sourceUrl": feed['sourceUrl'],
                            "sourceCategory": feed['sourceCategory'],
                            "sourceType": feed['sourceType'],
                            "sourceCountry": feed['sourceCountry'],
                            "content": feed['content'],
                            "image": feed['image'],
                            "isShortVideo": feed['isShortVideo']
                        }
                        feeds_data.append(feed_item)

                    # Nombre del archivo: {sourceType}-{category}-chunk-{number}.json
                    filename = f"{source_type}-{category}-chunk-{chunk_number}.json"
                    filepath = assets_dir / filename

                    # Guardar chunk en archivo JSON
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(feeds_data, f, ensure_ascii=False, indent=2)

                    stats['total_files'] += 1

                # Guardar estadísticas por categoría
                stats['by_source_type'][source_type][category] = {
                    'chunks': total_chunks,
                    'total_feeds': total_feeds
                }

        stats['success'] = True
        return stats

    except Exception as e:
        log(f"❌ Error al generar chunks de categoría: {e}")
        return stats
