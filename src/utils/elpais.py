"""
Scraper para obtener noticias de El País sobre Inteligencia Artificial.

Este módulo extrae artículos de https://elpais.com/noticias/inteligencia-artificial/
y los convierte en un formato compatible con feedparser.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Any
from utils.logger import log


def scrape_elpais_ia(url: str = "https://elpais.com/noticias/inteligencia-artificial/") -> Dict[str, Any]:
    """
    Extrae artículos de El País sobre IA y los convierte en formato de feed.

    Args:
        url: URL de la página de noticias de IA de El País

    Returns:
        Diccionario con estructura compatible con feedparser
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        log(f"📡 Obteniendo El País desde: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        entries = []

        # Buscar todos los contenedores de artículos
        # El País usa <article> con clases "c c-d c--m"
        article_containers = soup.find_all('article', class_=lambda x: x and 'c' in x.split() and 'c-d' in x.split())

        log(f"🔍 El País: Encontrados {len(article_containers)} artículos")

        for article in article_containers:
            try:
                entry = extract_elpais_article(article)
                if entry and entry.get('title') and entry.get('link'):
                    entries.append(entry)
            except Exception as e:
                log(f"⚠️ Error al procesar artículo individual: {e}")
                continue

        log(f"✅ El País: Extraídos {len(entries)} artículos válidos")

        # Estructura compatible con feedparser
        return {
            'feed': {
                'title': 'El País - Inteligencia Artificial',
                'link': url,
                'description': 'Noticias sobre Inteligencia Artificial de El País',
                'language': 'es'
            },
            'entries': entries,
            'bozo': 0  # Indica que el feed es válido
        }

    except requests.exceptions.RequestException as e:
        log(f"❌ Error al obtener El País: {e}")
        return {
            'feed': {},
            'entries': [],
            'bozo': 1,
            'bozo_exception': e
        }
    except Exception as e:
        log(f"❌ Error inesperado en scraper de El País: {e}")
        return {
            'feed': {},
            'entries': [],
            'bozo': 1,
            'bozo_exception': e
        }


def extract_elpais_article(article_element) -> Dict[str, Any]:
    """
    Extrae datos de un elemento de artículo de El País.

    Args:
        article_element: Elemento BeautifulSoup del artículo

    Returns:
        Diccionario con datos del artículo en formato feedparser
    """
    entry = {}

    # Extraer título y link
    # El título está en <h2 class="c_t"> dentro de <header class="c_h">
    header_elem = article_element.find('header', class_='c_h')
    if header_elem:
        title_elem = header_elem.find('h2', class_='c_t')
        if title_elem:
            link_elem = title_elem.find('a')
            if link_elem:
                href = link_elem.get('href', '')
                entry['link'] = href if href.startswith('http') else f"https://elpais.com{href}"
                entry['title'] = link_elem.get_text(separator=' ', strip=True)

    # Si no tenemos título o link, este artículo no es válido
    if not entry.get('title') or not entry.get('link'):
        return {}

    # Extraer descripción
    # La descripción está en un <p class="c_d">
    desc_elem = article_element.find('p', class_='c_d')
    if desc_elem:
        entry['summary'] = desc_elem.get_text(separator=' ', strip=True)

    # Extraer imagen
    # La imagen está en un <img> dentro de <div class="c_m">
    img_container = article_element.find('div', class_=lambda x: x and 'c_m' in x.split())
    if img_container:
        img_elem = img_container.find('img')
        if img_elem:
            # Intentar obtener src o data-src
            img_src = img_elem.get('src') or img_elem.get('data-src', '')
            if img_src and img_src.startswith('http'):
                entry['media_content'] = [{'url': img_src}]

    # Extraer autor
    # El autor está en <a class="c_a_a"> dentro de <div class="c_a">
    author_container = article_element.find('div', class_='c_a')
    if author_container:
        author_elem = author_container.find('a', class_='c_a_a')
        if author_elem:
            entry['author'] = author_elem.get_text(strip=True)
        else:
            entry['author'] = 'El País'
    else:
        entry['author'] = 'El País'

    # Extraer fecha
    # La fecha está en <time datetime="...">
    time_elem = article_element.find('time')
    if time_elem and time_elem.get('datetime'):
        # El País usa formato ISO 8601
        entry['published'] = time_elem.get('datetime')
    else:
        # Si no hay fecha, usar la fecha de ejecución
        entry['published'] = datetime.utcnow().isoformat() + '+00:00'

    # Generar ID único basado en el link
    if entry.get('link'):
        entry['id'] = entry['link']

    # Extraer categoría/sección
    # La categoría está en <a class="c_k"> dentro de <header class="c_h">
    if header_elem:
        category_elem = header_elem.find('a', class_='c_k')
        if category_elem:
            entry['category'] = category_elem.get_text(strip=True)

    return entry


def is_elpais_feed(category: str = None) -> bool:
    """
    Determina si un feed es de El País.

    Args:
        category: Categoría del feed

    Returns:
        True si es un feed de El País
    """
    if category == 'El_Pais':
        return True
    return False
