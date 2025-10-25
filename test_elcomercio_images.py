"""
Script de prueba para analizar la estructura de imágenes en El Comercio PE
"""

import requests
from bs4 import BeautifulSoup

url = "https://elcomercio.pe/noticias/inteligencia-artificial/"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

print(f"📡 Obteniendo contenido de: {url}\n")
response = requests.get(url, headers=headers, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.content, 'html.parser')

# Buscar los primeros 3 story-items
article_containers = soup.find_all('div', class_='story-item', limit=3)

print(f"🔍 Encontrados {len(article_containers)} artículos\n")

for idx, article in enumerate(article_containers, 1):
    print(f"{'='*80}")
    print(f"ARTÍCULO {idx}")
    print(f"{'='*80}\n")

    # Buscar el título
    title_elem = article.find('a', class_='story-item__title')
    if title_elem:
        print(f"📰 Título: {title_elem.get_text(strip=True)[:60]}...")

    # Buscar todas las imágenes
    img_elements = article.find_all('img')

    print(f"\n🖼️  Imágenes encontradas: {len(img_elements)}\n")

    for img_idx, img in enumerate(img_elements, 1):
        print(f"  Imagen {img_idx}:")
        print(f"  Clases: {img.get('class', [])}")

        # Mostrar todos los atributos del img
        for attr, value in img.attrs.items():
            if attr in ['src', 'data-src', 'data-original', 'data-lazy', 'srcset']:
                # Truncar URLs largas para legibilidad
                if isinstance(value, str) and len(value) > 100:
                    print(f"    {attr}: {value[:100]}...")
                else:
                    print(f"    {attr}: {value}")

        print()

    # Buscar pictures
    pictures = article.find_all('picture')
    if pictures:
        print(f"  🎨 Picture elements: {len(pictures)}")
        for pic_idx, pic in enumerate(pictures, 1):
            print(f"    Picture {pic_idx} HTML:")
            print(f"    {str(pic)[:300]}...")
            print()

    print()
