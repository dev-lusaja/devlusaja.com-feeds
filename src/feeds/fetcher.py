import feedparser
from utils.logger import log
from utils.wired import scrape_wired_es_ai, is_wired_feed
from utils.elpais import scrape_elpais_ia, is_elpais_feed
from utils.euronews import scrape_euronews_es_ai, is_euronews_feed
from utils.elcomercio import scrape_elcomercio_ia, is_elcomercio_feed
from utils.lanacion import scrape_lanacion_ar_ai, is_lanacion_feed
from utils.cnnespanol import scrape_cnnespanol_ia, is_cnnespanol_feed
from utils.tiktok_scraper import scrape_tiktok_user, is_tiktok_scraper_feed
from utils.featured_papers import get_featured_papers, is_featured_papers_feed

def fetch_feed(url: str, category):
    """
    Obtiene el feed RSS/Atom desde una URL o usa scrapers personalizados.

    Args:
        url: URL del feed RSS o página web
        category: Categoría del feed

    Returns:
        Objeto con estructura de feedparser
    """
    # Detectar si es Wired ES y usar scraper personalizado
    if is_wired_feed(category):
        return scrape_wired_es_ai(url)

    # Detectar si es El País y usar scraper personalizado
    if is_elpais_feed(category):
        return scrape_elpais_ia(url)

    # Detectar si es Euronews ES y usar scraper personalizado
    if is_euronews_feed(category):
        return scrape_euronews_es_ai(url)

    # Detectar si es El Comercio PE y usar scraper personalizado
    if is_elcomercio_feed(category):
        return scrape_elcomercio_ia(url)

    # Detectar si es La Nación AR y usar scraper personalizado
    if is_lanacion_feed(category):
        return scrape_lanacion_ar_ai(url)

    # Detectar si es CNN Español y usar scraper personalizado
    if is_cnnespanol_feed(category):
        return scrape_cnnespanol_ia(url)

    # Detectar si es TikTok y usar scraper personalizado
    if is_tiktok_scraper_feed(url, category):
        return scrape_tiktok_user(url)

    # Detectar si es la lista estática de papers destacados
    if is_featured_papers_feed(category):
        return get_featured_papers(url)

    # Para otros feeds, usar feedparser estándar
    return feedparser.parse(url)
