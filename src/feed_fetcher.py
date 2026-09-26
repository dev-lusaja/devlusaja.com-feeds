import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from config.loader import load_feeds_config, get_feeds_months_back, get_max_chunks_per_category, SEPARATE_SOURCE_TYPES, get_db_path
from feeds.fetcher import fetch_feed
from feeds.saver import save_feed, exits_feed
from feeds.dataframe_builder import build_dataframe, save_dataframe, save_dataframe_json
from database.connection import DatabaseConnection
from database.operations import (
    create_feeds_table,
    insert_feeds_from_dataframe,
    get_feed_count,
    was_executed_today,
    register_execution,
)
from feeds.chunk_generator import generate_feed_chunks
from feeds.metadata_generator import generate_all_metadata, generate_separate_assets
from feeds.category_chunk_generator import generate_category_chunks
from feeds.shorts_chunk_generator import generate_shorts_chunks
from feeds.image_postprocessor import process_feeds_images
from utils.cleanup import cleanup_json_files
from utils.logger import log
from utils.stats import ExecutionStats

# Cargar variables de entorno
load_dotenv()

# Configuración
ITEMS_PER_CHUNK = 30  # Número máximo de feeds por chunk
IMAGES_LIMIT = 20  # Máximo de noticias sin imagen a completar por corrida

def main(force: bool = False, source_type: str = None):
    # Inicializar estadísticas
    stats = ExecutionStats()

    # Verificar si ya se ejecutó hoy (solo si MySQL está habilitado y no es force)
    if not force:
        try:
            with DatabaseConnection() as db:
                create_feeds_table(db)
                if was_executed_today(db):
                    print("⚠️ El proceso ya se ejecutó hoy. Usa --force para ejecutar de nuevo.")
                    return
        except Exception as e:
            print(f"⚠️ No se pudo verificar ejecución previa: {e}")

    if force:
        print("🔄 Modo FORCE activado - descargando datos del día nuevamente\n")

    config_path = Path(__file__).parent.parent / "feeds_config.yaml"
    feeds = load_feeds_config(config_path)
    stats.total_feeds_config = len(feeds)
    to_fetch = [f for f in feeds if (f['sourceType'] == source_type if source_type else f['sourceType'] not in SEPARATE_SOURCE_TYPES)]

    # Obtener configuración de meses hacia atrás para filtrar feeds
    months_back = get_feeds_months_back(config_path)
    print(f"📅 Filtrando feeds de los últimos {months_back} meses")

    # Obtener configuración de máximo de chunks por categoría
    max_chunks = get_max_chunks_per_category(config_path)
    if max_chunks:
        print(f"📦 Límite de chunks por categoría: {max_chunks}")

    # Descargar feeds (sin logs)
    print("📡 Descargando feeds...", end='', flush=True)
    for feed_info in to_fetch:
        url = feed_info['url']
        category = feed_info['category']

        if exits_feed(category) and not force:
            stats.feeds_cached += 1
            continue

        feed = fetch_feed(url, category)
        feed_path = save_feed(feed, category)
        stats.feeds_downloaded += 1
    print(" ✓")

    # Construir DataFrame con todos los feeds
    print("📊 Construyendo DataFrame...", end='', flush=True)
    df = build_dataframe(feeds_dir="feeds_data", feeds_config=feeds)
    if not df.empty:  # feeds_data/ puede traer caché de otros sourceTypes: cada BD guarda solo lo suyo
        df = df[df['sourceType'].isin({f['sourceType'] for f in to_fetch})]
    stats.total_entries = len(df) if not df.empty else 0
    print(" ✓")

    if not df.empty:
        feeds_processed = len(df)

        try:
            # Guardar en base de datos
            print("💾 Guardando en MySQL...", end='', flush=True)
            with DatabaseConnection(get_db_path(source_type)) as db:
                create_feeds_table(db)
                stats.feeds_before = get_feed_count(db)
                db_stats = insert_feeds_from_dataframe(db, df)
                stats.feeds_inserted = db_stats['inserted']
                stats.feeds_skipped = db_stats['skipped']
                stats.feeds_errors = db_stats['errors']
                stats.feeds_after = get_feed_count(db)
                if not source_type:  # no marcar el día como ejecutado por una corrida parcial
                    register_execution(db, feeds_processed, stats.feeds_inserted, 'completed')
            print(" ✓")

            # Completar imágenes faltantes de las últimas noticias antes de generar los assets
            if not source_type:
                with DatabaseConnection() as db:
                    process_feeds_images(db, source_type='notice', category=None, limit=IMAGES_LIMIT)

            # Generar metadata
            print("📋 Generando metadata...", end='', flush=True)
            with DatabaseConnection() as db:
                generate_all_metadata(db, feeds, months_back=months_back, max_chunks=max_chunks)
            print(" ✓")

            # Generar chunks por sourceType
            print("📦 Generando chunks por tipo de fuente...", end='', flush=True)
            with DatabaseConnection() as db:
                chunk_stats = generate_feed_chunks(db, output_dir="assets", items_per_chunk=ITEMS_PER_CHUNK, months_back=months_back, max_chunks=max_chunks)
                if chunk_stats['success']:
                    stats.total_chunk_files = chunk_stats['total_files']
                    for source_type, source_stats in chunk_stats['by_source_type'].items():
                        stats.add_chunk_by_source_type(
                            source_type,
                            source_stats['chunks'],
                            source_stats['total_feeds']
                        )
            print(" ✓")

            # Generar chunks por categoría
            print("📋 Generando chunks por categoría...", end='', flush=True)
            with DatabaseConnection() as db:
                category_stats = generate_category_chunks(db, output_dir="assets", items_per_chunk=ITEMS_PER_CHUNK, months_back=months_back, max_chunks=max_chunks)
                if category_stats['success']:
                    stats.category_chunk_files = category_stats['total_files']
                    for source_type, categories in category_stats['by_source_type'].items():
                        for category, cat_stats in categories.items():
                            stats.add_chunk_by_category(
                                source_type,
                                category,
                                cat_stats['chunks'],
                                cat_stats['total_feeds']
                            )
            print(" ✓")

            # Generar chunks de shorts
            print("🎬 Generando chunks de shorts...", end='', flush=True)
            with DatabaseConnection() as db:
                shorts_stats = generate_shorts_chunks(db, output_dir="assets", items_per_chunk=ITEMS_PER_CHUNK, months_back=months_back, max_chunks=max_chunks)
                if shorts_stats['success']:
                    stats.shorts_chunks = shorts_stats['total_chunks']
                    stats.shorts_total = shorts_stats['total_shorts']
            print(" ✓")

            # Metadata y chunks de SEPARATE_SOURCE_TYPES, cada uno desde su propia BD
            print("📰 Generando assets de fuentes separadas...", end='', flush=True)
            generate_separate_assets(feeds, max_chunks=max_chunks, items_per_chunk=ITEMS_PER_CHUNK)
            print(" ✓")

            # Limpiar archivos JSON
            print("🧹 Limpiando archivos...", end='', flush=True)
            stats.json_files_deleted = cleanup_json_files()
            print(" ✓")

        except Exception as e:
            print(f"\n❌ Error al guardar en MySQL: {e}")
            try:
                with DatabaseConnection() as db:
                    register_execution(db, feeds_processed, 0, 'error')
            except:
                pass
    else:
        print("⚠️ No se pudo generar el DataFrame (sin datos)")

    # Imprimir resumen final
    stats.print_summary()

if __name__ == "__main__":
    # Verificar si se pasó el parámetro --force
    force = '--force' in sys.argv
    source_type = sys.argv[sys.argv.index('--source-type') + 1] if '--source-type' in sys.argv else None
    main(force=force, source_type=source_type)
