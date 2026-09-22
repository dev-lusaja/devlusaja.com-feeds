# Estructura de los JSON en `assets/`

Referencia de los archivos que `src/feed_fetcher.py` / `src/regenerate_assets.py`
publican en `assets/` (y por lo tanto en Netlify). Pensado para quien integre
estos JSON desde la web. Todos los ejemplos de este documento son salida real
de los generadores (`src/feeds/*_generator.py`), no inventada a mano.

## Tipos de archivo

| Archivo | Generador | Contenido |
|---|---|---|
| `metadata.json` | `metadata_generator.py` | Índice: qué `sourceType`/categorías existen, cuántos items y chunks tiene cada uno |
| `{sourceType}-all-chunk-{n}.json` | `chunk_generator.py` | Items de un `sourceType` completo (todas sus categorías juntas) |
| `{sourceType}-{category}-chunk-{n}.json` | `category_chunk_generator.py` | Items de una categoría puntual de un `sourceType` (ej. `pappers-arXiv_LG-chunk-0.json`) |
| `shorts-all-chunk-{n}.json` | `shorts_chunk_generator.py` | Videos cortos (`isShortVideo=1`) de YouTube y TikTok juntos, sin importar su `sourceType`/categoría |

`sourceType` actuales (ver `feeds_config.yaml`): `notice`, `forum`, `educational`, `pappers`, `youtube`, `tiktok`.

Todos los archivos de items son un **array JSON plano** (sin envoltorio `{ items: [...] }`).
Los chunks están numerados desde `0`; cuántos existen para cada `sourceType`/categoría
se puede saber de antemano leyendo `metadata.json` (no hace falta ir probando `-chunk-N`
hasta que falle).

## Item de feed (forma común)

Todos los `{sourceType}-all-chunk-*.json` y `{sourceType}-{category}-chunk-*.json`
usan la misma forma de item:

```json
{
  "id": "id-pappers-arxiv-1",
  "title": "A Great Paper on LLMs",
  "link": "https://arxiv.org/abs/2509.12345",
  "pubDate": "2026-09-21T08:00:00+00:00",
  "description": "Abstract del paper sobre LLMs.",
  "author": "J. Doe",
  "sourceTitle": "arXiv cs.LG",
  "sourceUrl": "https://export.arxiv.org/rss/cs.LG",
  "sourceCategory": "arXiv_LG",
  "sourceType": "pappers",
  "sourceCountry": "",
  "content": "",
  "image": "",
  "isShortVideo": 0,
  "isFeatured": 0,
  "linkPdf": "https://arxiv.org/pdf/2509.12345"
}
```

| Campo | Tipo | Notas |
|---|---|---|
| `id` | string | UUID5 determinístico calculado desde `link` + `sourceType`. Estable entre corridas: sirve como key/dedup en el front. |
| `title` | string | |
| `link` | string (URL) | URL original del artículo/paper/video. |
| `pubDate` | string (ISO 8601) | `datetime.isoformat()`; siempre trae offset de zona horaria. |
| `description` | string, texto plano | HTML ya limpiado (`BeautifulSoup.get_text`). Para `sourceCategory` que empieza con `arXiv` es solo el abstract. |
| `author` | string | `"Desconocido"` si el feed no trae autor. |
| `sourceTitle` | string | Nombre legible de la fuente (`title` en `feeds_config.yaml`). |
| `sourceUrl` | string | URL del feed/fuente (`url` en `feeds_config.yaml`), no del item. |
| `sourceCategory` | string | Categoría (`category` en `feeds_config.yaml`), ej. `Xataka`, `arXiv_LG`, `Featured`, `YouTube_DotCSV`. |
| `sourceType` | string | Uno de los `sourceType` listados arriba. |
| `sourceCountry` | string | Puede ser `""`. |
| `content` | string | Contenido HTML completo si el feed lo trae; casi siempre `""`. |
| `image` | string (URL) | Thumbnail/imagen destacada; `""` si no se pudo resolver. |
| `isShortVideo` | `0` \| `1` | Solo tiene sentido para `youtube`/`tiktok`. Los `isShortVideo=1` **no** aparecen en `{sourceType}-all-*` ni en `{sourceType}-{category}-*`; solo viven en `shorts-all-chunk-*.json` (ver más abajo). |
| `isFeatured` | `0` \| `1` | `1` cuando `sourceCategory == "Featured"` (hoy, solo los papers históricos de `src/utils/featured_papers.py`). Calculado al vuelo, no es una columna de la base de datos. |
| `linkPdf` | string (URL) | Solo para `sourceCategory` que empieza con `arXiv` (ej. `arXiv_LG`, `arXiv_AI`): `link` con `/abs/` reemplazado por `/pdf/`. Para el resto de categorías es `""`. |

`shorts-all-chunk-*.json` usa la misma forma **sin** `isFeatured` ni `linkPdf`
(esos dos campos no aplican a shorts, así que ni se calculan ahí):

```json
[
  {
    "id": "id-tiktok-1",
    "title": "Video de TikTok sobre IA",
    "link": "https://www.tiktok.com/@ia_hipster/video/999",
    "pubDate": "2026-09-21T15:00:00+00:00",
    "description": "Video de TikTok.",
    "author": "@ia_hipster",
    "sourceTitle": "IA Hipster",
    "sourceUrl": "https://www.tiktok.com/@ia_hipster",
    "sourceCategory": "TikTok_IAHipster",
    "sourceType": "tiktok",
    "sourceCountry": "",
    "content": "",
    "image": "https://example.com/tiktok1.jpg",
    "isShortVideo": 1
  }
]
```

## `metadata.json`

```json
{
  "totalItems": 5,
  "generatedAt": "2026-09-21T22:01:56.955005Z",
  "sources": [
    { "title": "Xataka IA", "category": "Xataka", "type": "notice" },
    { "title": "arXiv cs.LG", "category": "arXiv_LG", "type": "pappers" },
    { "title": "Papers Destacados", "category": "Featured", "type": "pappers" }
  ],
  "byType": {
    "pappers": {
      "totalItems": 1,
      "totalChunks": 1,
      "itemsPerChunk": 30,
      "chunkPrefix": "pappers-all"
    }
  },
  "categories": {
    "pappers": [
      {
        "category": "Featured",
        "title": "Papers Destacados",
        "count": 1,
        "isPriority": true,
        "totalChunks": 1,
        "chunkPrefix": "pappers-Featured"
      },
      {
        "category": "arXiv_LG",
        "title": "arXiv cs.LG",
        "count": 1,
        "isPriority": true,
        "totalChunks": 1,
        "chunkPrefix": "pappers-arXiv_LG"
      }
    ]
  },
  "shorts": {
    "totalItems": 2,
    "totalChunks": 1,
    "itemsPerChunk": 30,
    "chunkPrefix": "shorts-all"
  }
}
```

- `sources`: lista plana de **todas** las fuentes configuradas en `feeds_config.yaml`
  (aunque no tengan items todavía).
- `byType`: conteos y paginación por `sourceType`, ya aplicando las exclusiones de
  `exclusions.chunks_all` — usar para armar las URLs de `{sourceType}-all-chunk-{0..totalChunks-1}.json`.
- `categories`: igual que `byType` pero por categoría dentro de cada `sourceType` — usar
  para armar `{sourceType}-{category}-chunk-{0..totalChunks-1}.json`. `isPriority` siempre
  es `true` hoy (no hay lógica que lo ponga en `false` todavía).
- `byType`/`categories` **incluyen** los shorts en sus conteos (cuentan filas `isShortVideo=1`
  igual que las demás), pero esos items solo se pueden leer realmente desde `shorts-all-chunk-*.json`.
- `shorts`: mismo shape que una entrada de `byType`, para `shorts-all-chunk-*.json`.

## Reglas de filtrado/paginación a tener en cuenta

- **Paginación**: 30 items por chunk (`ITEMS_PER_CHUNK`), y `config.max_chunks_per_category`
  en `feeds_config.yaml` limita cuántos chunks se generan como máximo (hoy 30).
- **Antigüedad**: solo se publican items de los últimos `config.feeds_months_back` meses
  (hoy 2), **excepto** los de `sourceCategory == "Featured"`, que quedan siempre visibles
  sin importar su `pubDate`.
- **Exclusiones de `-all`**: `exclusions.chunks_all` en `feeds_config.yaml` saca categorías
  puntuales de los archivos `{sourceType}-all-*` y de los conteos de `metadata.json`
  (ej. `Featured` no aparece en `pappers-all-*`, solo en `pappers-Featured-*`).
- **Archivos obsoletos**: si una categoría pasa a tener menos chunks que en la corrida
  anterior, `utils/cleanup.py` borra los archivos sobrantes — no asumir que un chunk que
  existió una vez sigue existiendo.
