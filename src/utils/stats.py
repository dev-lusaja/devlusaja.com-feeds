from typing import Dict, List
from datetime import datetime


class ExecutionStats:
    """Clase para acumular estadísticas de ejecución del feed fetcher."""

    def __init__(self):
        self.start_time = datetime.now()
        self.end_time = None

        # Estadísticas de descarga
        self.total_feeds_config = 0
        self.feeds_downloaded = 0
        self.feeds_cached = 0

        # Estadísticas de DataFrame
        self.total_entries = 0

        # Estadísticas de Base de Datos
        self.feeds_before = 0
        self.feeds_after = 0
        self.feeds_inserted = 0
        self.feeds_skipped = 0
        self.feeds_errors = 0

        # Estadísticas de chunks
        self.chunks_by_source_type: Dict[str, int] = {}
        self.feeds_by_source_type: Dict[str, int] = {}
        self.chunks_by_category: Dict[str, Dict[str, int]] = {}
        self.feeds_by_category: Dict[str, Dict[str, int]] = {}
        self.shorts_chunks = 0
        self.shorts_total = 0

        # Estadísticas de archivos
        self.total_chunk_files = 0
        self.category_chunk_files = 0
        self.json_files_deleted = 0

        # Estado de backup
        self.backup_created = False
        self.backup_path = None

    def finish(self):
        """Marca el final de la ejecución."""
        self.end_time = datetime.now()

    def get_duration(self) -> str:
        """Retorna la duración de la ejecución en formato legible."""
        if self.end_time:
            duration = self.end_time - self.start_time
            seconds = duration.total_seconds()
            if seconds < 60:
                return f"{seconds:.1f}s"
            else:
                minutes = int(seconds // 60)
                secs = int(seconds % 60)
                return f"{minutes}m {secs}s"
        return "En ejecución..."

    def add_chunk_by_source_type(self, source_type: str, chunks: int, total_feeds: int):
        """Registra chunks generados por tipo de fuente."""
        self.chunks_by_source_type[source_type] = chunks
        self.feeds_by_source_type[source_type] = total_feeds

    def add_chunk_by_category(self, source_type: str, category: str, chunks: int, total_feeds: int):
        """Registra chunks generados por categoría."""
        if source_type not in self.chunks_by_category:
            self.chunks_by_category[source_type] = {}
            self.feeds_by_category[source_type] = {}

        self.chunks_by_category[source_type][category] = chunks
        self.feeds_by_category[source_type][category] = total_feeds

    def print_summary(self):
        """Imprime un resumen completo de la ejecución."""
        self.finish()

        print("\n" + "=" * 80)
        print("RESUMEN DE EJECUCIÓN".center(80))
        print("=" * 80)

        # Tiempo de ejecución
        print(f"\n⏱️  DURACIÓN: {self.get_duration()}")

        # Descarga de feeds
        print("\n📡 DESCARGA DE FEEDS")
        print("-" * 80)
        print(f"  Total configurados:  {self.total_feeds_config}")
        print(f"  Descargados:         {self.feeds_downloaded}")
        print(f"  En caché:            {self.feeds_cached}")
        print(f"  DataFrame generado:  {self.total_entries} entradas")

        # Base de datos
        if self.feeds_inserted > 0 or self.feeds_skipped > 0:
            print("\n💾 BASE DE DATOS")
            print("-" * 80)
            print(f"  Feeds antes:         {self.feeds_before}")
            print(f"  Nuevos insertados:   {self.feeds_inserted}")
            print(f"  Ya existían:         {self.feeds_skipped}")
            if self.feeds_errors > 0:
                print(f"  Errores:             {self.feeds_errors}")
            print(f"  Total después:       {self.feeds_after}")

            if self.backup_created:
                print(f"  Backup creado:       ✅ {self.backup_path if self.backup_path else 'Sí'}")

        # Chunks por tipo de fuente
        if self.chunks_by_source_type:
            print("\n📦 CHUNKS POR TIPO DE FUENTE")
            print("-" * 80)
            for source_type in sorted(self.chunks_by_source_type.keys()):
                chunks = self.chunks_by_source_type[source_type]
                feeds = self.feeds_by_source_type.get(source_type, 0)
                print(f"  {source_type:20} {chunks:3} chunks  ({feeds:4} feeds)")
            print(f"\n  Total archivos generados: {self.total_chunk_files}")

        # Chunks por categoría
        if self.chunks_by_category:
            print("\n📋 CHUNKS POR CATEGORÍA")
            print("-" * 80)
            for source_type in sorted(self.chunks_by_category.keys()):
                print(f"\n  {source_type.upper()}:")
                categories = self.chunks_by_category[source_type]
                for category in sorted(categories.keys()):
                    chunks = categories[category]
                    feeds = self.feeds_by_category[source_type].get(category, 0)
                    print(f"    {category:30} {chunks:3} chunks  ({feeds:4} feeds)")
            print(f"\n  Total archivos de categoría generados: {self.category_chunk_files}")

        # Shorts
        if self.shorts_chunks > 0:
            print("\n🎬 SHORTS (Videos cortos)")
            print("-" * 80)
            print(f"  Total chunks:        {self.shorts_chunks}")
            print(f"  Total shorts:        {self.shorts_total}")

        # Limpieza
        if self.json_files_deleted > 0:
            print("\n🧹 LIMPIEZA")
            print("-" * 80)
            print(f"  Archivos JSON eliminados: {self.json_files_deleted}")

        print("\n" + "=" * 80)
        print("✅ PROCESO COMPLETADO".center(80))
        print("=" * 80 + "\n")
