"""
Scraper para obtener noticias de La Nación Argentina sobre Inteligencia Artificial.

Este módulo extrae artículos de https://www.lanacion.com.ar/tema/inteligencia-artificial-tid58563/
y los convierte en un formato compatible con feedparser.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Any
from utils.logger import log


def scrape_lanacion_ar_ai(url: str = "https://www.lanacion.com.ar/tema/inteligencia-artificial-tid58563/") -> Dict[str, Any]:
    """
    Extrae artículos de La Nación Argentina sobre IA y los convierte en formato de feed.

    Args:
        url: URL de la página de tag de IA de La Nación Argentina

    Returns:
        Diccionario con estructura compatible con feedparser
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        log(f"📡 Obteniendo La Nación AR desde: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        entries = []

        # Buscar todos los contenedores de artículos
        # La Nación usa <article> con clase "mod-article"
        article_containers = soup.find_all('article', class_='mod-article')

        log(f"🔍 La Nación AR: Encontrados {len(article_containers)} artículos")

        for article in article_containers:
            try:
                entry = extract_lanacion_article(article)
                if entry and entry.get('title') and entry.get('link'):
                    entries.append(entry)
            except Exception as e:
                log(f"⚠️ Error al procesar artículo individual: {e}")
                continue

        log(f"✅ La Nación AR: Extraídos {len(entries)} artículos válidos")

        # Estructura compatible con feedparser
        return {
            'feed': {
                'title': 'La Nación Argentina - Inteligencia Artificial',
                'link': url,
                'description': 'Noticias sobre Inteligencia Artificial de La Nación Argentina',
                'language': 'es'
            },
            'entries': entries,
            'bozo': 0  # Indica que el feed es válido
        }

    except requests.exceptions.RequestException as e:
        log(f"❌ Error al obtener La Nación AR: {e}")
        return {
            'feed': {},
            'entries': [],
            'bozo': 1,
            'bozo_exception': e
        }
    except Exception as e:
        log(f"❌ Error inesperado en scraper de La Nación AR: {e}")
        return {
            'feed': {},
            'entries': [],
            'bozo': 1,
            'bozo_exception': e
        }


def extract_lanacion_article(article_element) -> Dict[str, Any]:
    """
    Extrae datos de un elemento de artículo de La Nación Argentina.

    Args:
        article_element: Elemento BeautifulSoup del artículo

    Returns:
        Diccionario con datos del artículo en formato feedparser
    """
    entry = {}

    # Extraer título y link
    # El título y link están en <a> dentro de <h2 class="com-title --font-primary --l --font-medium">
    title_section = article_element.find('h2', class_=lambda x: x and 'com-title' in x and '--l' in x)
    if title_section:
        link_elem = title_section.find('a', class_='com-link')
        if link_elem:
            href = link_elem.get('href', '')
            entry['link'] = href if href.startswith('http') else f"https://www.lanacion.com.ar{href}"
            entry['title'] = link_elem.get_text(strip=True)

    # Si no tenemos título o link, este artículo no es válido
    if not entry.get('title') or not entry.get('link'):
        return {}

    # Extraer imagen
    # La imagen está en <img> dentro de <picture>
    picture_elem = article_element.find('picture')
    if picture_elem:
        img_elem = picture_elem.find('img')
        if img_elem:
            # Intentar obtener src
            img_src = img_elem.get('src', '')
            if img_src and img_src.startswith('http'):
                entry['media_content'] = [{'url': img_src}]

    # Extraer categoría/tag
    # La categoría está en <a> dentro de <h3 class="com-title --font-primary --fourxs --font-medium --tags">
    tag_section = article_element.find('h3', class_=lambda x: x and 'com-title' in x and '--tags' in x)
    if tag_section:
        tag_link = tag_section.find('a', class_='com-link')
        if tag_link:
            entry['category'] = tag_link.get_text(strip=True)

    # Extraer fecha
    # La fecha está en <time class="com-date --fourxs" datetime="24 de octubre de 2025">
    time_elem = article_element.find('time', class_='com-date')
    if time_elem:
        date_str = time_elem.get_text(strip=True)
        entry['published'] = parse_spanish_date(date_str)
    else:
        # Si no hay fecha, usar la fecha actual
        entry['published'] = datetime.utcnow().isoformat() + '+00:00'

    # Autor por defecto
    entry['author'] = 'La Nación Argentina'

    # Generar ID único basado en el link
    if entry.get('link'):
        entry['id'] = entry['link']

    return entry


def parse_spanish_date(date_str: str) -> str:
    """
    Convierte una fecha en español (ej: "24 de octubre de 2025") a formato ISO.
    Usa la hora actual del momento de ejecución para completar la fecha.

    Args:
        date_str: Fecha en formato español

    Returns:
        Fecha en formato ISO o la fecha original si falla la conversión
    """
    try:
        # Mapeo de meses en español
        months_es = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }

        # Formato esperado: "24 de octubre de 2025"
        parts = date_str.lower().split(' de ')
        if len(parts) == 3:
            day = parts[0].strip()
            month = months_es.get(parts[1].strip(), '01')
            year = parts[2].strip()

            # Asegurar que el día tenga 2 dígitos
            day = day.zfill(2)

            # Obtener la hora actual en UTC del momento de ejecución
            now_utc = datetime.utcnow()
            time_part = now_utc.strftime("%H:%M:%S")

            # Crear fecha ISO con la hora de ejecución del script en UTC
            return f"{year}-{month}-{day}T{time_part}+00:00"

    except Exception:
        pass

    # Si falla, retornar la fecha original
    return date_str


def is_lanacion_feed(category: str = None) -> bool:
    """
    Determina si un feed es de La Nación Argentina.

    Args:
        category: Categoría del feed

    Returns:
        True si es un feed de La Nación Argentina
    """
    if category == 'LaNacion_AR':
        return True
    return False
