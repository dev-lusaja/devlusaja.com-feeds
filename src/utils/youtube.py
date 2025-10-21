def is_youtube_short(link: str) -> bool:
    """
    Detecta si un link de YouTube corresponde a un Short.

    Args:
        link: URL del video de YouTube

    Returns:
        True si el link contiene 'shorts', False en caso contrario
    """
    if not link:
        return False

    return '/shorts/' in link.lower()

def get_youtube_thumbnail(entry_id: str, link: str) -> str:
    """
    Extrae el thumbnail de YouTube desde el ID del video o el link.

    Casos manejados:
    1. ID con formato 'yt:video:VIDEO_ID'
    2. Link con formato 'youtube.com/watch?v=VIDEO_ID'
    3. Link con formato 'youtu.be/VIDEO_ID'

    Args:
        entry_id: ID de la entrada (puede contener 'yt:video:VIDEO_ID')
        link: URL del video de YouTube

    Returns:
        URL del thumbnail en alta calidad o cadena vacía si no se puede extraer
    """
    video_id = ''

    # CASO 1: Extraer desde el ID con formato 'yt:video:VIDEO_ID'
    if entry_id and entry_id.startswith('yt:video:'):
        video_id = entry_id.replace('yt:video:', '')

    # CASO 2: Extraer desde el link 'youtube.com/watch?v=VIDEO_ID'
    elif link and 'youtube.com/watch?v=' in link:
        try:
            # Extraer el parámetro 'v' del query string
            video_id = link.split('v=')[1].split('&')[0]
        except (IndexError, AttributeError):
            pass

    # CASO 3: Extraer desde el link 'youtu.be/VIDEO_ID'
    elif link and 'youtu.be/' in link:
        try:
            # El ID está después de youtu.be/
            video_id = link.split('youtu.be/')[1].split('?')[0]
        except (IndexError, AttributeError):
            pass

    # Si se extrajo un video_id válido, construir la URL del thumbnail
    if video_id:
        # YouTube ofrece varios tamaños de thumbnails:
        # - default.jpg (120x90)
        # - mqdefault.jpg (320x180)
        # - hqdefault.jpg (480x360) <- Usamos este
        # - sddefault.jpg (640x480)
        # - maxresdefault.jpg (1280x720)
        return f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg'

    return ''