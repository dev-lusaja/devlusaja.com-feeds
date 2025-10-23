import json
import uuid
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from utils.logger import log
from dateutil import parser as date_parser
from bs4 import BeautifulSoup
from utils.arxiv import extract_abstract
from utils.youtube import get_youtube_thumbnail, is_youtube_short
from utils.tiktok import is_tiktok_video, get_tiktok_thumbnail
from utils.xataka import extract_first_image

def load_all_feeds(feeds_dir: str = "feeds_data") -> List[Dict[str, Any]]:
    """
    Carga todos los archivos JSON de feeds desde el directorio especificado.

    Args:
        feeds_dir: Directorio donde se encuentran los archivos JSON de feeds

    Returns:
        Lista de diccionarios con los datos de los feeds
    """
    feeds_path = Path(feeds_dir)
    all_feeds = []

    if not feeds_path.exists():
        log(f"⚠️ El directorio {feeds_dir} no existe")
        return all_feeds

    json_files = list(feeds_path.glob("*.json"))
    log(f"📂 Encontrados {len(json_files)} archivos JSON")

    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                feed_data = json.load(f)
                all_feeds.append({
                    'file_path': str(json_file),
                    'data': feed_data
                })
        except Exception as e:
            log(f"❌ Error al cargar {json_file}: {e}")

    return all_feeds

def make_deterministic_uuid(fields: dict, namespace: uuid.UUID = uuid.NAMESPACE_DNS) -> str:
    # Normaliza: ordena claves para consistencia
    name = json.dumps(fields, sort_keys=True, separators=(',', ':'))
    return str(uuid.uuid5(namespace, name))

def standardize_pub_date(pub_date_str: str) -> str:
    """
    Estandariza el formato de fecha a ISO 8601 (YYYY-MM-DDTHH:MM:SS+00:00).

    Maneja múltiples formatos de entrada:
    - ISO 8601: "2025-10-17T15:33:24+00:00"
    - RFC 2822: "Fri, 17 Oct 2025 00:00:00 -0400"
    - RFC 2822 GMT: "Thu, 16 Oct 2025 08:20:00 GMT"

    Args:
        pub_date_str: Cadena de fecha en cualquier formato

    Returns:
        Fecha en formato ISO 8601 o cadena vacía si hay error
    """
    if not pub_date_str or pub_date_str.strip() == '':
        return ''

    try:
        # dateutil.parser es muy flexible y maneja múltiples formatos automáticamente
        parsed_date = date_parser.parse(pub_date_str)
        # Retornar en formato ISO 8601 estándar
        return parsed_date.isoformat()
    except (ValueError, TypeError) as e:
        log(f"⚠️ Error al parsear fecha '{pub_date_str}': {e}")
        return pub_date_str  # Retornar la fecha original si falla el parseo

def extract_entry_data(entry: Dict[str, Any], category: str, source_title: str,
                       source_url: str, source_type: str) -> Dict[str, Any]:
    """
    Extrae y transforma los datos de una entrada de feed al formato deseado.

    Args:
        entry: Diccionario con los datos de la entrada del feed
        category: Categoría del feed
        source_title: Título de la fuente
        source_url: URL de la fuente
        source_type: Tipo de fuente (notice, forum, youtube, pappers)

    Returns:
        Diccionario con los datos estructurados
    """


    # Extraer título
    title = entry.get('title', '')

    # Extraer link
    link = entry.get('link', '')
    if not link and 'links' in entry and len(entry['links']) > 0:
        link = entry['links'][0].get('href', '')

    # Extraer el id
    uuid_data = {"id":entry.get('id', ''), "category": category, "feed_title": title, "feed_url": link, "source_type": source_type}
    uuid = make_deterministic_uuid(uuid_data)
    entry_id = uuid

    # Extraer fecha de publicación
    pub_date = ''
    if 'published' in entry:
        pub_date = entry['published']
    elif 'updated' in entry:
        pub_date = entry['updated']

    # Estandarizar formato de fecha a ISO 8601
    pub_date = standardize_pub_date(pub_date)

    # Extraer descripción/summary
    description = ''
    if 'summary' in entry:
        description = entry['summary']
    elif 'description' in entry:
        description = entry['description']

    original_description = description # with html content
    soup = BeautifulSoup(description, "html.parser")
    description = soup.get_text(separator=" ", strip=True) # clean content

    # Extraer autor
    author = entry.get('author', 'Desconocido')
    if not author and 'authors' in entry and len(entry['authors']) > 0:
        author = entry['authors'][0].get('name', 'Desconocido')

    # Extraer contenido
    content = ''
    if 'content' in entry and len(entry['content']) > 0:
        content = entry['content'][0].get('value', '')

    # Extraer imagen
    image = ''

    # Detectar si es un video corto (YouTube Shorts)
    is_short_video = 0

    ####################
    # CASOS ESPECIALES #
    ####################

    # CASO ESPECIAL: ArXiv (Pappers) - Extraer solo el abstract
    if source_type == 'pappers' and category.lower().startswith('arxiv'):
        description = extract_abstract(description)

    # CASO ESPECIAL: YouTube - Construir URL del thumbnail desde el ID del video
    if source_type == 'youtube':
        # Intentar obtener el thumbnail de YouTube
        original_entry_id = entry.get('id', '')
        image = get_youtube_thumbnail(original_entry_id, link)

        # Detectar si es un YouTube Short
        if is_youtube_short(link):
            is_short_video = 1

    # CASO ESPECIAL: TikTok - Todos los videos de TikTok son shorts
    if source_type == 'tiktok':
        # Intentar obtener el thumbnail de TikTok desde el feed
        image = get_tiktok_thumbnail(entry, link)

        # Todos los videos de TikTok son videos cortos por definición
        is_short_video = 1

    # CASO ESPECIAL: Xataka - obtener primera imagen
    if source_type == 'notice' and category.lower() == 'xataka':
        image = extract_first_image(original_description)

    # Si no se pudo obtener el thumbnail de casos especiales, usar métodos estándar
    if not image:
        if 'media_content' in entry and len(entry['media_content']) > 0:
            image = entry['media_content'][0].get('url', '')
        elif 'media_thumbnail' in entry and len(entry['media_thumbnail']) > 0:
            image = entry['media_thumbnail'][0].get('url', '')

    return {
        'id': entry_id,
        'title': title,
        'link': link,
        'pubDate': pub_date,
        'description': description,
        'author': author,
        'sourceTitle': source_title,
        'sourceUrl': source_url,
        'sourceCategory': category,
        'sourceType': source_type,
        'content': content,
        'image': image,
        'isShortVideo': is_short_video,
        'raw_data': json.dumps(entry, ensure_ascii=False)
    }

def get_feed_metadata(file_path: str, feeds_config: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Obtiene los metadatos de un feed basándose en el nombre del archivo y la configuración.

    Args:
        file_path: Ruta del archivo JSON
        feeds_config: Lista de configuraciones de feeds

    Returns:
        Diccionario con los metadatos del feed
    """
    file_name = Path(file_path).stem  # Ej: Reddit_ClaudeAI_feed_2025-10-16

    # Extraer la categoría del nombre del archivo
    # El formato es: {category}_feed_{date}
    parts = file_name.split('_feed_')
    if len(parts) > 0:
        category = parts[0]

        # Buscar en la configuración
        for feed_info in feeds_config:
            if feed_info['category'] == category:
                return {
                    'category': category,
                    'source_title': feed_info['title'],
                    'source_url': feed_info['url'],
                    'source_type': feed_info['sourceType']
                }

def build_dataframe(feeds_dir: str = "feeds_data",
                    feeds_config: List[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    Construye un DataFrame de pandas con todos los datos de los feeds.

    Args:
        feeds_dir: Directorio donde se encuentran los archivos JSON de feeds
        feeds_config: Lista de configuraciones de feeds (opcional)

    Returns:
        DataFrame de pandas con los datos estructurados
    """
    if feeds_config is None:
        feeds_config = []

    all_feeds = load_all_feeds(feeds_dir)

    if not all_feeds:
        log("⚠️ No se encontraron feeds para procesar")
        return pd.DataFrame()

    all_entries = []

    for feed_info in all_feeds:
        file_path = feed_info['file_path']
        feed_data = feed_info['data']

        # Obtener metadatos del feed
        metadata = get_feed_metadata(file_path, feeds_config)

        # Procesar las entradas
        entries = feed_data.get('entries', [])

        for entry in entries:
            entry_data = extract_entry_data(
                entry,
                metadata['category'],
                metadata['source_title'],
                metadata['source_url'],
                metadata['source_type']
            )
            all_entries.append(entry_data)

    df = pd.DataFrame(all_entries)

    log(f"📊 DataFrame creado con {len(df)} entradas")

    return df

def save_dataframe(df: pd.DataFrame, feeds_dir: str = "feeds_data", output_path: str = "feeds_dataframe.csv"):
    """
    Guarda el DataFrame en un archivo CSV.

    Args:
        df: DataFrame de pandas
        output_path: Ruta del archivo de salida
    """
    try:
        feeds_full_path = Path(feeds_dir) / output_path
        df.to_csv(
            feeds_full_path,
            index=False,
            encoding='utf-8',
            quoting=1,  # csv.QUOTE_ALL - encapsula todos los campos entre comillas
            escapechar='\\'  # carácter de escape para comillas dentro del contenido
        )
        log(f"💾 DataFrame guardado en {feeds_full_path}")
    except Exception as e:
        log(f"❌ Error al guardar DataFrame: {e}")

def save_dataframe_json(df: pd.DataFrame, feeds_dir: str = "feeds_data", output_path: str = "feeds_dataframe.json"):
    """
    Guarda el DataFrame en un archivo JSON.

    Args:
        df: DataFrame de pandas
        output_path: Ruta del archivo de salida
    """
    try:
        feeds_full_path = Path(feeds_dir) / output_path
        df.to_json(feeds_full_path, orient='records', indent=2, force_ascii=False)
        log(f"💾 DataFrame guardado en {feeds_full_path}")
    except Exception as e:
        log(f"❌ Error al guardar DataFrame: {e}")
