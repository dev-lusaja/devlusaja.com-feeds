"""
Top del día para LinkedIn, en dos llamadas a la IA (OpenRouter): primero agrupa las noticias de IA
en español de las últimas horas que cuentan la misma historia, después elige las más importantes.
El post, armado con la plantilla de feeds_config.yaml (daily_top), se envía a un canal de Discord por
webhook, seguido de un reporte (.txt adjunto) con cuántas veces y en qué medios salió cada historia.

Solo lee las BDs (feeds.db y googlenews.db); no escribe nada ni toca assets/.

Uso:
    python src/daily_top.py            # elige y envía a Discord
    python src/daily_top.py --dry-run  # elige e imprime el post, sin enviar

Requiere OPENROUTER_API_KEY y DISCORD_WEBHOOK_URL (entorno o .env).
"""
import json
import os
import sys
from collections import Counter
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

GROUP_PROMPT = """Eres el editor de un resumen diario de noticias de inteligencia artificial en español.
En la lista de noticias de las últimas horas (JSON al final) hay historias que salieron en varios medios con títulos distintos.
Agrupa las noticias que cuentan exactamente la misma historia (el mismo hecho, anuncio o suceso), aunque estén redactadas distinto.

Reglas:
- Agrupa solo si es el mismo hecho: dos noticias distintas sobre la misma empresa o el mismo tema no van juntas.
- Cada id puede estar en un solo grupo.
- Incluye solo los grupos de 2 o más noticias; las que no se repiten no las pongas.

Responde únicamente con JSON, sin texto adicional, con esta forma:
{{"grupos": [["n1", "n7"], ["n3", "n12", "n40"]]}}
Si ninguna historia se repite, responde {{"grupos": []}}.

Noticias:
{candidates}"""

SELECT_PROMPT = """Eres el editor de un resumen diario de noticias de inteligencia artificial en español que se publica en LinkedIn.
De la lista de historias de las últimas horas (JSON al final), elige las {top_n} más importantes, ordenadas de mayor a menor importancia.
Cada historia ya junta todas sus versiones: "num_medios" es en cuántos medios distintos salió y "medios" en cuáles.

Criterios:
- Impacto real en la industria de la IA, en la sociedad o en la vida de las personas: lanzamientos, regulación, inversiones grandes, avances, decisiones de empresas o gobiernos.
- Que una historia aparezca en muchos medios es señal de importancia.
- Las {top_n} deben tratar temas distintos.
- Evita artículos de opinión, guías, eventos locales menores y contenido promocional.

Para cada una escribe un resumen de una sola frase (máximo 25 palabras) usando solo la información del título y la descripción: no inventes cifras, nombres ni datos que no estén ahí.

Responde únicamente con JSON, sin texto adicional, con esta forma:
{{"noticias": [{{"id": "h1", "resumen": "..."}}]}}

Historias:
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
    candidates, by_title, outlets = [], {}, {}
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
            # El mismo medio llega escrito distinto según la fuente ("El País" vs "EL PAÍS" de Google News):
            # se queda la primera forma que salió para no contarlo como dos medios
            if source:
                source = outlets.setdefault(source.casefold(), source)
            if not title:
                continue
            # Mismo título = misma noticia: no se manda dos veces, pero cada medio distinto cuenta como aparición
            # (GoogleNews_IA y GoogleNews_ML suelen traer el mismo artículo del mismo medio: ese no suma)
            same = by_title.get(title.lower())
            if same:
                if source not in same['medios']:
                    same['medios'].append(source)
                continue
            by_title[title.lower()] = {'titulo': title, 'medio': source, 'medios': [source], 'fecha': pub_date, 'descripcion': description[:300]}
            candidates.append(by_title[title.lower()])

    candidates.sort(key=lambda c: c['fecha'], reverse=True)
    return candidates[:cfg.get('max_candidates', 150)]


def extract_json(content: str) -> dict:
    # Algunos modelos envuelven el JSON en ```json ... ``` o agregan texto: se toma del primer { al último }
    return json.loads(content[content.find('{'):content.rfind('}') + 1])


def call_models(prompt: str, cfg: dict, api_key: str, parse, step: str):
    """Prueba los modelos de daily_top.models en orden hasta que uno devuelva algo que parse acepte: (modelo, resultado)."""
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
            result = parse(resp.json()['choices'][0]['message']['content'] or '')
            log(f"✅ {step} hecha con {model}")
            return model, result
        except Exception as e:
            log(f"⚠️ {step}: {model} falló: {e}")
    raise RuntimeError(f"{step}: ningún modelo devolvió una respuesta válida")


def parse_groups(content: str, valid_ids: set) -> list:
    """Grupos de ids (2 o más) desde la respuesta del modelo; un id repetido se queda en el primer grupo donde salió."""
    groups, seen = [], set()
    for group in extract_json(content).get('grupos', []):
        if not isinstance(group, list):
            continue
        ids = [nid for nid in dict.fromkeys(group) if nid in valid_ids and nid not in seen]
        if len(ids) >= 2:
            seen.update(ids)
            groups.append(ids)
    return groups


def group_candidates(candidates: dict, cfg: dict, api_key: str) -> tuple:
    """Paso 1: el modelo agrupa las candidatas que cuentan la misma historia. (modelo o None, grupos); si falla, sin grupos."""
    payload = [{'id': nid, 'titulo': c['titulo'], 'descripcion': c['descripcion']} for nid, c in candidates.items()]
    prompt = GROUP_PROMPT.format(candidates=json.dumps(payload, ensure_ascii=False))
    try:
        return call_models(prompt, cfg, api_key, lambda content: parse_groups(content, set(candidates)), "Agrupación")
    except RuntimeError as e:
        # Sin agrupar el top igual sale, solo que cada candidata cuenta como una historia aparte
        log(f"⚠️ {e}; se sigue sin agrupar")
        return None, []


def build_stories(candidates: dict, groups: list) -> dict:
    """
    Una historia por grupo y por cada candidata suelta, en el orden de las candidatas (de la más nueva a la más vieja):
    {"h1": {"ids": [...], "principal": id, "medios": Counter}}. La principal, la que va al modelo y al post, es la de
    descripción más larga (Google News la trae vacía, así que gana un medio propio); en empate, la más nueva.
    """
    group_of = {nid: i for i, group in enumerate(groups) for nid in group}
    members = {}
    for nid in candidates:
        members.setdefault(group_of.get(nid, nid), []).append(nid)
    stories = {}
    for i, ids in enumerate(members.values(), 1):
        stories[f"h{i}"] = {
            'ids': ids,
            'principal': max(ids, key=lambda nid: len(candidates[nid]['descripcion'])),
            'medios': Counter(m or "medio desconocido" for nid in ids for m in candidates[nid]['medios']),
        }
    return stories


def parse_selection(content: str, valid_ids: set, top_n: int) -> list:
    """Lista de (id de historia, resumen) desde la respuesta del modelo; ValueError si no trae top_n historias válidas."""
    selection, seen = [], set()
    for item in extract_json(content).get('noticias', []):
        story_id, summary = item.get('id'), (item.get('resumen') or '').strip()
        if story_id in valid_ids and story_id not in seen and summary:
            seen.add(story_id)
            selection.append((story_id, summary))
    if len(selection) < top_n:
        raise ValueError(f"solo {len(selection)} historias válidas de {top_n}")
    return selection[:top_n]


def select_top(candidates: dict, stories: dict, cfg: dict, api_key: str) -> tuple:
    """Paso 2: el modelo elige las top_n historias más importantes. (modelo, selección)."""
    top_n = cfg.get('top_n', 5)
    payload = []
    for story_id, story in stories.items():
        news = candidates[story['principal']]
        payload.append({
            'id': story_id, 'titulo': news['titulo'], 'medio': news['medio'],
            'num_medios': len(story['medios']), 'medios': list(story['medios']),
            'descripcion': news['descripcion'],
        })
    prompt = SELECT_PROMPT.format(top_n=top_n, candidates=json.dumps(payload, ensure_ascii=False))
    return call_models(prompt, cfg, api_key, lambda content: parse_selection(content, set(stories), top_n), "Selección")


def today_label() -> str:
    now = datetime.now(ZoneInfo("America/Bogota"))
    return f"{now.day} de {MONTHS[now.month - 1]} de {now.year}"


def render_post(cfg: dict, candidates: dict, stories: dict, selection: list) -> str:
    items = []
    for i, (story_id, summary) in enumerate(selection):
        news = candidates[stories[story_id]['principal']]
        items.append(cfg['item_template'].format(
            numero=NUMBER_EMOJIS[i],
            titulo=news['titulo'],
            fuente=f" ({news['medio']})" if news['medio'] else "",
            resumen=summary,
        ))
    return cfg['post_template'].format(fecha=today_label(), noticias="\n\n".join(items)).strip()


def appearances(story: dict) -> str:
    total = sum(story['medios'].values())
    detail = ", ".join(f"{m} ({n})" if n > 1 else m for m, n in story['medios'].most_common())
    return f"{total} {'aparición' if total == 1 else 'apariciones'}: {detail}"


def render_report(candidates: dict, stories: dict, selection: list, models: tuple, hours_back: int) -> str:
    """En qué medios y cuántas veces salió cada historia del top, las más repetidas que no entraron y todas las candidatas."""
    group_model, select_model = models
    lines = [
        f"Reporte del top · {today_label()}",
        f"Agrupación: {group_model or 'falló, cada candidata cuenta como una historia aparte'}",
        f"Selección: {select_model}",
        f"{len(candidates)} candidatas de las últimas {hours_back} h → {len(stories)} historias",
        "",
    ]
    for i, (story_id, _) in enumerate(selection, 1):
        story = stories[story_id]
        lines += [f"{i}. {candidates[story['principal']]['titulo']}", f"   {appearances(story)}", ""]

    picked = {story_id for story_id, _ in selection}
    left_out = sorted(
        (sid for sid, st in stories.items() if sid not in picked and sum(st['medios'].values()) > 1),
        key=lambda sid: sum(stories[sid]['medios'].values()), reverse=True,
    )[:5]
    if left_out:
        lines.append("Las más repetidas que no entraron al top:")
        for story_id in left_out:
            story = stories[story_id]
            lines += [f"- {candidates[story['principal']]['titulo']}", f"  {appearances(story)}"]
        lines.append("")

    lines.append("Candidatas enviadas al modelo, por historia:")
    for story_id, story in stories.items():
        for nid in story['ids']:
            c = candidates[nid]
            lines.append(f"{story_id} · {nid} · {', '.join(m or 'medio desconocido' for m in c['medios'])} · {c['titulo']}")
    return "\n".join(lines)


def send_to_discord(webhook_url: str, content: str, filename: str = None, text: str = None):
    """Un mensaje al webhook; con filename, text va como .txt adjunto."""
    # flags=4 (SUPPRESS_EMBEDS): sin tarjeta de vista previa del link.
    # allowed_mentions vacío: un título con "@everyone" no notifica a nadie.
    payload = {'flags': 4, 'allowed_mentions': {'parse': []}, 'content': content}
    if filename:
        resp = requests.post(
            webhook_url,
            data={'payload_json': json.dumps(payload)},
            files={'files[0]': (filename, text.encode('utf-8'))},
            timeout=30,
        )
    else:
        resp = requests.post(webhook_url, json=payload, timeout=30)
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

    group_model, groups = group_candidates(candidates, cfg, api_key)
    stories = build_stories(candidates, groups)
    log(f"🧩 {len(stories)} historias distintas")
    if len(stories) < top_n:
        sys.exit(f"❌ Hay {len(stories)} historias distintas, se necesitan al menos {top_n}")

    select_model, selection = select_top(candidates, stories, cfg, api_key)
    post = render_post(cfg, candidates, stories, selection)
    report = render_report(candidates, stories, selection, (group_model, select_model), cfg.get('hours_back', 24))
    print(post, report, sep="\n\n" + "-" * 40 + "\n\n")

    if dry_run:
        return
    if len(post) <= DISCORD_MAX_CHARS:
        send_to_discord(webhook_url, post)
    else:
        # Discord corta los mensajes en 2.000 caracteres: el post completo va como adjunto
        send_to_discord(webhook_url, "📎 El post supera los 2.000 caracteres de Discord, va adjunto:", 'post-linkedin.txt', post)
    log("✅ Post enviado a Discord")
    # El post ya salió: si falla el reporte no se marca el job como fallido (re-ejecutarlo duplicaría el post)
    try:
        send_to_discord(webhook_url, "📊 Reporte de apariciones:", 'reporte-top.txt', report)
        log("✅ Reporte enviado a Discord")
    except requests.RequestException as e:
        log(f"⚠️ No se pudo enviar el reporte: {e}")


if __name__ == "__main__":
    main(dry_run='--dry-run' in sys.argv)
