import feedparser
from utils.logger import log
from utils.wired import scrape_wired_es_ai, is_wired_feed

def fetch_feed(url: str, category):
    """
    Obtiene el feed RSS/Atom desde una URL o usa scrapers personalizados.

    Args:
        url: URL del feed RSS o página web
        category: Categoría del feed

    Returns:
        Objeto con estructura de feedparser
    """
    log(f"📡 Obteniendo feed: {category} ({url})")

    # Detectar si es Wired ES y usar scraper personalizado
    if is_wired_feed(category):
        log(f"🔍 Usando scraper personalizado para Wired ES")
        return scrape_wired_es_ai(url)

    # Para otros feeds, usar feedparser estándar
    return feedparser.parse(url)
