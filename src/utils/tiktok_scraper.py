"""
Scraper para obtener videos de perfiles de TikTok.

Este módulo extrae videos de perfiles públicos de TikTok
y los convierte en un formato compatible con feedparser.
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, BrowserContext
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Any, Optional
from utils.logger import log
from database.connection import DatabaseConnection
from database.operations import feed_exists
import re
import time
import os
import json


def load_tiktok_cookies(context: BrowserContext):
    """
    Carga cookies de TikTok desde variables de entorno si existen.
    """
    cookie_str = os.getenv('TIKTOK_COOKIE', '')
    session_id = os.getenv('TIKTOK_SESSION_ID', '')
    cookies = []
    if session_id:
        cookies.append({'name': 'sessionid', 'value': session_id, 'domain': '.tiktok.com', 'path': '/'})
    if cookie_str:
        for item in cookie_str.split(';'):
            if '=' in item:
                parts = item.strip().split('=', 1)
                cookies.append({'name': parts[0], 'value': parts[1], 'domain': '.tiktok.com', 'path': '/'})
    if cookies:
        try:
            context.add_cookies(cookies)
            log(f"🍪 Cargadas {len(cookies)} cookies de TikTok")
        except Exception as e:
            log(f"⚠️ Error al agregar cookies de TikTok: {e}")


def extract_date_from_video_page(context: BrowserContext, video_url: str) -> Optional[str]:
    """
    Visita la página de un video de TikTok y extrae la fecha de publicación.

    Busca el elemento:
    <span data-e2e="browser-nickname">
        ...
        <span>8-31</span>  <!-- Formato: M-D o MM-DD -->
    </span>

    Args:
        context: Contexto del navegador Playwright
        video_url: URL del video de TikTok

    Returns:
        Fecha en formato ISO (YYYY-MM-DDTHH:MM:SS+00:00) o None si no se encuentra
    """
    try:
        # Crear nueva página en el mismo contexto
        page = context.new_page()

        # Navegar a la URL del video
        page.goto(video_url, wait_until='domcontentloaded', timeout=15000)

        # Esperar a que cargue el elemento con la fecha
        try:
            page.wait_for_selector('[data-e2e="browser-nickname"]', timeout=5000)
        except PlaywrightTimeoutError:
            log(f"   ⚠️ Timeout esperando fecha en {video_url[:60]}...")

        # Pequeña espera adicional
        time.sleep(0.5)

        # Obtener HTML
        html_content = page.content()
        page.close()

        # Parsear con BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Buscar el span con la fecha
        nickname_span = soup.find('span', {'data-e2e': 'browser-nickname'})

        if not nickname_span:
            return None

        # Obtener todos los spans dentro
        spans = nickname_span.find_all('span')

        # El último span debería contener la fecha en formato M-D o MM-DD
        date_text = None
        for span in reversed(spans):
            text = span.get_text(strip=True)
            # Verificar si parece una fecha (formato: números-números)
            if re.match(r'^\d{1,2}-\d{1,2}$', text):
                date_text = text
                break

        if not date_text:
            return None

        # Convertir "8-31" a fecha completa
        parts = date_text.split('-')
        if len(parts) != 2:
            return None

        month = int(parts[0])
        day = int(parts[1])

        # Determinar el año (asumir año actual, pero si la fecha es futura, usar año anterior)
        now = datetime.utcnow()
        current_year = now.year

        try:
            # Intentar con año actual
            video_date = datetime(current_year, month, day)

            # Si la fecha es futura, el video es del año anterior
            if video_date > now:
                video_date = datetime(current_year - 1, month, day)

            # Convertir a ISO format
            iso_date = video_date.isoformat() + '+00:00'
            return iso_date

        except ValueError:
            # Fecha inválida
            return None

    except Exception as e:
        log(f"   ⚠️ Error al extraer fecha de {video_url[:60]}: {e}")
        return None


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

        # Conectar a BD para verificar videos existentes
        db = None
        try:
            db = DatabaseConnection()
            db.__enter__()
        except Exception as e:
            log(f"⚠️ No se pudo conectar a BD, se procesarán todos los videos: {e}")
            db = None

        # Usar Playwright para renderizar la página
        with sync_playwright() as p:
            # Lanzar navegador en modo headless
            browser = p.chromium.launch(headless=True)

            # Crear contexto con user agent realista
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='es-ES'
            )
            load_tiktok_cookies(context)

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

        log(f"🔍 TikTok @{username}: Encontrados {len(video_containers)} contenedores de videos")

        for video_div in video_containers:
            try:
                entry = extract_tiktok_video(video_div, username, context, db)
                if entry and entry.get('title') and entry.get('link'):
                    entries.append(entry)
            except Exception as e:
                log(f"⚠️ Error al procesar video individual: {e}")
                continue

        # Fallback: Extraer de script de rehidratación JSON si no hubo contenedores DOM
        if not entries:
            rehydration_script = soup.find('script', id='__UNIVERSAL_DATA_FOR_REHYDRATION__') or soup.find('script', id='SIGI_STATE')
            if rehydration_script and rehydration_script.string:
                try:
                    data = json.loads(rehydration_script.string)
                    # Buscar recurisvamente items
                    def extract_items_from_dict(obj):
                        if isinstance(obj, dict):
                            if 'id' in obj and 'desc' in obj and 'createTime' in obj:
                                item_id = str(obj['id'])
                                desc = str(obj.get('desc', ''))
                                video_url = f"https://www.tiktok.com/@{username}/video/{item_id}"
                                cover = ''
                                if isinstance(obj.get('video'), dict):
                                    cover = obj['video'].get('cover') or obj['video'].get('originCover') or ''
                                create_time = obj.get('createTime')
                                pub_date = datetime.utcfromtimestamp(int(create_time)).isoformat() + '+00:00' if create_time else datetime.utcnow().isoformat() + '+00:00'
                                entries.append({
                                    'id': item_id,
                                    'title': desc[:200] if len(desc) > 200 else (desc or f"Video de @{username}"),
                                    'summary': desc,
                                    'link': video_url,
                                    'author': f"@{username}",
                                    'published': pub_date,
                                    'media_content': [{'url': cover}] if cover else []
                                })
                            else:
                                for v in obj.values():
                                    extract_items_from_dict(v)
                        elif isinstance(obj, list):
                            for elem in obj:
                                extract_items_from_dict(elem)

                    extract_items_from_dict(data)
                    log(f"🔍 TikTok @{username}: Extraídos {len(entries)} videos desde script JSON")
                except Exception as e:
                    log(f"⚠️ Error al extraer JSON de TikTok: {e}")

        log(f"✅ TikTok @{username}: Extraídos {len(entries)} videos válidos")

        # Cerrar conexión a BD si se abrió
        if db:
            try:
                db.__exit__(None, None, None)
            except Exception:
                pass

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


def extract_tiktok_video(video_element, username: str, context: BrowserContext, db: Optional[DatabaseConnection] = None) -> Dict[str, Any]:
    """
    Extrae datos de un elemento de video de TikTok.

    Args:
        video_element: Elemento BeautifulSoup del video
        username: Nombre de usuario del perfil
        context: Contexto del navegador Playwright
        db: Conexión a la base de datos (opcional, para verificar existencia)

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

    # Fecha: Solo visitar la página del video si NO existe en la BD
    if entry.get('link'):
        # Verificar si el video ya existe en la BD
        video_exists = False
        if db:
            try:
                video_exists = feed_exists(db, entry['link'])
            except Exception as e:
                log(f"   ⚠️ Error al verificar existencia: {e}")
                video_exists = False

        if video_exists:
            # Video ya existe, usar fecha actual (no se guardará de todas formas)
            entry['published'] = datetime.utcnow().isoformat() + '+00:00'
        else:
            # Video nuevo, visitar página para extraer fecha real
            video_date = extract_date_from_video_page(context, entry['link'])
            if video_date:
                entry['published'] = video_date
            else:
                # Fallback: usar fecha actual si no se pudo extraer
                entry['published'] = datetime.utcnow().isoformat() + '+00:00'
    else:
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
