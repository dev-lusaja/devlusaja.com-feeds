from bs4 import BeautifulSoup

def extract_first_image(html_content: str) -> str | None:
    """
    Devuelve la URL de la primera imagen encontrada en el HTML.
    Si la URL termina con '/', se elimina.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    img_tag = soup.find("img")
    
    if img_tag and img_tag.has_attr("src"):
        img_url = img_tag["src"].strip()
        # Quitar el slash final si existe
        if img_url.endswith("/"):
            img_url = img_url[:-1]
        return img_url
    
    return None
