import json
import uuid
from pathlib import Path
from typing import List, Dict, Any
from config.loader import load_featured_pappers_config
from utils.logger import log
from database.connection import DatabaseConnection
from database.operations import insert_feed

def make_deterministic_uuid(fields: dict, namespace: uuid.UUID = uuid.NAMESPACE_DNS) -> str:
    name = json.dumps(fields, sort_keys=True, separators=(',', ':'))
    return str(uuid.uuid5(namespace, name))

def generate_featured_pappers(db: DatabaseConnection = None, output_dir: str = "assets", config_path: str = None) -> dict:
    """
    Genera archivos JSON para los pappers destacados configurados en feeds_config.yaml.

    Args:
        db: Conexión a la base de datos (opcional)
        output_dir: Directorio de salida (por defecto 'assets')
        config_path: Ruta al archivo YAML de configuración

    Returns:
        Diccionario con estadísticas de generación
    """
    stats = {
        'success': False,
        'total_items': 0,
        'files_generated': []
    }

    if config_path is None:
        config_path = str(Path(__file__).parent.parent.parent / "feeds_config.yaml")

    try:
        featured_list = load_featured_pappers_config(config_path)
        if not featured_list:
            log("⚠️ No se encontraron pappers destacados en la configuración")
            return stats

        assets_dir = Path(output_dir)
        assets_dir.mkdir(exist_ok=True)

        items_data = []
        for paper in featured_list:
            title = paper.get('title', '')
            link = paper.get('link', '')

            # Generar UUID único y determinista
            uuid_data = {"feed_url": link, "source_type": "pappers", "title": title}
            entry_id = make_deterministic_uuid(uuid_data)

            # Generar linkPdf
            if '/abs/' in link:
                link_pdf = link.replace('/abs/', '/pdf/')
            else:
                link_pdf = link

            # Si es de arxiv o similar
            source_category = "arXiv_Featured" if "arxiv.org" in link else "featured"

            item = {
                "id": entry_id,
                "title": title,
                "link": link,
                "linkPdf": link_pdf,
                "pubDate": "2025-01-01T00:00:00+00:00",
                "description": paper.get('description', title),
                "author": paper.get('author', 'Destacado'),
                "sourceTitle": "Pappers Destacados",
                "sourceUrl": link,
                "sourceCategory": source_category,
                "sourceType": "pappers",
                "sourceCountry": "",
                "content": "",
                "image": "",
                "isShortVideo": 0
            }
            items_data.append(item)

            # Guardar en base de datos si hay conexión
            if db:
                feed_data = {
                    'id': entry_id,
                    'title': title,
                    'link': link,
                    'linkPdf': link_pdf,
                    'pubDate': item['pubDate'],
                    'description': item['description'],
                    'author': item['author'],
                    'sourceTitle': item['sourceTitle'],
                    'sourceUrl': item['sourceUrl'],
                    'sourceCategory': source_category,
                    'sourceType': item['sourceType'],
                    'sourceCountry': item['sourceCountry'],
                    'content': item['content'],
                    'image': item['image'],
                    'isShortVideo': item['isShortVideo'],
                    'raw_data': json.dumps(paper, ensure_ascii=False)
                }
                insert_feed(db, feed_data)

        # Archivos de salida
        output_filenames = [
            "pappers-featured-chunk-0.json",
            "pappers-featured.json",
            "pappers-pappers_destacados-chunk-0.json"
        ]

        for filename in output_filenames:
            filepath = assets_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(items_data, f, ensure_ascii=False, indent=2)
            stats['files_generated'].append(filename)

        stats['total_items'] = len(items_data)
        stats['success'] = True
        log(f"✅ Generados pappers destacados ({len(items_data)} items) en {output_dir}")
        return stats

    except Exception as e:
        log(f"❌ Error al generar pappers destacados: {e}")
        return stats
