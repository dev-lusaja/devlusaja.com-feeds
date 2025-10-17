import feedparser
from utils.logger import log

def fetch_feed(url: str, category):
    """Obtiene el feed RSS/Atom desde una URL."""
    log(f"📡 Obteniendo feed: {category} ({url})")
    return feedparser.parse(url)
