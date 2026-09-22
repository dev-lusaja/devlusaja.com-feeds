"""
Lista estática de papers históricos destacados de IA.

No requiere scraping ni red: son entradas fijas y curadas manualmente.
La categoría 'Featured' está exenta del filtro `feeds_months_back` en
database/operations.py, así que estos papers no desaparecen aunque su
pubDate (fijado a la fecha de ejecución, no la fecha real del paper) sea viejo.
"""

from datetime import datetime, timezone
from typing import Any, Dict

FEATURED_CATEGORY = "Featured"

FEATURED_PAPERS = [
    {
        "title": "Attention Is All You Need",
        "link": "https://arxiv.org/pdf/1706.03762.pdf",
        "author": "Google Brain, 2017",
        "summary": "Introduce la arquitectura Transformer, basada únicamente en mecanismos de atención, que reemplazó a las redes recurrentes y convolucionales como base de los modelos de lenguaje modernos.",
    },
    {
        "title": "ImageNet Classification with Deep Convolutional Neural Networks (AlexNet)",
        "link": "https://proceedings.neurips.cc/paper/2012/file/c399862d3b9d6b76c8436e924a68c45b-Paper.pdf",
        "author": "Universidad de Toronto, 2012",
        "summary": "Presenta AlexNet, la red neuronal convolucional que ganó ImageNet 2012 y desató el auge moderno del deep learning en visión por computador.",
    },
    {
        "title": "Generative Adversarial Nets (GAN)",
        "link": "https://arxiv.org/pdf/1406.2661.pdf",
        "author": "Universidad de Montreal, 2014",
        "summary": "Propone las redes generativas antagónicas (GAN), un marco de dos redes que compiten entre sí para generar datos sintéticos realistas.",
    },
    {
        "title": "Deep Residual Learning for Image Recognition (ResNet)",
        "link": "https://arxiv.org/pdf/1512.03385.pdf",
        "author": "Microsoft Research, 2015",
        "summary": "Introduce las conexiones residuales que permitieron entrenar redes neuronales mucho más profundas, base de gran parte de la visión por computador moderna.",
    },
    {
        "title": "Mastering the game of Go with deep neural networks and tree search (AlphaGo)",
        "link": "https://storage.googleapis.com/deepmind-media/alphago/AlphaGoNaturePaper.pdf",
        "author": "Google DeepMind, 2016",
        "summary": "Describe AlphaGo, el primer sistema en vencer a un profesional humano en Go combinando redes neuronales profundas con búsqueda en árbol Monte Carlo.",
    },
    {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "link": "https://arxiv.org/pdf/1810.04805.pdf",
        "author": "Google, 2018",
        "summary": "Presenta BERT, un modelo de lenguaje preentrenado de forma bidireccional que estableció un nuevo estándar en tareas de comprensión de lenguaje natural.",
    },
    {
        "title": "Language Models are Few-Shot Learners (GPT-3)",
        "link": "https://arxiv.org/pdf/2005.14165.pdf",
        "author": "OpenAI, 2020",
        "summary": "Muestra que escalar los modelos de lenguaje a 175B parámetros (GPT-3) permite resolver tareas con muy pocos ejemplos (few-shot learning), sin ajuste fino.",
    },
    {
        "title": "High-Resolution Image Synthesis with Latent Diffusion Models",
        "link": "https://arxiv.org/pdf/2112.10752.pdf",
        "author": "LMU Munich / Runway, 2022",
        "summary": "Propone los modelos de difusión latente, que reducen drásticamente el coste computacional de la generación de imágenes y son la base de Stable Diffusion.",
    },
    {
        "title": "Training language models to follow instructions with human feedback (InstructGPT)",
        "link": "https://arxiv.org/pdf/2203.02155.pdf",
        "author": "OpenAI, 2022",
        "summary": "Introduce el ajuste por refuerzo con retroalimentación humana (RLHF) para alinear modelos de lenguaje con las instrucciones del usuario; base de ChatGPT.",
    },
    {
        "title": "LLaMA: Open and Efficient Foundation Language Models",
        "link": "https://arxiv.org/pdf/2302.13971.pdf",
        "author": "Meta AI, 2023",
        "summary": "Presenta LLaMA, una familia de modelos de lenguaje fundacionales entrenados únicamente con datos públicos, competitivos con modelos mucho mayores.",
    },
    {
        "title": "DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning",
        "link": "https://arxiv.org/pdf/2501.12948.pdf",
        "author": "DeepSeek, 2025",
        "summary": "Muestra cómo entrenar capacidades de razonamiento en modelos de lenguaje mediante aprendizaje por refuerzo a gran escala, sin depender de ajuste fino supervisado previo.",
    },
]


def get_featured_papers(url: str = "featured-papers") -> Dict[str, Any]:
    """
    Devuelve la lista fija de papers destacados en formato compatible con feedparser.

    Args:
        url: Ignorado, se mantiene por compatibilidad con la firma de fetch_feed.

    Returns:
        Diccionario con estructura compatible con feedparser.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    entries = [
        {
            "title": paper["title"],
            "link": paper["link"],
            "author": paper["author"],
            "summary": paper["summary"],
            "published": now_iso,
        }
        for paper in FEATURED_PAPERS
    ]

    return {
        "feed": {
            "title": "Papers Destacados",
            "link": url,
            "description": "Papers históricos destacados de inteligencia artificial",
            "language": "es",
        },
        "entries": entries,
        "bozo": 0,
    }


def is_featured_papers_feed(category: str = None) -> bool:
    """Determina si un feed debe usar la lista estática de papers destacados."""
    return category == FEATURED_CATEGORY


def is_featured(category: str) -> int:
    """1 si la categoría es la de papers destacados, 0 en caso contrario."""
    return 1 if category == FEATURED_CATEGORY else 0
