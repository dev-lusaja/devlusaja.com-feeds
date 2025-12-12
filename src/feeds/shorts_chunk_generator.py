"""
Generador de chunks para videos cortos (shorts).

Este módulo genera archivos JSON con chunks de videos cortos (isShortVideo=1)
independientemente de su sourceType (YouTube, TikTok, etc.).
"""

import json
from pathlib import Path
from typing import Dict, Any
from database.connection import DatabaseConnection
from database.operations import get_short_videos_count, get_short_videos
from utils.logger import log


def generate_shorts_chunks(db: DatabaseConnection, output_dir: str = "assets", items_per_chunk: int = 30, months_back: int = 2, max_chunks: int = None) -> dict:
    """
    Genera archivos JSON con chunks de videos cortos (isShortVideo=1).

    Args:
        db: Objeto de conexión a la base de datos
        output_dir: Directorio donde guardar los archivos (por defecto 'assets')
        items_per_chunk: Número máximo de videos cortos por chunk (por defecto 30)
        months_back: Número de meses hacia atrás para filtrar feeds (por defecto 2)
        max_chunks: Número máximo de chunks a generar (None = sin límite)

    Returns:
        Diccionario con estadísticas de generación
    """
    stats = {
        'success': False,
        'total_files': 0,
        'total_shorts': 0,
        'total_chunks': 0
    }

    try:
        # Crear directorio si no existe
        assets_dir = Path(output_dir)
        assets_dir.mkdir(exist_ok=True)

        # Obtener conteo total de videos cortos (últimos N meses)
        total_shorts = get_short_videos_count(db, months_back=months_back)

        if total_shorts == 0:
            return stats

        # Calcular número de chunks necesarios
        total_chunks = (total_shorts + items_per_chunk - 1) // items_per_chunk

        # Aplicar límite de chunks si está configurado
        if max_chunks is not None and max_chunks > 0:
            total_chunks = min(total_chunks, max_chunks)

        # Generar cada chunk
        for chunk_number in range(total_chunks):
            offset = chunk_number * items_per_chunk

            # Obtener videos cortos para este chunk (últimos N meses)
            shorts = get_short_videos(db, limit=items_per_chunk, offset=offset, months_back=months_back)

            if not shorts:
                continue

            # Formatear videos cortos según la estructura requerida
            shorts_data = []
            for short in shorts:
                short_item = {
                    "id": short['id'],
                    "title": short['title'],
                    "link": short['link'],
                    "pubDate": short['pubDate'],
                    "description": short['description'],
                    "author": short['author'],
                    "sourceTitle": short['sourceTitle'],
                    "sourceUrl": short['sourceUrl'],
                    "sourceCategory": short['sourceCategory'],
                    "sourceType": short['sourceType'],
                    "sourceCountry": short['sourceCountry'],
                    "content": short['content'],
                    "image": short['image'],
                    "isShortVideo": short['isShortVideo']
                }
                shorts_data.append(short_item)

            # Nombre del archivo: shorts-all-chunk-{number}.json
            filename = f"shorts-all-chunk-{chunk_number}.json"
            filepath = assets_dir / filename

            # Guardar chunk en archivo JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(shorts_data, f, ensure_ascii=False, indent=2)

            stats['total_files'] += 1

        stats['total_shorts'] = total_shorts
        stats['total_chunks'] = total_chunks
        stats['success'] = True
        return stats

    except Exception as e:
        log(f"❌ Error al generar chunks de shorts: {e}")
        return stats
