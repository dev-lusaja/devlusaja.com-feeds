import json
import glob
from pathlib import Path
from database.connection import DatabaseConnection
from database.operations import create_feeds_table, insert_feed, get_feed_count
from utils.logger import log

def seed_database_from_assets(assets_dir: str = "assets") -> int:
    """
    Puebla la base de datos SQLite desde todos los archivos JSON de chunks en assets/.
    """
    assets_path = Path(assets_dir)
    if not assets_path.exists():
        log("⚠️ No existe el directorio assets/")
        return 0

    json_files = list(assets_path.glob("*.json"))
    log(f"📂 Encontrados {len(json_files)} archivos JSON en assets/ para sembrar la BD")

    inserted_total = 0
    with DatabaseConnection() as db:
        create_feeds_table(db)

        for json_file in json_files:
            if json_file.name == "metadata.json":
                continue

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    items = json.load(f)
                    if not isinstance(items, list):
                        continue

                    for item in items:
                        if not isinstance(item, dict) or 'id' not in item or 'link' not in item:
                            continue

                        source_cat = str(item.get('sourceCategory', ''))
                        feed_link = str(item.get('link', ''))

                        # Generar linkPdf si aplica
                        link_pdf = item.get('linkPdf', '')
                        if not link_pdf and source_cat.lower().startswith('arxiv_'):
                            link_pdf = feed_link.replace('/abs/', '/pdf/') if '/abs/' in feed_link else feed_link

                        feed_data = {
                            'id': item['id'],
                            'title': item.get('title', ''),
                            'link': feed_link,
                            'pubDate': item.get('pubDate', ''),
                            'description': item.get('description', ''),
                            'author': item.get('author', ''),
                            'sourceTitle': item.get('sourceTitle', ''),
                            'sourceUrl': item.get('sourceUrl', ''),
                            'sourceCategory': source_cat,
                            'sourceType': item.get('sourceType', ''),
                            'sourceCountry': item.get('sourceCountry', ''),
                            'content': item.get('content', ''),
                            'image': item.get('image', ''),
                            'isShortVideo': item.get('isShortVideo', 0),
                            'linkPdf': link_pdf,
                            'raw_data': json.dumps(item, ensure_ascii=False)
                        }

                        if insert_feed(db, feed_data):
                            inserted_total += 1

            except Exception as e:
                log(f"⚠️ Error al leer {json_file.name}: {e}")

        total_in_db = get_feed_count(db)
        log(f"✅ Sembrado completado. Feeds en la BD: {total_in_db}")
        return total_in_db

if __name__ == "__main__":
    seed_database_from_assets()
