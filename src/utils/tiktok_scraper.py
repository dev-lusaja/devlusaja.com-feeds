"""
Scraper para obtener videos de perfiles de TikTok.

Usa yt-dlp (listado "flat" del perfil, sin descargar videos) en lugar de
Playwright: TikTok muestra un captcha a Chromium headless y el grid queda vacío.
Devuelve un objeto con formato compatible con feedparser.
"""

from datetime import datetime, timezone
from typing import Dict, Any
from utils.logger import log
import re
import yt_dlp

MAX_VIDEOS = 30


def scrape_tiktok_user(url: str, username: str = None) -> Dict[str, Any]:
    """
    Extrae los videos más recientes de un perfil de TikTok en formato de feed.

    Args:
        url: URL del perfil de TikTok (ej: https://www.tiktok.com/@migue.baena)
        username: Nombre de usuario (opcional, se extrae de la URL si no se proporciona)

    Returns:
        Diccionario con estructura compatible con feedparser
    """
    if not username:
        username = extract_username_from_url(url)

    log(f"📡 Obteniendo TikTok desde: {url}")

    try:
        opts = {'extract_flat': True, 'playlistend': MAX_VIDEOS, 'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        log(f"❌ Error al obtener TikTok @{username}: {e}")
        return {'feed': {}, 'entries': [], 'bozo': 1, 'bozo_exception': e}

    entries = []
    for video in info.get('entries') or []:
        entry = video_to_entry(video, username)
        if entry:
            entries.append(entry)

    if not entries:
        # Un perfil activo sin videos casi siempre significa bloqueo/cambio de TikTok
        msg = f"TikTok @{username}: 0 videos obtenidos (¿bloqueo o cambio de API?)"
        log(f"⚠️ {msg}")
        return {'feed': {}, 'entries': [], 'bozo': 1, 'bozo_exception': Exception(msg)}

    log(f"✅ TikTok @{username}: Extraídos {len(entries)} videos")

    return {
        'feed': {
            'title': f'TikTok - @{username}',
            'link': url,
            'description': f'Videos de TikTok de @{username}',
            'language': 'es'
        },
        'entries': entries,
        'bozo': 0
    }


def video_to_entry(video: Dict[str, Any], username: str) -> Dict[str, Any]:
    """Convierte una entrada flat de yt-dlp en una entrada estilo feedparser."""
    link = video.get('url') or video.get('webpage_url')
    if not link:
        return {}

    description = (video.get('description') or video.get('title') or '').strip()
    title = description[:200] if description else f"Video de @{username}"

    timestamp = video.get('timestamp')
    published = datetime.fromtimestamp(timestamp, timezone.utc) if timestamp else datetime.now(timezone.utc)

    entry = {
        'id': str(video.get('id') or link),
        'link': link,
        'title': title,
        'summary': description,
        'author': f"@{username}",
        'published': published.isoformat(),
    }

    views = video.get('view_count')
    if views is not None:
        entry['summary'] = f"{description}\n\nVistas: {views}"

    thumbnails = video.get('thumbnails') or []
    if thumbnails:
        entry['media_content'] = [{'url': thumbnails[0]['url']}]

    return entry


def extract_username_from_url(url: str) -> str:
    """
    Extrae el nombre de usuario de una URL de TikTok.

    Args:
        url: URL del perfil de TikTok

    Returns:
        Nombre de usuario sin el símbolo @
    """
    match = re.search(r'@([a-zA-Z0-9._]+)', url)
    if match:
        return match.group(1)
    return 'unknown'


def is_tiktok_scraper_feed(url: str = None, category: str = None) -> bool:
    """
    Determina si un feed debe usar el scraper de TikTok.

    Args:
        url: URL del feed
        category: Categoría del feed

    Returns:
        True si debe usar el scraper de TikTok
    """
    if url and 'tiktok.com/@' in url:
        return True

    if category and category.startswith('TikTok_'):
        return True

    return False
