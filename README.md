# Rastreador de precios y detector de errores de tarifa (Colombia)

Rastrea precios en Éxito, Olímpica, Mercado Libre, Falabella, Alkosto y Ktronix, detecta
caídas anómalas (posibles *price glitches*) y avisa por un bot de Telegram.

## Cómo funciona
1. `watchlist.json` define qué términos buscar en cada tienda.
2. Cada ciclo guarda los precios en SQLite (`pricewatch.db`).
3. El detector compara contra la **mediana histórica** del producto (necesita ≥3
   observaciones) y contra el **precio de lista** que publica la tienda.
4. Si hay caída ≥ umbral y no se alertó ese precio antes, se envía el aviso a todos los
   suscriptores (`/start` y `/stop` en el bot).

## Puesta en marcha
```bash
pip install -r requirements.txt
cp .env.example .env        # y completa TELEGRAM_BOT_TOKEN (créalo con @BotFather)
export $(grep -v '^#' .env | sed 's/ *#.*//' | xargs)
python -m pricewatch.main --dry-run          # prueba sin enviar
python -m pricewatch.main --loop 60          # producción: un ciclo por minuto
python -m unittest discover -s tests -v      # tests
```

## Estado de los scrapers (importante)
| Tienda | Método | Estado |
|---|---|---|
| Éxito, Olímpica | API de catálogo VTEX | Sin verificar contra el sitio en vivo |
| Mercado Libre | API oficial | Puede exigir `ML_ACCESS_TOKEN` |
| Falabella | JSON `__NEXT_DATA__` | Sin verificar; anti-bots fuerte |
| Alkosto, Ktronix | JSON-LD de la búsqueda | El menos fiable; puede requerir su API interna |

Los scrapers se escribieron sin acceso a los sitios reales. Ejecuta `--dry-run`, mira
qué tienda devuelve 0 productos y ajusta ese scraper (cada uno es un archivo corto).

## Velocidad de las alertas
Los "segundos" dependen del intervalo de rastreo. Para minutos usa `--loop` en un VPS
pequeño o un contenedor. GitHub Actions con cron no baja de ~5 min y no es fiable en
tiempo; sirve solo para pruebas.

## Consideraciones legales y de buena conducta
- Revisa los términos de uso y el `robots.txt` de cada sitio antes de rastrear a escala.
- Mantén pausas entre peticiones (`Scraper.delay`) y no abuses del volumen.
- Las ofertas por error de precio no obligan a la tienda a vender: pueden cancelar el pedido.
- Si vas a publicar el servicio a terceros, define aviso de privacidad (Ley 1581 de 2012)
  para los chat IDs de los suscriptores.

## Siguientes pasos
Extraer histórico por categoría con sitemaps, cola de tareas, panel web, filtros por
usuario (marca, categoría, % mínimo) y proxies rotativos.
