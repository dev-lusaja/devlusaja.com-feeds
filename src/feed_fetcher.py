import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from config.loader import load_feeds_config
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
    get_metadata_from_db
)
from database.backup import create_mysql_backup
from feeds.chunk_generator import generate_feed_chunks
from feeds.metadata_generator import save_metadata_json
from feeds.category_chunk_generator import generate_category_chunks
from feeds.shorts_chunk_generator import generate_shorts_chunks
from utils.cleanup import cleanup_json_files
from utils.logger import log

# Cargar variables de entorno
load_dotenv()

# Configuración
ITEMS_PER_CHUNK = 30  # Número máximo de feeds por chunk

def main(force: bool = False):
    # Verificar si MySQL está configurado
    use_mysql = os.getenv('USE_MYSQL', 'false').lower() == 'true'

    # Verificar si ya se ejecutó hoy (solo si MySQL está habilitado y no es force)
    if use_mysql and not force:
        try:
            with DatabaseConnection() as db:
                create_feeds_table(db)
                if was_executed_today(db):
                    log("⚠️ El proceso ya se ejecutó hoy. Usa --force para ejecutar de nuevo.")
                    return
        except Exception as e:
            log(f"⚠️ No se pudo verificar ejecución previa: {e}")

    if force:
        log("🔄 Modo FORCE activado - descargando datos del día nuevamente")

    config_path = Path(__file__).parent.parent / "feeds_config.yaml"
    feeds = load_feeds_config(config_path)

    downloaded  = 0
    cached      = 0
    for feed_info in feeds:
        url = feed_info['url']
        category = feed_info['category']

        if exits_feed(category) and not force:
            cached += 1
            log(f"⚠️ El feed para '{category}' ya existe hoy. Saltando descarga.")
            continue

        feed = fetch_feed(url, category)
        feed_path = save_feed(feed, category)
        downloaded += 1

    log(f"📍 Feeds descargados: {downloaded}/{len(feeds)}")
    log(f"📍 Feeds en cache: {cached}/{len(feeds)}")

    # Construir DataFrame con todos los feeds
    log("\n📊 Construyendo DataFrame con todos los feeds...")
    df = build_dataframe(feeds_dir="feeds_data", feeds_config=feeds)

    if not df.empty:
        # Guardar DataFrame en CSV
        #save_dataframe(df, output_path="feeds_dataframe.csv")

        # Guardar DataFrame en JSON
        #save_dataframe_json(df, output_path="feeds_dataframe.json")

        log(f"✅ DataFrame generado con {len(df)} entradas totales")

        if use_mysql:
            log("\n💾 Guardando datos en MySQL...")
            feeds_inserted = 0
            feeds_processed = len(df)

            try:
                with DatabaseConnection() as db:
                    # Crear tabla si no existe
                    create_feeds_table(db)

                    # Obtener conteo previo
                    count_before = get_feed_count(db)
                    log(f"📊 Feeds existentes en BD: {count_before}")

                    # Insertar feeds nuevos
                    stats = insert_feeds_from_dataframe(db, df)
                    feeds_inserted = stats['inserted']

                    # Obtener conteo después
                    count_after = get_feed_count(db)
                    log(f"📊 Total feeds en BD: {count_after}")
                    log(f"✅ MySQL: {stats['inserted']} insertados, {stats['skipped']} ya existían, {stats['errors']} errores")

                    # Registrar ejecución
                    register_execution(db, feeds_processed, feeds_inserted, 'completed')

                # Crear backup después de guardar en MySQL
                create_mysql_backup()

                # Generar metadata desde la base de datos
                log("\n📋 Generando metadata desde la base de datos...")
                with DatabaseConnection() as db:
                    metadata = get_metadata_from_db(db, feeds)
                    if metadata:
                        save_metadata_json(metadata, output_dir="assets")
                    else:
                        log("⚠️ No se pudo generar el metadata")

                # Generar chunks de feeds por sourceType
                log("\n📦 Generando chunks de feeds por sourceType...")
                with DatabaseConnection() as db:
                    success = generate_feed_chunks(db, output_dir="assets", items_per_chunk=ITEMS_PER_CHUNK)
                    if not success:
                        log("⚠️ No se pudieron generar los chunks de feeds")

                # Generar chunks de feeds por sourceType y category
                log("\n📦 Generando chunks de feeds por sourceType...")
                with DatabaseConnection() as db:
                    success = generate_feed_chunks(db, output_dir="assets", items_per_chunk=ITEMS_PER_CHUNK)
                    if not success:
                        log("⚠️ No se pudieron generar los chunks de feeds")
                # Generar chunks de feeds por sourceType
                log("\n📦 Generando chunks de feeds por sourceType...")
                with DatabaseConnection() as db:
                    success = generate_category_chunks(db, output_dir="assets", items_per_chunk=ITEMS_PER_CHUNK)
                    if not success:
                        log("⚠️ No se pudieron generar los chunks por category feeds")

                # Generar chunks de shorts (todos los videos cortos)
                log("\n📦 Generando chunks de shorts (isShortVideo=1)...")
                with DatabaseConnection() as db:
                    success = generate_shorts_chunks(db, output_dir="assets", items_per_chunk=ITEMS_PER_CHUNK)
                    if not success:
                        log("⚠️ No se pudieron generar los chunks de shorts")

                # Limpiar archivos JSON
                log("\n🧹 Limpiando archivos JSON...")
                cleanup_json_files()

            except Exception as e:
                log(f"❌ Error al guardar en MySQL: {e}")
                # Intentar registrar ejecución con error
                try:
                    with DatabaseConnection() as db:
                        register_execution(db, feeds_processed, 0, 'error')
                except:
                    pass
        else:
            log("\n⚠️ MySQL deshabilitado (USE_MYSQL=false o no configurado)")
    else:
        log("⚠️ No se pudo generar el DataFrame (sin datos)")

if __name__ == "__main__":
    # Verificar si se pasó el parámetro --force
    force = '--force' in sys.argv
    main(force=force)
