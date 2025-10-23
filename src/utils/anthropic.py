from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote


def decode_nextjs_image_url(img_src: str) -> str:
    """
    Decodifica una URL de imagen optimizada por Next.js.

    Anthropic usa Next.js Image Optimization con formato:
    /_next/image?url=https%3A%2F%2Fwww-cdn.anthropic.com%2F...&w=...&q=...

    Args:
        img_src: URL de la imagen (puede ser Next.js optimized o directa)

    Returns:
        URL decodificada del CDN o la URL original si no es Next.js
    """
    if not img_src:
        return ''

    # Si es una imagen optimizada por Next.js
    if '/_next/image?url=' in img_src:
        try:
            parsed = urlparse(img_src)
            query_params = parse_qs(parsed.query)
            if 'url' in query_params:
                # Decodificar la URL real del CDN
                cdn_url = unquote(query_params['url'][0])
                return cdn_url
        except:
            pass

    return img_src


def extract_hero_image(html_content: str, debug: bool = False) -> str:
    """
    Extrae la imagen principal de un post de Anthropic desde el HTML.

    Anthropic usa varios patrones:
    1. Hero SVG: <div class="PostDetail_post-hero__*">
    2. Contenido: <div class="Body_media-column__*">
    3. Imágenes inline con Next.js Image Optimization

    Args:
        html_content: Contenido HTML del post
        debug: Si es True, imprime información de debugging

    Returns:
        URL de la imagen (decodificada si es Next.js) o cadena vacía
    """
    if not html_content:
        if debug:
            print("⚠️ HTML content is empty")
        return ''

    try:
        # Usar html.parser (built-in de Python)
        soup = BeautifulSoup(html_content, 'html.parser')

        if debug:
            print(f"📄 HTML length: {len(html_content)} chars")
            print(f"🔍 Buscando imágenes en Anthropic...")

        # Método 1: Buscar imagen hero (SVG)
        hero_div = soup.find('div', class_=lambda x: x and 'PostDetail_post-hero' in x)
        if hero_div:
            if debug:
                print("✓ Encontrado PostDetail_post-hero")
            img = hero_div.find('img')
            if img and img.get('src'):
                if debug:
                    print(f"✓ Imagen en hero: {img['src'][:80]}...")
                return decode_nextjs_image_url(img['src'])

        # Método 2: Buscar en Body_media-column (imágenes del contenido)
        media_column = soup.find('div', class_=lambda x: x and 'Body_media-column' in x)
        if media_column:
            if debug:
                print("✓ Encontrado Body_media-column")
            img = media_column.find('img')
            if img and img.get('src'):
                if debug:
                    print(f"✓ Imagen en media-column: {img['src'][:80]}...")
                return decode_nextjs_image_url(img['src'])

        # Método 3: Buscar figura con caption inline
        inline_img = soup.find('figure', class_=lambda x: x and 'ImageWithCaption' in x)
        if inline_img:
            if debug:
                print("✓ Encontrado ImageWithCaption")
            img = inline_img.find('img')
            if img and img.get('src'):
                if debug:
                    print(f"✓ Imagen inline: {img['src'][:80]}...")
                return decode_nextjs_image_url(img['src'])

        # Método 4: Buscar la primera imagen de anthropic.com (fallback)
        all_imgs = soup.find_all('img', src=True)
        if debug:
            print(f"🔍 Total de imágenes encontradas: {len(all_imgs)}")

        for img in all_imgs:
            src = img.get('src', '')
            if 'anthropic.com' in src or 'cdn.anthropic.com' in src or src.startswith('/_next/'):
                if debug:
                    print(f"✓ Imagen de Anthropic encontrada: {src[:80]}...")
                return decode_nextjs_image_url(src)

        if debug:
            print("⚠️ No se encontró ninguna imagen de Anthropic")
            # Mostrar las primeras 5 imágenes encontradas
            for i, img in enumerate(all_imgs[:5]):
                print(f"   Img {i+1}: {img.get('src', 'NO SRC')[:80]}")

    except Exception as e:
        if debug:
            print(f"❌ Error al parsear HTML: {e}")
        pass

    return ''


def is_anthropic_feed(source_type: str, category: str = None) -> bool:
    """
    Determina si un feed es de Anthropic.

    Args:
        source_type: Tipo de fuente
        category: Categoría (opcional)

    Returns:
        True si es un feed de Anthropic
    """
    if source_type and source_type.lower() == 'notice':
        if category and 'anthropic' in category.lower():
            return True
    return False
