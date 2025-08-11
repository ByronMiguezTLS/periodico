# Periódico semanal de IA (gratis)

Sitio estático para **GitHub Pages** que se **actualiza solo cada domingo** usando **GitHub Actions**.
No usa API de pago: recoge **RSS**, hace resumen **extractivo** (TextRank) y publica una edición bonita y fácil de leer.

## Despliegue rápido
1. Crea un repo (p. ej. `ia-weekly`), sube todo.
2. Ve a **Settings → Pages** → `Deploy from a branch` → `main` → **/docs**.
3. En **Actions** verás el workflow `build-site`. Se ejecuta cada **domingo 08:00 UTC** (≈ 10:00 Madrid en verano). Puedes hacer **Run workflow** para publicarlo ya.

> Si quieres 10:00 exactas en invierno (CET), cambia el cron a `0 9 * * SUN`.

## Personalización
- Fuentes RSS: edita `feeds.yml`.
- Diseño: `docs/styles.css`.
- Lógica de ranking & categorías: `build.py` (sección `categorize` y `score_item`).

## Estructura
- `.github/workflows/build.yml` — planificador y build.
- `build.py` — genera resúmenes, ranking, `docs/data/edition.json` y archivo.
- `docs/index.html`, `docs/app.js`, `docs/styles.css` — front-end estático.
- `docs/data/` — JSON publicado (edición actual y archivo).
- `feeds.yml` — lista de feeds.
