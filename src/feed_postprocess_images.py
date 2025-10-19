#!/usr/bin/env python3
"""
Script para post-procesar feeds sin imagen.

Este script busca feeds en la base de datos que no tienen imagen
y extrae la primera imagen de su URL usando web scraping.

Uso:
    python feed_postprocess_images.py                                    # Procesa TechCrunch_AI (notice)
    python feed_postprocess_images.py --category Xataka                  # Procesa categoría específica
    python feed_postprocess_images.py --all                              # Procesa todos los feeds notice sin imagen
    python feed_postprocess_images.py --limit 10                         # Procesa solo 10 feeds
    python feed_postprocess_images.py --source-type pappers --category arxiv_AI  # Procesa otro tipo de fuente
"""

import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Agregar el directorio src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database.connection import DatabaseConnection
from feeds.image_postprocessor import process_feeds_images
from utils.logger import log

# Cargar variables de entorno
load_dotenv()

def main():
    parser = argparse.ArgumentParser(
        description='Post-procesa feeds sin imagen extrayendo imágenes de sus URLs'
    )
    parser.add_argument(
        '--source-type',
        type=str,
        default='notice',
        help='Tipo de fuente a procesar (por defecto: notice)'
    )
    parser.add_argument(
        '--category',
        type=str,
        default='TechCrunch_AI',
        help='Categoría a procesar (por defecto: TechCrunch_AI)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Procesar todas las categorías del source-type especificado'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Límite de feeds a procesar (por defecto: todos)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay en segundos entre peticiones (por defecto: 1.0)'
    )

    args = parser.parse_args()

    # Procesar argumentos
    source_type = args.source_type
    category = None if args.all else args.category
    limit = args.limit
    delay = args.delay

    log("="*60)
    log("🖼️  POST-PROCESADOR DE IMÁGENES")
    log("="*60)
    log(f"📋 Configuración:")
    log(f"   - Source Type: {source_type}")
    log(f"   - Category: {category if category else 'TODAS'}")
    log(f"   - Limit: {limit if limit else 'Sin límite'}")
    log(f"   - Delay: {delay}s")
    log("="*60 + "\n")

    try:
        with DatabaseConnection() as db:
            stats = process_feeds_images(
                db,
                source_type=source_type,
                category=category,
                limit=limit,
                delay=delay
            )

            # Mostrar resumen final
            log(f"\n{'='*60}")
            log("📊 RESUMEN FINAL")
            log(f"{'='*60}")
            log(f"✅ Feeds procesados: {stats['processed']}")
            log(f"✅ Feeds actualizados con imagen: {stats['updated']}")
            log(f"⚠️  Feeds sin imagen o con error: {stats['failed']}")
            log(f"{'='*60}\n")

    except Exception as e:
        log(f"\n❌ Error durante el procesamiento: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
