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
    reemplazando '/abs/' por '/pdf/' en la URL y quitando un '.pdf' final
    (https://arxiv.org/pdf/2609.24847). Links no-arXiv que ya son PDF (p.ej. papers
    destacados) se devuelven tal cual. Para el resto devuelve ''.
    """
    link = link or ''
    if 'arxiv.org/' in link or (category and category.lower().startswith('arxiv')):
        link = link.replace('/abs/', '/pdf/')
        return link[:-4] if link.endswith('.pdf') else link
    if link.lower().endswith('.pdf'):
        return link
    return ''