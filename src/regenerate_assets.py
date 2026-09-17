#!/usr/bin/env python3
"""
Script para regenerar todos los archivos JSON y metadata desde la base de datos.

Este script es útil después de hacer cambios manuales en la base de datos
(como post-procesar imágenes) para actualizar todos los archivos de salida.

Uso:
    python src/regenerate_assets.py
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Agregar el directorio src al path
sys.path.insert(0, str(Path(__file__).parent))

from config.loader import load_feeds_config, get_feeds_months_back, get_max_chunks_per_category
from database.connection import DatabaseConnection
from database.operations import get_metadata_from_db, get_feed_count
from feeds.chunk_generator import generate_feed_chunks
from feeds.metadata_generator import save_metadata_json
from feeds.category_chunk_generator import generate_category_chunks
from feeds.shorts_chunk_generator import generate_shorts_chunks
from feeds.featured_pappers_generator import generate_featured_pappers
from utils.cleanup import cleanup_json_files
from utils.logger import log

# Cargar variables de entorno
load_dotenv()

# Configuración
ITEMS_PER_CHUNK = 30  # Número máximo de feeds por chunk

def regenerate_all_assets():
    """
    Regenera todos los archivos JSON y metadata desde la base de datos.

    Returns:
        bool: True si se completó exitosamente, False en caso de error
    """
    log("="*60)
    log("🔄 REGENERADOR DE ASSETS")
    log("="*60)
    log("Este script regenera todos los archivos JSON y metadata")
    log("desde la base de datos sin modificar los feeds.")
    log("="*60 + "\n")

    try:
        # Cargar configuración de feeds
        config_path = Path(__file__).parent.parent / "feeds_config.yaml"
        feeds_config = load_feeds_config(config_path)

        # Cargar configuraciones adicionales
        months_back = get_feeds_months_back(config_path)
        max_chunks = get_max_chunks_per_category(config_path)

        log(f"⚙️  Configuración: últimos {months_back} meses")
        if max_chunks:
            log(f"⚙️  Límite de chunks por categoría: {max_chunks}")

        with DatabaseConnection() as db:
            # Verificar cuántos feeds hay en la base de datos
            feed_count = get_feed_count(db)
            log(f"📊 Feeds en base de datos: {feed_count}")

            if feed_count == 0:
                log("⚠️  No hay feeds en la base de datos. Nada que regenerar.")
                return False

            # 0. Generar pappers destacados
            log("\n⭐ Generando pappers destacados...")
            generate_featured_pappers(db, output_dir="assets", config_path=str(config_path))

            # 1. Generar metadata desde la base de datos
            log("\n📋 Generando metadata desde la base de datos...")
            metadata = get_metadata_from_db(db, feeds_config, months_back=months_back, max_chunks=max_chunks)
            if metadata:
                save_metadata_json(metadata, output_dir="assets")
                log("✅ Metadata generado exitosamente")
            else:
                log("⚠️  No se pudo generar el metadata")
                return False

            # 2. Generar chunks de feeds por sourceType (notice, forum, pappers)
            log("\n📦 Generando chunks de feeds por sourceType...")
            success = generate_feed_chunks(db, output_dir="assets", items_per_chunk=ITEMS_PER_CHUNK, months_back=months_back, max_chunks=max_chunks)
            if success:
                log("✅ Chunks por sourceType generados exitosamente")
            else:
                log("⚠️  No se pudieron generar los chunks por sourceType")
                return False

            # 3. Generar chunks de feeds por sourceType y category
            log("\n📦 Generando chunks de feeds por category...")
            success = generate_category_chunks(db, output_dir="assets", items_per_chunk=ITEMS_PER_CHUNK, months_back=months_back, max_chunks=max_chunks)
            if success:
                log("✅ Chunks por category generados exitosamente")
            else:
                log("⚠️  No se pudieron generar los chunks por category")
                return False

            # 4. Generar chunks de shorts (todos los videos cortos)
            log("\n📦 Generando chunks de shorts (isShortVideo=1)...")
            success = generate_shorts_chunks(db, output_dir="assets", items_per_chunk=ITEMS_PER_CHUNK, months_back=months_back, max_chunks=max_chunks)
            if success:
                log("✅ Chunks de shorts generados exitosamente")
            else:
                log("⚠️  No se pudieron generar los chunks de shorts")
                # No retornar False aquí porque puede que no haya shorts aún

            # 5. Limpiar archivos JSON huérfanos
            log("\n🧹 Limpiando archivos JSON obsoletos...")
            cleanup_json_files()
            log("✅ Archivos JSON limpiados")

        # Resumen final
        log(f"\n{'='*60}")
        log("✅ REGENERACIÓN COMPLETADA")
        log(f"{'='*60}")
        log(f"📊 Total de feeds procesados: {feed_count}")
        log(f"📁 Archivos actualizados en ./assets/")
        log(f"{'='*60}\n")

        return True

    except Exception as e:
        log(f"\n❌ Error durante la regeneración: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Punto de entrada principal."""
    success = regenerate_all_assets()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
