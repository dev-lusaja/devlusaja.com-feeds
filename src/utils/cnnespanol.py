"""
Scraper para obtener noticias de CNN Español sobre Inteligencia Artificial.

Este módulo extrae artículos de https://cnnespanol.cnn.com/ciencia/inteligencia-artificial
y los convierte en un formato compatible con feedparser.
El scraper procesa múltiples secciones dentro de la misma página.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Any
import re
from utils.logger import log


def scrape_cnnespanol_ia(url: str = "https://cnnespanol.cnn.com/ciencia/inteligencia-artificial") -> Dict[str, Any]:
    """
    Extrae artículos de CNN Español sobre IA y los convierte en formato de feed.
    Procesa múltiples secciones dentro de la misma página.

    Args:
        url: URL de la página de IA de CNN Español

    Returns:
        Diccionario con estructura compatible con feedparser
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        log(f"📡 Obteniendo CNN Español desde: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        entries = []

        # SECCIÓN 1: Buscar artículos con estructura de lista
        # Estos están en <li> con clase "container__item"
        log(f"🔍 CNN Español: Buscando artículos de Sección 1...")
        section1_articles = soup.find_all('li', class_=lambda x: x and 'container__item' in x)
        log(f"🔍 CNN Español Sección 1: Encontrados {len(section1_articles)} artículos")

        for article in section1_articles:
            try:
                entry = extract_cnnespanol_article_section1(article)
                if entry and entry.get('title') and entry.get('link'):
                    entries.append(entry)
            except Exception as e:
                log(f"⚠️ Error al procesar artículo de Sección 1: {e}")
                continue

        # TODO: Agregar más secciones cuando se proporcionen las estructuras HTML
        # section2_articles = soup.find_all(...)
        # for article in section2_articles:
        #     entry = extract_cnnespanol_article_section2(article)
        #     ...

        log(f"✅ CNN Español: Extraídos {len(entries)} artículos válidos en total")

        # Estructura compatible con feedparser
        return {
            'feed': {
                'title': 'CNN Español - Inteligencia Artificial',
                'link': url,
                'description': 'Noticias sobre Inteligencia Artificial de CNN Español',
                'language': 'es'
            },
            'entries': entries,
            'bozo': 0  # Indica que el feed es válido
        }

    except requests.exceptions.RequestException as e:
        log(f"❌ Error al obtener CNN Español: {e}")
        return {
            'feed': {},
            'entries': [],
            'bozo': 1,
            'bozo_exception': e
        }
    except Exception as e:
        log(f"❌ Error inesperado en scraper de CNN Español: {e}")
        return {
            'feed': {},
            'entries': [],
            'bozo': 1,
            'bozo_exception': e
        }


def extract_cnnespanol_article_section1(article_element) -> Dict[str, Any]:
    """
    Extrae datos de un elemento de artículo de CNN Español - Sección 1.
    Estructura: <li> con clase "container__item"

    Args:
        article_element: Elemento BeautifulSoup del artículo

    Returns:
        Diccionario con datos del artículo en formato feedparser
    """
    entry = {}

    # Extraer link del atributo data-open-link
    data_link = article_element.get('data-open-link', '')
    if not data_link:
        return {}

    # Completar URL
    entry['link'] = f"https://cnnespanol.cnn.com{data_link}" if data_link.startswith('/') else data_link

    # Extraer título
    title_elem = article_element.find('span', class_='container__headline-text')
    if title_elem:
        entry['title'] = title_elem.get_text(strip=True)
    else:
        return {}

    # Si no tenemos título o link, este artículo no es válido
    if not entry.get('title') or not entry.get('link'):
        return {}

    # Extraer fecha de publicación desde la URL
    pub_date = extract_date_from_url(data_link)
    if pub_date:
        entry['published'] = pub_date
    else:
        # Si no se puede extraer la fecha, usar la fecha actual
        entry['published'] = datetime.utcnow().isoformat() + '+00:00'

    # Extraer imagen del elemento picture
    picture_elem = article_element.find('picture', class_='image__picture')
    if picture_elem:
        # Buscar el primer source con srcset
        source_elem = picture_elem.find('source')
        if source_elem and source_elem.get('srcset'):
            img_url = parse_srcset(source_elem.get('srcset'))
            if img_url:
                entry['media_content'] = [{'url': img_url}]

    # Extraer fecha en texto (si está disponible)
    date_elem = article_element.find('div', class_='container__date')
    if date_elem:
        entry['published_text'] = date_elem.get_text(strip=True)

    # Generar ID único basado en el link
    entry['id'] = entry['link']

    # Autor por defecto
    entry['author'] = 'CNN Español'

    return entry


def extract_date_from_url(url: str) -> str:
    """
    Extrae la fecha de una URL con formato /YYYY/MM/DD/ y la convierte a formato ISO.

    Args:
        url: URL que contiene la fecha (ej: /2025/11/03/entretenimiento/...)

    Returns:
        Fecha en formato ISO (YYYY-MM-DDTHH:MM:SS+00:00) o None si no se encuentra
    """
    try:
        # Buscar patrón /YYYY/MM/DD/ en la URL
        pattern = r'/(\d{4})/(\d{2})/(\d{2})/'
        match = re.search(pattern, url)

        if match:
            year = match.group(1)
            month = match.group(2)
            day = match.group(3)

            # Obtener la hora actual en UTC
            now_utc = datetime.utcnow()
            time_part = now_utc.strftime("%H:%M:%S")

            # Crear fecha ISO
            return f"{year}-{month}-{day}T{time_part}+00:00"
    except Exception as e:
        log(f"⚠️ Error al extraer fecha de URL {url}: {e}")

    return None


def parse_srcset(srcset_value: str) -> str:
    """
    Parsea el valor de un atributo srcset y retorna la primera URL.
    El srcset puede tener múltiples URLs separadas por comas.

    Args:
        srcset_value: Valor del atributo srcset

    Returns:
        Primera URL encontrada o cadena vacía
    """
    try:
        # El srcset puede tener formato: "url1 1x, url2 2x" o simplemente "url"
        # Tomamos la primera URL antes de cualquier espacio o coma
        if srcset_value:
            # Dividir por coma y tomar el primer elemento
            first_part = srcset_value.split(',')[0].strip()
            # Dividir por espacio y tomar la URL (primer elemento)
            url = first_part.split()[0]
            return url
    except Exception as e:
        log(f"⚠️ Error al parsear srcset: {e}")

    return ""


def is_cnnespanol_feed(category: str = None) -> bool:
    """
    Determina si un feed es de CNN Español.

    Args:
        category: Categoría del feed

    Returns:
        True si es un feed de CNN Español
    """
    if category == 'CNN_Espanol':
        return True
    return False
