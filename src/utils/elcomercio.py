"""
Scraper para obtener noticias de El Comercio PE sobre Inteligencia Artificial.

Este módulo extrae artículos de https://elcomercio.pe/noticias/inteligencia-artificial/
y los convierte en un formato compatible con feedparser.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Any
from utils.logger import log


def scrape_elcomercio_ia(url: str = "https://elcomercio.pe/noticias/inteligencia-artificial/") -> Dict[str, Any]:
    """
    Extrae artículos de El Comercio PE sobre IA y los convierte en formato de feed.

    Args:
        url: URL de la página de noticias de IA de El Comercio

    Returns:
        Diccionario con estructura compatible con feedparser
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        log(f"📡 Obteniendo El Comercio PE desde: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        entries = []

        # Buscar todos los contenedores de artículos
        # El Comercio usa divs con clase "story-item"
        article_containers = soup.find_all('div', class_='story-item')

        log(f"🔍 El Comercio PE: Encontrados {len(article_containers)} artículos")

        for article in article_containers:
            try:
                entry = extract_elcomercio_article(article)
                if entry and entry.get('title') and entry.get('link'):
                    entries.append(entry)
            except Exception as e:
                log(f"⚠️ Error al procesar artículo individual: {e}")
                continue

        log(f"✅ El Comercio PE: Extraídos {len(entries)} artículos válidos")

        # Estructura compatible con feedparser
        return {
            'feed': {
                'title': 'El Comercio PE - Inteligencia Artificial',
                'link': url,
                'description': 'Noticias sobre Inteligencia Artificial de El Comercio Perú',
                'language': 'es'
            },
            'entries': entries,
            'bozo': 0  # Indica que el feed es válido
        }

    except requests.exceptions.RequestException as e:
        log(f"❌ Error al obtener El Comercio PE: {e}")
        return {
            'feed': {},
            'entries': [],
            'bozo': 1,
            'bozo_exception': e
        }
    except Exception as e:
        log(f"❌ Error inesperado en scraper de El Comercio PE: {e}")
        return {
            'feed': {},
            'entries': [],
            'bozo': 1,
            'bozo_exception': e
        }


def extract_elcomercio_article(article_element) -> Dict[str, Any]:
    """
    Extrae datos de un elemento de artículo de El Comercio PE.

    Args:
        article_element: Elemento BeautifulSoup del artículo

    Returns:
        Diccionario con datos del artículo en formato feedparser
    """
    entry = {}

    # Extraer título y link
    # El título está en <a> con clase "story-item__title"
    title_elem = article_element.find('a', class_='story-item__title')
    if title_elem:
        entry['title'] = title_elem.get_text(separator=' ', strip=True)
        href = title_elem.get('href', '')
        # Asegurar que el link sea absoluto
        if href.startswith('/'):
            entry['link'] = f"https://elcomercio.pe{href}"
        elif href.startswith('http'):
            entry['link'] = href
        else:
            entry['link'] = f"https://elcomercio.pe/{href}"

    # Si no tenemos título o link, este artículo no es válido
    if not entry.get('title') or not entry.get('link'):
        return {}

    # Extraer descripción
    # La descripción está en <p> con clase "story-item__subtitle"
    desc_elem = article_element.find('p', class_='story-item__subtitle')
    if desc_elem:
        entry['summary'] = desc_elem.get_text(separator=' ', strip=True)

    # Extraer imagen
    # La imagen está en <img> con clase "story-item__img"
    img_elem = article_element.find('img', class_='story-item__img')
    if img_elem:
        # Intentar obtener data-src primero (es la imagen real), luego src
        img_src = img_elem.get('data-src') or img_elem.get('src', '')
        if img_src:
            # Reemplazar &amp; por & para que la URL funcione correctamente
            img_src = img_src.replace('&amp;', '&')
            # Verificar que no sea la imagen por defecto
            if 'default-md.png' not in img_src:
                entry['media_content'] = [{'url': img_src}]

    # Extraer autor
    # El autor está en <a> con clase "story-item__author"
    author_elem = article_element.find('a', class_='story-item__author')
    if author_elem:
        entry['author'] = author_elem.get_text(strip=True)
    else:
        entry['author'] = 'El Comercio'

    # Extraer fecha
    # La fecha está en spans con clase "story-item__date-time"
    date_spans = article_element.find_all('span', class_='story-item__date-time')
    if len(date_spans) >= 2:
        # El primer span tiene la fecha (24/10/2025), el segundo la hora (11:48)
        date_str = date_spans[0].get_text(strip=True)
        time_str = date_spans[1].get_text(strip=True)

        # Combinar fecha y hora
        entry['published'] = parse_elcomercio_date(date_str, time_str)
    else:
        # Si no se encuentra fecha, usar la fecha actual
        entry['published'] = datetime.utcnow().isoformat() + '+00:00'

    # Generar ID único basado en el link
    if entry.get('link'):
        entry['id'] = entry['link']

    # Extraer categoría/sección
    # La sección está en <a> con clase "story-item__section"
    section_elem = article_element.find('a', class_='story-item__section')
    if section_elem:
        entry['category'] = section_elem.get_text(strip=True)

    return entry


def parse_elcomercio_date(date_str: str, time_str: str) -> str:
    """
    Convierte una fecha de El Comercio (formato: dd/mm/yyyy y hh:mm) a formato ISO.

    Args:
        date_str: Fecha en formato dd/mm/yyyy
        time_str: Hora en formato hh:mm

    Returns:
        Fecha en formato ISO
    """
    try:
        # Formato esperado: "24/10/2025" y "11:48"
        day, month, year = date_str.split('/')
        hour, minute = time_str.split(':')

        # Crear fecha ISO (asumiendo UTC-5 para Perú)
        # Pero lo convertimos a UTC
        return f"{year}-{month}-{day}T{hour}:{minute}:00-05:00"

    except Exception:
        # Si falla, retornar la fecha actual en UTC
        return datetime.utcnow().isoformat() + '+00:00'


def is_elcomercio_feed(category: str = None) -> bool:
    """
    Determina si un feed es de El Comercio PE.

    Args:
        category: Categoría del feed

    Returns:
        True si es un feed de El Comercio PE
    """
    if category == 'ElComercio_PE':
        return True
    return False
