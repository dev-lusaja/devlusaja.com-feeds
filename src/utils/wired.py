"""
Scraper para obtener noticias de Wired ES sobre Inteligencia Artificial.

Este módulo extrae artículos de https://es.wired.com/tag/inteligencia-artificial
y los convierte en un formato compatible con feedparser.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Any
from utils.logger import log


def scrape_wired_es_ai(url: str = "https://es.wired.com/tag/inteligencia-artificial") -> Dict[str, Any]:
    """
    Extrae artículos de Wired ES sobre IA y los convierte en formato de feed.

    Args:
        url: URL de la página de tag de IA de Wired ES

    Returns:
        Diccionario con estructura compatible con feedparser
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        log(f"📡 Obteniendo Wired ES desde: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        entries = []

        # Buscar todos los contenedores de artículos
        # Wired ES usa divs con clase que contiene "SummaryItemWrapper"
        article_containers = soup.find_all('div', class_=lambda x: x and 'SummaryItemWrapper' in x)

        log(f"🔍 Wired ES: Encontrados {len(article_containers)} artículos")

        for article in article_containers:
            try:
                entry = extract_wired_article(article)
                if entry and entry.get('title') and entry.get('link'):
                    entries.append(entry)
            except Exception as e:
                log(f"⚠️ Error al procesar artículo individual: {e}")
                continue

        log(f"✅ Wired ES: Extraídos {len(entries)} artículos válidos")

        # Estructura compatible con feedparser
        return {
            'feed': {
                'title': 'Wired ES - Inteligencia Artificial',
                'link': url,
                'description': 'Noticias sobre Inteligencia Artificial de Wired España',
                'language': 'es'
            },
            'entries': entries,
            'bozo': 0  # Indica que el feed es válido
        }

    except requests.exceptions.RequestException as e:
        log(f"❌ Error al obtener Wired ES: {e}")
        return {
            'feed': {},
            'entries': [],
            'bozo': 1,
            'bozo_exception': e
        }
    except Exception as e:
        log(f"❌ Error inesperado en scraper de Wired ES: {e}")
        return {
            'feed': {},
            'entries': [],
            'bozo': 1,
            'bozo_exception': e
        }


def extract_wired_article(article_element) -> Dict[str, Any]:
    """
    Extrae datos de un elemento de artículo de Wired ES.

    Args:
        article_element: Elemento BeautifulSoup del artículo

    Returns:
        Diccionario con datos del artículo en formato feedparser
    """
    entry = {}

    # Extraer título y link
    # El título está en <h3> con clase "SummaryItemHedBase" dentro de <a> con clase "SummaryItemHedLink"
    
    link_elem = article_element.find('a', class_=lambda x: x and 'SummaryItemHedLink' in x)
    if link_elem:
        href = link_elem.get('href', '')
        entry['link'] = href if href.startswith('http') else f"https://es.wired.com{href}"

        # Extraer título del h3 dentro del link
        title_elem = link_elem.find('h3', class_=lambda x: x and 'SummaryItemHedBase' in x)
        if title_elem:
            # Obtener texto y limpiar tags HTML internos como <em>
            entry['title'] = title_elem.get_text(separator=' ', strip=True)

    # Si no tenemos título o link, este artículo no es válido
    if not entry.get('title') or not entry.get('link'):
        return {}

    # Extraer descripción
    # La descripción está en un div con clase "SummaryItemDek"
    desc_elem = article_element.find('div', class_=lambda x: x and 'SummaryItemDek' in x)
    if desc_elem:
        entry['summary'] = desc_elem.get_text(separator=' ', strip=True)

    # Extraer imagen
    # La imagen está en un <img> dentro de <picture> con clase "ResponsiveImagePicture"
    picture_elem = article_element.find('picture', class_=lambda x: x and 'ResponsiveImagePicture' in x)
    if picture_elem:
        img_elem = picture_elem.find('img')
        if img_elem:
            # Intentar obtener src o data-src
            img_src = img_elem.get('src') or img_elem.get('data-src', '')
            if img_src:
                entry['media_content'] = [{'url': img_src}]

    # Extraer autor
    # El autor está en un span con clase "BylineName"
    author_elem = article_element.find('span', class_=lambda x: x and 'BylineName' in x)
    if author_elem:
        # Remover el "Por " del principio si existe
        author_text = author_elem.get_text(strip=True)
        entry['author'] = author_text.replace('Por ', '')
    else:
        entry['author'] = 'Wired ES'

    # Extraer fecha
    # TODO: traer la fecha real, se pondra por ahora la fecha de ejecución
    entry['published'] = datetime.utcnow().isoformat() + '+00:00'

    # Generar ID único basado en el link
    if entry.get('link'):
        entry['id'] = entry['link']

    # Extraer categoría/rubric
    rubric_elem = article_element.find('span', class_=lambda x: x and 'RubricName' in x)
    if rubric_elem:
        entry['category'] = rubric_elem.get_text(strip=True)

    return entry


def parse_spanish_date(date_str: str) -> str:
    """
    Convierte una fecha en español (ej: "23 de octubre de 2025") a formato ISO.
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

        # Formato esperado: "23 de octubre de 2025"
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


def is_wired_feed(category: str = None) -> bool:
    """
    Determina si un feed es de Wired ES.

    Args:
        category: Categoría del feed

    Returns:
        True si es un feed de Wired ES
    """
    if category == 'Wired_ES':
        return True
    return False
