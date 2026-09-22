import re

def extract_abstract(text: str) -> str:
    """
    Extrae y devuelve el texto que aparece después de la palabra 'Abstract'
    (ignorando mayúsculas, saltos de línea o signos de puntuación).
    """
    # Busca la palabra 'Abstract' (sin importar mayúsculas/minúsculas)
    match = re.search(r'(?i)\babstract\b[:\-]?\s*(.*)', text, re.DOTALL)
    if match:
        # Captura todo lo que viene después
        result = match.group(1).strip()
        return result
    return text

def get_link_pdf(link: str, category: str) -> str:
    """
    Devuelve el link directo al PDF para categorías de arXiv (arXiv_LG, arXiv_AI, ...),
    reemplazando '/abs/' por '/pdf/' en la URL. Para el resto de categorías devuelve ''.
    """
    if category and category.lower().startswith('arxiv'):
        return (link or '').replace('/abs/', '/pdf/')
    return ''