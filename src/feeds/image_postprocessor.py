import requests
import time
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from database.connection import DatabaseConnection
from database.operations import update_feed_image
from utils.logger import log

def extract_first_image_from_url(
    url: str,
    timeout: int = 10,
    source_type: Optional[str] = None,
    category: Optional[str] = None
) -> Optional[str]:
    """
    Extrae la primera imagen de una página web.

    Busca imágenes en el siguiente orden de prioridad:
    1. Meta tags Open Graph (og:image)
    2. Meta tags Twitter Card (twitter:image)
    3. Primera imagen <img> en el contenido con src válido

    Para categoría "Towards" con sourceType "notice", busca específicamente
    la imagen con clase "attachment-post-thumbnail".

    Args:
        url: URL de la página web
        timeout: Timeout en segundos para la petición HTTP
        source_type: Tipo de fuente (para lógica especial)
        category: Categoría de la fuente (para lógica especial)

    Returns:
        URL de la imagen encontrada o None si no se encuentra
    """
    if not url:
        return None

    try:
        # Realizar petición HTTP con headers completos para simular navegador real
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

        # Usar session para mantener cookies (importante para Medium/Towards)
        session = requests.Session()
        response = session.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        response.raise_for_status()

        # Forzar encoding UTF-8 para evitar problemas de decodificación
        response.encoding = response.apparent_encoding or 'utf-8'

        # Parsear HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Caso especial: Towards con sourceType notice
        if source_type == 'notice' and category == 'Towards':
            towards_img = soup.find('img', class_='attachment-post-thumbnail')
            if towards_img and towards_img.get('src'):
                img_src = towards_img['src']
                # Si es URL relativa, convertir a absoluta
                if img_src.startswith('//'):
                    img_src = 'https:' + img_src
                elif img_src.startswith('/'):
                    from urllib.parse import urljoin
                    img_src = urljoin(url, img_src)
                return img_src

        # Caso especial: Anthropic - extraer imagen (Next.js Image Optimization)
        if source_type == 'notice' and category and 'anthropic' in category.lower():
            from utils.anthropic import extract_hero_image
            # Habilitar debug para ver qué está buscando
            anthropic_image = extract_hero_image(response.text, debug=True)
            if anthropic_image:
                log(f"   ✅ Imagen de Anthropic extraída: {anthropic_image[:80]}...")
                return anthropic_image
            else:
                log(f"   ⚠️ No se encontró imagen en Anthropic (ver detalles arriba)")

        # 1. Buscar Open Graph image
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image['content']

        # 2. Buscar Twitter Card image
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            return twitter_image['content']

        # 3. Buscar primera imagen en el contenido
        # Buscar en el article o main primero (más probable que sea contenido relevante)
        content_areas = soup.find_all(['article', 'main', 'div'], class_=lambda x: x and any(
            keyword in x.lower() for keyword in ['content', 'article', 'post', 'entry']
        ))

        # Si encontramos áreas de contenido, buscar ahí primero
        for area in content_areas:
            img = area.find('img', src=True)
            if img and img.get('src'):
                img_src = img['src']
                # Ignorar imágenes pequeñas, placeholders, o de tracking
                if any(skip in img_src.lower() for skip in ['pixel', 'tracker', 'blank', 'spacer', '1x1']):
                    continue
                # Si es URL relativa, convertir a absoluta
                if img_src.startswith('//'):
                    img_src = 'https:' + img_src
                elif img_src.startswith('/'):
                    from urllib.parse import urljoin
                    img_src = urljoin(url, img_src)
                return img_src

        # Si no se encontró en áreas de contenido, buscar en todo el documento
        img = soup.find('img', src=True)
        if img and img.get('src'):
            img_src = img['src']
            if img_src.startswith('//'):
                img_src = 'https:' + img_src
            elif img_src.startswith('/'):
                from urllib.parse import urljoin
                img_src = urljoin(url, img_src)
            return img_src

        return None

    except requests.exceptions.RequestException as e:
        log(f"⚠️ Error al obtener imagen de {url}: {e}")
        return None
    except Exception as e:
        log(f"⚠️ Error inesperado al procesar {url}: {e}")
        return None

def get_feeds_without_images(
    db: DatabaseConnection,
    source_type: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene feeds que no tienen imagen.

    Args:
        db: Conexión a la base de datos
        source_type: Filtrar por tipo de fuente (opcional)
        category: Filtrar por categoría (opcional)
        limit: Límite de resultados (opcional)

    Returns:
        Lista de feeds sin imagen
    """
    cursor = db.get_cursor()
    if not cursor:
        return []

    try:
        # Construir query dinámica (TechCrunch_AI/Towards/MIT_AI bloquean el scraping: excluidas para no gastar el LIMIT)
        query = """
        SELECT id, title, link, sourceType, sourceCategory
        FROM feeds
        WHERE (image IS NULL OR image = '') AND sourceType not in ('pappers') AND sourceCategory not in ('GoogleNews', 'OpenAI', 'TechCrunch_AI', 'Towards', 'MIT_AI')
        """
        params = []

        if source_type:
            query += f" AND sourceType = '{source_type}'"

        if category:
            query += f" AND sourceCategory = '{category}'"

        query += " ORDER BY pubDate DESC"

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        results = cursor.fetchall()
        return results

    except Exception as e:
        log(f"❌ Error al obtener feeds sin imágenes: {e}")
        return []
    finally:
        cursor.close()

def process_feeds_images(
    db: DatabaseConnection,
    source_type: Optional[str] = 'notice',
    category: Optional[str] = 'TechCrunch_AI',
    limit: Optional[int] = None,
    delay: float = 1.0
) -> Dict[str, int]:
    """
    Procesa feeds sin imagen y extrae la primera imagen de su URL.

    Args:
        db: Conexión a la base de datos
        source_type: Tipo de fuente a procesar (por defecto 'notice')
        category: Categoría a procesar (por defecto 'TechCrunch_AI')
        limit: Límite de feeds a procesar (None = todos)
        delay: Delay en segundos entre peticiones para no saturar servidores

    Returns:
        Diccionario con estadísticas: {'processed': int, 'updated': int, 'failed': int}
    """
    stats = {'processed': 0, 'updated': 0, 'failed': 0}

    # Obtener feeds sin imagen
    log(f"📊 Buscando feeds sin imagen (sourceType={source_type}, category={category})...")
    feeds = get_feeds_without_images(db, source_type, category, limit)

    if not feeds:
        log("✅ No hay feeds sin imagen para procesar")
        return stats

    log(f"📦 Encontrados {len(feeds)} feeds sin imagen. Procesando...")

    for feed in feeds:
        feed_id = feed['id']
        feed_link = feed['link']
        feed_title = feed['title']
        feed_source_type = feed['sourceType']
        feed_category = feed['sourceCategory']

        stats['processed'] += 1

        log(f"\n🔍 [{stats['processed']}/{len(feeds)}] Procesando: {feed_title[:60]}...")
        log(f"   URL: {feed_link}")
        log(f"   Source: {feed_source_type} / {feed_category}")

        # Extraer imagen
        image_url = extract_first_image_from_url(
            feed_link,
            source_type=feed_source_type,
            category=feed_category
        )

        if image_url:
            # Actualizar en la base de datos
            if update_feed_image(db, feed_id, image_url):
                stats['updated'] += 1
                log(f"   ✅ Imagen encontrada y actualizada: {image_url[:80]}...")
            else:
                stats['failed'] += 1
                log(f"   ❌ Error al actualizar imagen en la BD")
        else:
            stats['failed'] += 1
            log(f"   ⚠️ No se encontró imagen en la página")

        # Delay para no saturar servidores
        if stats['processed'] < len(feeds):
            time.sleep(delay)

    # Resumen
    log(f"\n{'='*60}")
    log(f"✅ Procesamiento completado:")
    log(f"   - Total procesados: {stats['processed']}")
    log(f"   - Actualizados con imagen: {stats['updated']}")
    log(f"   - Fallidos: {stats['failed']}")
    log(f"{'='*60}")

    return stats
