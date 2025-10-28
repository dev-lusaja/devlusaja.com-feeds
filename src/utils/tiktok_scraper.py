"""
Scraper para obtener videos de perfiles de TikTok.

Este módulo extrae videos de perfiles públicos de TikTok
y los convierte en un formato compatible con feedparser.
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Any
from utils.logger import log
import re
import time


def scrape_tiktok_user(url: str, username: str = None) -> Dict[str, Any]:
    """
    Extrae videos de un perfil de TikTok y los convierte en formato de feed.

    Args:
        url: URL del perfil de TikTok (ej: https://www.tiktok.com/@migue.baena)
        username: Nombre de usuario (opcional, se extrae de la URL si no se proporciona)

    Returns:
        Diccionario con estructura compatible con feedparser
    """
    try:
        # Extraer username de la URL si no se proporciona
        if not username:
            username = extract_username_from_url(url)

        log(f"📡 Obteniendo TikTok desde: {url}")

        entries = []

        # Usar Playwright para renderizar la página
        with sync_playwright() as p:
            # Lanzar navegador en modo headless
            browser = p.chromium.launch(headless=True)

            # Crear contexto con user agent realista
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='es-ES'
            )

            page = context.new_page()

            # Navegar a la URL
            log(f"🌐 Cargando página de TikTok...")
            page.goto(url, wait_until='networkidle', timeout=30000)

            # Esperar a que los videos se carguen
            # Esperar por el selector de videos
            try:
                page.wait_for_selector('div[data-e2e="user-post-item"]', timeout=10000)
                log(f"✅ Videos cargados en la página")
            except PlaywrightTimeoutError:
                log(f"⚠️ Timeout esperando videos, intentando extraer de todas formas...")

            # Dar un poco más de tiempo para que termine de cargar
            time.sleep(2)

            # Obtener el HTML renderizado
            html_content = page.content()

            # Cerrar navegador
            browser.close()

        # Parsear con BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Buscar todos los contenedores de videos
        # Según tu ejemplo: <div data-e2e="user-post-item">
        video_containers = soup.find_all('div', attrs={'data-e2e': 'user-post-item'})

        # Si no encuentra con data-e2e, intentar con otras formas
        if not video_containers:
            # Buscar por id que contiene "column-item-video-container"
            video_containers = soup.find_all('div', id=re.compile(r'column-item-video-container-\d+'))

        log(f"🔍 TikTok @{username}: Encontrados {len(video_containers)} videos")

        for video_div in video_containers:
            try:
                entry = extract_tiktok_video(video_div, username)
                if entry and entry.get('title') and entry.get('link'):
                    entries.append(entry)
            except Exception as e:
                log(f"⚠️ Error al procesar video individual: {e}")
                continue

        log(f"✅ TikTok @{username}: Extraídos {len(entries)} videos válidos")

        # Estructura compatible con feedparser
        return {
            'feed': {
                'title': f'TikTok - @{username}',
                'link': url,
                'description': f'Videos de TikTok de @{username}',
                'language': 'es'
            },
            'entries': entries,
            'bozo': 0  # Indica que el feed es válido
        }

    except PlaywrightTimeoutError as e:
        log(f"❌ Timeout al cargar TikTok @{username}: {e}")
        return {
            'feed': {},
            'entries': [],
            'bozo': 1,
            'bozo_exception': e
        }
    except Exception as e:
        log(f"❌ Error inesperado en scraper de TikTok: {e}")
        return {
            'feed': {},
            'entries': [],
            'bozo': 1,
            'bozo_exception': e
        }


def extract_tiktok_video(video_element, username: str) -> Dict[str, Any]:
    """
    Extrae datos de un elemento de video de TikTok.

    Args:
        video_element: Elemento BeautifulSoup del video
        username: Nombre de usuario del perfil

    Returns:
        Diccionario con datos del video en formato feedparser
    """
    entry = {}

    # Extraer link del video
    # <a href="https://www.tiktok.com/@migue.baena/video/7565855288671161622">
    link_elem = video_element.find('a', href=True)
    if link_elem:
        href = link_elem.get('href', '')
        if href.startswith('http'):
            entry['link'] = href
        elif href.startswith('/'):
            entry['link'] = f"https://www.tiktok.com{href}"
        else:
            return {}

        # Extraer video ID del link
        video_id_match = re.search(r'/video/(\d+)', entry['link'])
        if video_id_match:
            entry['id'] = video_id_match.group(1)
        else:
            entry['id'] = entry['link']

    # Si no tenemos link, este video no es válido
    if not entry.get('link'):
        return {}

    # Extraer thumbnail e información del video desde el <img>
    img_elem = video_element.find('img', alt=True)
    if img_elem:
        # El alt contiene la descripción completa del video
        alt_text = img_elem.get('alt', '').strip()

        # Extraer título/descripción
        # El formato del alt es: "descripción creado por Username con la música ..."
        if alt_text:
            # Limpiar el texto y extraer la parte principal
            description = alt_text.split(' creado por ')[0].strip()

            # Si la descripción es muy corta, usar el alt completo
            if len(description) < 10:
                description = alt_text

            entry['title'] = description[:200] if len(description) > 200 else description
            entry['summary'] = alt_text

        # Extraer thumbnail
        # Intentar src, srcset o data-src
        img_src = img_elem.get('src') or img_elem.get('data-src', '')

        # Si hay srcset, obtener la primera URL
        if not img_src:
            srcset = img_elem.get('srcset', '')
            if srcset:
                # El srcset tiene formato: "url 1x, url 2x"
                img_src = srcset.split()[0]

        if img_src:
            entry['media_content'] = [{'url': img_src}]

    # Si no tenemos título, usar uno por defecto
    if not entry.get('title'):
        entry['title'] = f"Video de @{username}"

    # Extraer views
    # <strong data-e2e="video-views">14.9K</strong>
    views_elem = video_element.find('strong', attrs={'data-e2e': 'video-views'})
    if views_elem:
        views_text = views_elem.get_text(strip=True)
        entry['views'] = views_text

        # Agregar views a la descripción si existe
        if entry.get('summary'):
            entry['summary'] = f"{entry['summary']}\n\nVistas: {views_text}"

    # Autor
    entry['author'] = f"@{username}"

    # Fecha (usar fecha actual ya que TikTok no siempre muestra la fecha en el perfil)
    entry['published'] = datetime.utcnow().isoformat() + '+00:00'

    return entry


def extract_username_from_url(url: str) -> str:
    """
    Extrae el nombre de usuario de una URL de TikTok.

    Args:
        url: URL del perfil de TikTok

    Returns:
        Nombre de usuario sin el símbolo @
    """
    # Patrones: https://www.tiktok.com/@username o @username
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
    # Si la URL es de tiktok.com (no de rsshub), usar scraper
    if url and 'tiktok.com/@' in url:
        return True

    # Si la categoría empieza con TikTok_, usar scraper
    if category and category.startswith('TikTok_'):
        return True

    return False
