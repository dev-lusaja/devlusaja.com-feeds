"""
Top del día para LinkedIn: la IA (OpenRouter) elige las noticias de IA en español más importantes
de las últimas horas y el post, armado con la plantilla de feeds_config.yaml (daily_top), se envía
a un canal de Discord por webhook.

Solo lee las BDs (feeds.db y googlenews.db); no escribe nada ni toca assets/.

Uso:
    python src/daily_top.py            # elige y envía a Discord
    python src/daily_top.py --dry-run  # elige e imprime el post, sin enviar

Requiere OPENROUTER_API_KEY y DISCORD_WEBHOOK_URL (entorno o .env).
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from dotenv import load_dotenv
from config.loader import load_feeds_config, load_daily_top_config, get_db_path
from database.connection import DatabaseConnection
from utils.logger import log

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DISCORD_MAX_CHARS = 2000
NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre"]

PROMPT = """Eres el editor de un resumen diario de noticias de inteligencia artificial en español que se publica en LinkedIn.
De la lista de noticias de las últimas horas (JSON al final), elige las {top_n} más importantes, ordenadas de mayor a menor importancia.

Criterios:
- Impacto real en la industria de la IA, en la sociedad o en la vida de las personas: lanzamientos, regulación, inversiones grandes, avances, decisiones de empresas o gobiernos.
- Que la misma historia aparezca en varios medios es señal de importancia, pero elígela una sola vez: las {top_n} deben tratar temas distintos. Entre las versiones de una misma historia, elige la que tenga la descripción más informativa.
- Evita artículos de opinión, guías, eventos locales menores y contenido promocional.

Para cada una escribe un resumen de una sola frase (máximo 25 palabras) usando solo la información del título y la descripción: no inventes cifras, nombres ni datos que no estén ahí.

Responde únicamente con JSON, sin texto adicional, con esta forma:
{{"noticias": [{{"id": "n1", "resumen": "..."}}]}}

Noticias:
{candidates}"""


def split_source(title: str, description: str) -> tuple:
    """
    Google News trae el medio al final del título ("Título - Medio") y de la descripción ("Título Medio"),
    pero no siempre, y tanto titulares como medios pueden tener " - " ("EFE - Agencia de noticias"):
    solo se separa si la descripción termina con ese mismo sufijo. Sin medio, la descripción es el
    título tal cual y no se separa nada. Devuelve (título, medio o "").
    """
    description = description.strip()
    if " ".join(description.split()) == " ".join(title.split()):
        return title, ""
    start = title.find(" - ")
    while start != -1:
        source = title[start + 3:].strip()
        if source and description.endswith(source):
            return title[:start].strip(), source
        start = title.find(" - ", start + 3)
    return title, ""


def parse_date(value: str):
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def load_candidates(feeds: list, cfg: dict) -> list:
    """Noticias de las últimas hours_back horas de las categorías de daily_top, de la más nueva a la más vieja."""
    categories = set(cfg['categories'])
    by_db = {}
    for feed in feeds:
        if feed['category'] in categories:
            by_db.setdefault(get_db_path(feed['sourceType']), set()).add(feed['category'])

    since = datetime.now(timezone.utc) - timedelta(hours=cfg.get('hours_back', 24))
    candidates, seen_titles = [], set()
    for db_path, cats in by_db.items():
        if not Path(db_path).exists():
            log(f"⚠️ No existe {db_path}, se omiten {sorted(cats)}")
            continue
        with DatabaseConnection(db_path) as db:
            cursor = db.get_cursor()
            # pubDate_parsed ignora la zona horaria: se filtra con un día de margen y el corte exacto va abajo
            cursor.execute(
                f"""SELECT title, description, sourceTitle, sourceType, pubDate FROM feeds
                    WHERE sourceCategory IN ({','.join('?' * len(cats))}) AND pubDate_parsed >= datetime(?, '-1 day')""",
                [*cats, since.strftime('%Y-%m-%d %H:%M:%S')]
            )
            rows = cursor.fetchall()

        for row in rows:
            pub_date = parse_date(row['pubDate'])
            if not pub_date or pub_date < since:
                continue
            title, description = (row['title'] or '').strip(), (row['description'] or '').strip()
            if row['sourceType'] == 'googlenews':
                # Su descripción es solo el título + el medio, no aporta nada a la IA
                title, source = split_source(title, description)
                description = ''
            else:
                source = row['sourceTitle']
            if not title or title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())
            candidates.append({'titulo': title, 'medio': source, 'fecha': pub_date, 'descripcion': description[:300]})

    candidates.sort(key=lambda c: c['fecha'], reverse=True)
    return candidates[:cfg.get('max_candidates', 150)]


def parse_selection(content: str, valid_ids: set, top_n: int) -> list:
    """Lista de (id, resumen) desde la respuesta del modelo; ValueError si no trae top_n noticias válidas."""
    # Algunos modelos envuelven el JSON en ```json ... ``` o agregan texto: se toma del primer { al último }
    data = json.loads(content[content.find('{'):content.rfind('}') + 1])
    selection, seen = [], set()
    for item in data.get('noticias', []):
        news_id, summary = item.get('id'), (item.get('resumen') or '').strip()
        if news_id in valid_ids and news_id not in seen and summary:
            seen.add(news_id)
            selection.append((news_id, summary))
    if len(selection) < top_n:
        raise ValueError(f"solo {len(selection)} noticias válidas de {top_n}")
    return selection[:top_n]


def select_top(candidates: dict, cfg: dict, api_key: str) -> list:
    """Prueba los modelos de daily_top.models en orden hasta que uno devuelva una selección válida."""
    top_n = cfg.get('top_n', 5)
    payload = [
        {'id': news_id, 'titulo': c['titulo'], 'medio': c['medio'], 'descripcion': c['descripcion']}
        for news_id, c in candidates.items()
    ]
    prompt = PROMPT.format(top_n=top_n, candidates=json.dumps(payload, ensure_ascii=False))

    for model in cfg['models']:
        try:
            resp = requests.post(
                OPENROUTER_URL,
                headers={'Authorization': f'Bearer {api_key}', 'HTTP-Referer': 'https://devlusaja.com', 'X-Title': 'devlusaja feeds'},
                json={'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0.3},
                timeout=180,
            )
            if not resp.ok:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            selection = parse_selection(resp.json()['choices'][0]['message']['content'] or '', set(candidates), top_n)
            log(f"✅ Selección hecha con {model}")
            return selection
        except Exception as e:
            log(f"⚠️ {model} falló: {e}")
    raise RuntimeError("Ningún modelo devolvió una selección válida")


def render_post(cfg: dict, candidates: dict, selection: list) -> str:
    now = datetime.now(ZoneInfo("America/Bogota"))
    items = []
    for i, (news_id, summary) in enumerate(selection):
        news = candidates[news_id]
        items.append(cfg['item_template'].format(
            numero=NUMBER_EMOJIS[i],
            titulo=news['titulo'],
            fuente=f" ({news['medio']})" if news['medio'] else "",
            resumen=summary,
        ))
    fecha = f"{now.day} de {MONTHS[now.month - 1]} de {now.year}"
    return cfg['post_template'].format(fecha=fecha, noticias="\n\n".join(items)).strip()


def send_to_discord(post: str, webhook_url: str):
    # flags=4 (SUPPRESS_EMBEDS): sin tarjeta de vista previa del link.
    # allowed_mentions vacío: un título con "@everyone" no notifica a nadie.
    payload = {'flags': 4, 'allowed_mentions': {'parse': []}}
    if len(post) <= DISCORD_MAX_CHARS:
        resp = requests.post(webhook_url, json={**payload, 'content': post}, timeout=30)
    else:
        # Discord corta los mensajes en 2.000 caracteres: el post completo va como adjunto
        payload['content'] = "📎 El post supera los 2.000 caracteres de Discord, va adjunto:"
        resp = requests.post(
            webhook_url,
            data={'payload_json': json.dumps(payload)},
            files={'files[0]': ('post-linkedin.txt', post.encode('utf-8'))},
            timeout=30,
        )
    resp.raise_for_status()


def main(dry_run: bool = False):
    # Sin webhook no hay a dónde mandar el post: se corta antes de leer la BD o gastar cupo de OpenRouter
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if not webhook_url and not dry_run:
        sys.exit("❌ Falta DISCORD_WEBHOOK_URL")
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        sys.exit("❌ Falta OPENROUTER_API_KEY")

    config_path = Path(__file__).parent.parent / "feeds_config.yaml"
    cfg = load_daily_top_config(config_path)
    top_n = cfg.get('top_n', 5)

    found = load_candidates(load_feeds_config(config_path), cfg)
    log(f"📰 {len(found)} noticias candidatas de las últimas {cfg.get('hours_back', 24)} h")
    if len(found) < top_n:
        sys.exit(f"❌ Hay {len(found)} noticias candidatas, se necesitan al menos {top_n}")
    # ids cortos (n1, n2…) en vez de los UUID: menos tokens y menos riesgo de que el modelo los copie mal
    candidates = {f"n{i}": c for i, c in enumerate(found, 1)}

    selection = select_top(candidates, cfg, api_key)
    post = render_post(cfg, candidates, selection)
    print(post)

    if dry_run:
        return
    send_to_discord(post, webhook_url)
    log("✅ Post enviado a Discord")


if __name__ == "__main__":
    main(dry_run='--dry-run' in sys.argv)
