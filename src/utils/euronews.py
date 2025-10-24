"""
Scraper para obtener noticias de Euronews ES sobre Inteligencia Artificial.

Este módulo extrae artículos de https://es.euronews.com/tag/inteligencia-artificial
y los convierte en un formato compatible con feedparser.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Any
from utils.logger import log


def scrape_euronews_es_ai(url: str = "https://es.euronews.com/tag/inteligencia-artificial") -> Dict[str, Any]:
    """
    Extrae artículos de Euronews ES sobre IA y los convierte en formato de feed.

    Args:
        url: URL de la página de tag de IA de Euronews ES

    Returns:
        Diccionario con estructura compatible con feedparser
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        log(f"📡 Obteniendo Euronews ES desde: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        entries = []

        # Buscar todos los contenedores de artículos
        # Euronews ES usa <article> con clase "the-media-object"
        article_containers = soup.find_all('article', class_=lambda x: x and 'the-media-object' in x)

        log(f"🔍 Euronews ES: Encontrados {len(article_containers)} artículos")

        for article in article_containers:
            try:
                entry = extract_euronews_article(article)
                if entry and entry.get('title') and entry.get('link'):
                    entries.append(entry)
            except Exception as e:
                log(f"⚠️ Error al procesar artículo individual: {e}")
                continue

        log(f"✅ Euronews ES: Extraídos {len(entries)} artículos válidos")

        # Estructura compatible con feedparser
        return {
            'feed': {
                'title': 'Euronews ES - Inteligencia Artificial',
                'link': url,
                'description': 'Noticias sobre Inteligencia Artificial de Euronews España',
                'language': 'es'
            },
            'entries': entries,
            'bozo': 0  # Indica que el feed es válido
        }

    except requests.exceptions.RequestException as e:
        log(f"❌ Error al obtener Euronews ES: {e}")
        return {
            'feed': {},
            'entries': [],
            'bozo': 1,
            'bozo_exception': e
        }
    except Exception as e:
        log(f"❌ Error inesperado en scraper de Euronews ES: {e}")
        return {
            'feed': {},
            'entries': [],
            'bozo': 1,
            'bozo_exception': e
        }


def extract_euronews_article(article_element) -> Dict[str, Any]:
    """
    Extrae datos de un elemento de artículo de Euronews ES.

    Args:
        article_element: Elemento BeautifulSoup del artículo

    Returns:
        Diccionario con datos del artículo en formato feedparser
    """
    entry = {}

    # Extraer título y link
    # El título está en <h3 class="the-media-object__title"> dentro de <a class="the-media-object__link">
    link_elem = article_element.find('a', class_=lambda x: x and 'the-media-object__link' in x)
    if link_elem:
        href = link_elem.get('href', '')
        # Si el href no tiene el dominio completo, añadirlo
        entry['link'] = href if href.startswith('http') else f"https://es.euronews.com{href}"

        # Extraer título del h3 dentro del link
        title_elem = link_elem.find('h3', class_=lambda x: x and 'the-media-object__title' in x)
        if title_elem:
            entry['title'] = title_elem.get_text(separator=' ', strip=True)

    # Si no tenemos título o link, este artículo no es válido
    if not entry.get('title') or not entry.get('link'):
        return {}

    # Extraer descripción
    # La descripción está en un div con clase "the-media-object__description"
    desc_elem = article_element.find('div', class_=lambda x: x and 'the-media-object__description' in x)
    if desc_elem:
        entry['summary'] = desc_elem.get_text(separator=' ', strip=True)

    # Extraer imagen
    # La imagen está en <img class="the-media-object__image">
    img_elem = article_element.find('img', class_=lambda x: x and 'the-media-object__image' in x)
    if img_elem:
        # Intentar obtener src o srcset
        img_src = img_elem.get('src')
        if not img_src:
            # Si no hay src, intentar obtener la primera URL del srcset
            srcset = img_elem.get('srcset', '')
            if srcset:
                # srcset tiene formato "url 320w, url 480w"
                first_url = srcset.split(',')[0].strip().split(' ')[0]
                img_src = first_url

        if img_src and img_src.startswith('http'):
            entry['media_content'] = [{'url': img_src}]

    # Extraer categoría
    # La categoría está en <a class="the-media-object__metas">
    category_elem = article_element.find('a', class_=lambda x: x and 'the-media-object__metas' in x)
    if category_elem:
        entry['category'] = category_elem.get_text(strip=True)

    # Autor por defecto
    entry['author'] = 'Euronews ES'

    # Extraer fecha
    # La fecha está en <div class="the-media-object__date"> con <time datetime="...">
    date_elem = article_element.find('time')
    if date_elem:
        datetime_str = date_elem.get('datetime')
        if datetime_str:
            try:
                # Convertir el formato datetime a ISO si es necesario
                entry['published'] = parse_euronews_date(datetime_str)
            except Exception:
                entry['published'] = datetime.utcnow().isoformat() + '+00:00'
    else:
        # Si no hay fecha, usar la fecha actual
        entry['published'] = datetime.utcnow().isoformat() + '+00:00'

    # Generar ID único basado en el link
    if entry.get('link'):
        entry['id'] = entry['link']

    return entry


def parse_euronews_date(datetime_str: str) -> str:
    """
    Convierte una fecha de Euronews a formato ISO.

    Args:
        datetime_str: Fecha en formato de Euronews (ej: "2025-10-22 08:26:19 +02:00")

    Returns:
        Fecha en formato ISO
    """
    try:
        # El formato es "2025-10-22 08:26:19 +02:00"
        # Necesitamos convertirlo a ISO 8601: "2025-10-22T08:26:19+02:00"
        datetime_str = datetime_str.strip()

        # Separar la parte de fecha/hora del timezone
        parts = datetime_str.rsplit(' ', 1)
        if len(parts) == 2:
            datetime_part = parts[0]
            timezone_part = parts[1]

            # Reemplazar espacio entre fecha y hora por T
            datetime_part = datetime_part.replace(' ', 'T', 1)

            # Combinar todo en formato ISO
            return f"{datetime_part}{timezone_part}"

        # Si no tiene el formato esperado, intentar parsear directamente
        dt = datetime.fromisoformat(datetime_str.replace(' ', 'T', 1))
        return dt.isoformat()

    except Exception:
        # Si falla, retornar fecha actual en UTC
        return datetime.utcnow().isoformat() + '+00:00'


def is_euronews_feed(category: str = None) -> bool:
    """
    Determina si un feed es de Euronews ES.

    Args:
        category: Categoría del feed

    Returns:
        True si es un feed de Euronews ES
    """
    if category == 'Euronews':
        return True
    return False
