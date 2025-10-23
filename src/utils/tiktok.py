def is_tiktok_video(link: str, source_type: str = None) -> bool:
    """
    Detecta si un link corresponde a un video de TikTok.

    Args:
        link: URL del video
        source_type: Tipo de fuente (opcional, para verificación adicional)

    Returns:
        True si es un video de TikTok, False en caso contrario
    """
    if not link:
        return False

    # Todos los videos de TikTok son videos cortos
    return 'tiktok.com' in link.lower() or (source_type and source_type.lower() == 'tiktok')

def get_tiktok_thumbnail(entry: dict, link: str) -> str:
    """
    Intenta extraer el thumbnail de un video de TikTok desde el feed RSS.

    RSSHub generalmente incluye el thumbnail en media_content o media_thumbnail.
    Esta función es un placeholder para extracciones personalizadas si son necesarias.

    Args:
        entry: Diccionario con los datos de la entrada del feed
        link: URL del video de TikTok

    Returns:
        URL del thumbnail o cadena vacía
    """
    # Intentar obtener desde media_content
    if 'media_content' in entry and len(entry['media_content']) > 0:
        return entry['media_content'][0].get('url', '')

    # Intentar obtener desde media_thumbnail
    elif 'media_thumbnail' in entry and len(entry['media_thumbnail']) > 0:
        return entry['media_thumbnail'][0].get('url', '')

    return ''

def extract_tiktok_user_from_url(url: str) -> str:
    """
    Extrae el nombre de usuario de una URL de TikTok.

    Ejemplos:
    - https://www.tiktok.com/@migue.baena -> migue.baena
    - @migue.baena -> migue.baena

    Args:
        url: URL o handle de TikTok

    Returns:
        Nombre de usuario sin el símbolo @
    """
    if not url:
        return ''

    # Si ya tiene el formato @username
    if url.startswith('@'):
        return url[1:]

    # Si es una URL completa
    if 'tiktok.com/@' in url:
        try:
            # Extraer el usuario después de @
            username = url.split('@')[1].split('/')[0].split('?')[0]
            return username
        except (IndexError, AttributeError):
            pass

    return ''

def build_rsshub_tiktok_url(username: str, rsshub_instance: str = 'https://rsshub.app') -> str:
    """
    Construye la URL de RSSHub para un usuario de TikTok.

    Args:
        username: Nombre de usuario de TikTok (con o sin @)
        rsshub_instance: Instancia de RSSHub a usar (por defecto https://rsshub.app)

    Returns:
        URL completa del feed RSS de RSSHub
    """
    # Limpiar el username
    clean_username = username.lstrip('@')

    # Construir URL de RSSHub
    return f"{rsshub_instance}/tiktok/user/@{clean_username}"
