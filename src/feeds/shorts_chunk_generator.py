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


def generate_shorts_chunks(db: DatabaseConnection, output_dir: str = "assets", items_per_chunk: int = 30) -> bool:
    """
    Genera archivos JSON con chunks de videos cortos (isShortVideo=1).

    Args:
        db: Objeto de conexión a la base de datos
        output_dir: Directorio donde guardar los archivos (por defecto 'assets')
        items_per_chunk: Número máximo de videos cortos por chunk (por defecto 30)

    Returns:
        True si se generaron exitosamente, False en caso contrario
    """
    try:
        # Crear directorio si no existe
        assets_dir = Path(output_dir)
        assets_dir.mkdir(exist_ok=True)

        # Obtener conteo total de videos cortos
        total_shorts = get_short_videos_count(db)

        if total_shorts == 0:
            log("⚠️ No hay videos cortos en la base de datos")
            return False

        # Calcular número de chunks necesarios
        total_chunks = (total_shorts + items_per_chunk - 1) // items_per_chunk

        log(f"📦 Generando {total_chunks} chunks de shorts ({total_shorts} videos cortos)")

        total_files_generated = 0

        # Generar cada chunk
        for chunk_number in range(total_chunks):
            offset = chunk_number * items_per_chunk

            # Obtener videos cortos para este chunk
            shorts = get_short_videos(db, limit=items_per_chunk, offset=offset)

            if not shorts:
                continue

            # Formatear videos cortos según la estructura requerida
            shorts_data = []
            for short in shorts:
                short_item = {
                    "id": short.get('id', ''),
                    "title": short.get('title', ''),
                    "link": short.get('link', ''),
                    "pubDate": short.get('pubDate', ''),
                    "description": short.get('description', ''),
                    "author": short.get('author', 'Desconocido'),
                    "sourceTitle": short.get('sourceTitle', ''),
                    "sourceUrl": short.get('sourceUrl', ''),
                    "sourceCategory": short.get('sourceCategory', ''),
                    "sourceType": short.get('sourceType', ''),
                    "sourceCountry": short.get('sourceCountry', ''),
                    "content": short.get('content', ''),
                    "image": short.get('image', ''),
                    "isShortVideo": short.get('isShortVideo', 1)
                }
                shorts_data.append(short_item)

            # Nombre del archivo: shorts-all-chunk-{number}.json
            filename = f"shorts-all-chunk-{chunk_number}.json"
            filepath = assets_dir / filename

            # Guardar chunk en archivo JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(shorts_data, f, ensure_ascii=False, indent=2)

            total_files_generated += 1
            log(f"  ✅ Generado: {filename} ({len(shorts_data)} shorts)")

        log(f"✅ Total de archivos de shorts generados: {total_files_generated}")
        return True

    except Exception as e:
        log(f"❌ Error al generar chunks de shorts: {e}")
        return False
