import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from database.connection import DatabaseConnection
from database.operations import (
    get_all_source_types,
    get_feeds_by_source_type,
    get_feed_count_by_source_type
)
from config.loader import get_chunks_all_exclusions
from utils.logger import log

def generate_feed_chunks(db: DatabaseConnection, output_dir: str = "assets", items_per_chunk: int = 30, config_path: str = None) -> bool:
    """
    Genera archivos JSON con chunks de feeds agrupados por sourceType.
    Las exclusiones de categorías para archivos -all se configuran en feeds_config.yaml.

    Args:
        db: Objeto de conexión a la base de datos
        output_dir: Directorio donde guardar los archivos (por defecto 'assets')
        items_per_chunk: Número máximo de feeds por chunk (por defecto 30)
        config_path: Ruta al archivo de configuración YAML (por defecto 'feeds_config.yaml')

    Returns:
        True si se generaron exitosamente, False en caso contrario
    """
    # Si no se proporciona config_path, usar el path por defecto
    if config_path is None:
        config_path = str(Path(__file__).parent.parent.parent / "feeds_config.yaml")
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
            # Para YouTube y TikTok, excluir shorts (isShortVideo=1)
            #exclude_shorts = (source_type in ['youtube', 'tiktok'])
            exclude_shorts = False

            # Obtener categorías a excluir de los archivos -all desde la configuración
            exclude_categories = get_chunks_all_exclusions(config_path, source_type)
            if exclude_categories:
                log(f"📦 Excluyendo categorías {exclude_categories} de {source_type}-all")

            # Obtener conteo total de feeds para este tipo
            total_feeds = get_feed_count_by_source_type(db, source_type, exclude_shorts=exclude_shorts, exclude_categories=exclude_categories)

            if total_feeds == 0:
                log(f"⚠️ No hay feeds para el tipo '{source_type}'")
                continue

            # Calcular número de chunks necesarios
            total_chunks = (total_feeds + items_per_chunk - 1) // items_per_chunk

            log(f"📦 Generando {total_chunks} chunks para tipo '{source_type}' ({total_feeds} feeds)")

            # Generar cada chunk
            for chunk_number in range(total_chunks):
                offset = chunk_number * items_per_chunk

                # Obtener feeds para este chunk
                feeds = get_feeds_by_source_type(db, source_type, limit=items_per_chunk, offset=offset, exclude_shorts=exclude_shorts, exclude_categories=exclude_categories)

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
                        "image": feed.get('image', ''),
                        "isShortVideo": feed.get('isShortVideo', 0)
                    }
                    feeds_data.append(feed_item)

                # Nombre del archivo: {sourceType}-all-chunk-{number}.json
                filename = f"{source_type}-all-chunk-{chunk_number}.json"
                filepath = assets_dir / filename

                # Guardar chunk en archivo JSON
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(feeds_data, f, ensure_ascii=False, indent=2)

                total_files_generated += 1
                log(f"  ✅ Generado: {filename} ({len(feeds_data)} feeds)")

        log(f"✅ Total de archivos generados: {total_files_generated}")
        return True

    except Exception as e:
        log(f"❌ Error al generar chunks: {e}")
        return False

def save_metadata_json(metadata: Dict[str, Any], output_dir: str = "assets") -> bool:
    """
    Guarda el metadata en un archivo JSON en la carpeta assets.

    Args:
        metadata: Diccionario con el metadata a guardar
        output_dir: Directorio donde guardar el archivo (por defecto 'assets')

    Returns:
        True si se guardó exitosamente, False en caso contrario
    """
    try:
        # Crear directorio si no existe
        assets_dir = Path(output_dir)
        assets_dir.mkdir(exist_ok=True)

        # Ruta del archivo
        output_path = assets_dir / "metadata.json"

        # Guardar JSON con formato legible
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        log(f"✅ Metadata guardado exitosamente en {output_path}")
        return True

    except Exception as e:
        log(f"❌ Error al guardar metadata: {e}")
        return False
