# ✈️ Buscador de chollos de vuelos (Madrid ⇄ París y quedadas)

Mira precios 4 veces al día en GitHub Actions (gratis, sin servidor) y te escribe por Telegram cuando encuentra:

- 🗼 **Visita a París**: MAD → CDG/ORY, ida y vuelta ≤ 150 € por persona
- 🏠 **Visita a España**: CDG/ORY → Madrid, Valencia, Zaragoza o Barcelona (a las tres últimas vas tú en tren 🚄), ida y vuelta ≤ 150 € por persona
- 💑 **Quedada**: Madrid → X **y** París → X el mismo fin de semana, con los dos billetes sumando ≤ 200 €

Siempre **vuelos directos**, **viernes o sábado → domingo o lunes**, y **nunca Beauvais (BVA) ni Vatry (XCR)**, ni en ida ni en vuelta, en ninguna ruta.
Todo esto se cambia en [`config.yaml`](config.yaml).

## Cómo funciona

```
GitHub Actions (4 veces al día)
 │
 ├─ 1. RADAR · Travelpayouts ──── barre todas las rutas × 4 meses (precios en caché, gratis)
 ├─ 2. ESCANEO · Google Flights ─ Madrid ⇄ CDG/ORY, cada fin de semana de las próximas 8 semanas
 ├─ 3. COMPROBACIÓN ───────────── todo lo que pinta barato se vuelve a mirar en tiempo real
 │      Google Flights  ──si Google nos bloquea──▶  SerpApi (plan B, 200 búsquedas/mes)
 ├─ 4. DECISIÓN ───────────────── ¿por debajo del tope? ¿muy por debajo de lo habitual? (🔥)
 ├─ 5. FILTRO ANTISPAM ────────── no repite avisos salvo que el precio baje otro 10 %
 ├─ 6. TELEGRAM ───────────────── un mensaje con todos los chollos nuevos y enlaces
 └─ 7. MEMORIA ────────────────── guarda historial y avisos en data/state.json (commit automático)
```

| Fuente | Papel | Coste | Punto débil |
|---|---|---|---|
| **Travelpayouts** | Radar: ve meses enteros de golpe | Gratis | Precios de hace horas o días |
| **Google Flights** (`fast-flights`) | Precio real y escaneo de la ruta principal | Gratis | Es scraping: Google puede bloquearlo |
| **SerpApi** | Plan B cuando Google falla | Gratis hasta ~250 al mes | Pocas búsquedas |

En las quedadas, si el radar solo tiene precio para uno de los dos lados, el sistema estima el otro con lo más barato que ha visto y, si la suma promete, busca los dos lados en tiempo real.

## Puesta en marcha (unos 20 minutos)

### 1. Bot de Telegram
1. En Telegram, abre **@BotFather** → `/newbot` → ponle un nombre → copia el **token**.
2. Escríbele cualquier cosa a tu bot nuevo (o crea un grupo con tu novio, mete al bot y escribe allí, y os llega a los dos).
3. Para obtener el chat id:
   ```bash
   python -m vuelos.telegram_setup TU_TOKEN
   ```
   (o abre `https://api.telegram.org/botTU_TOKEN/getUpdates` en el navegador y busca `"chat":{"id":...}`).

### 2. Travelpayouts (radar)
Regístrate gratis en <https://www.travelpayouts.com> → **Tools → API** → copia el **API token**.

### 3. SerpApi (plan B)
Regístrate gratis en <https://serpapi.com> → **Dashboard → API key**.

### 4. GitHub
1. Crea un repositorio (puede ser **privado**) y sube esta carpeta.
2. **Settings → Secrets and variables → Actions → New repository secret** y crea:
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TRAVELPAYOUTS_TOKEN`, `SERPAPI_KEY`
3. **Actions** → "Buscar chollos de vuelos" → **Run workflow** para probarlo ya.

A partir de ahí se ejecuta solo. Si el radar o SerpApi no tienen clave, el sistema funciona con lo que tenga.

## Probar en tu ordenador

```bash
pip install -r requirements.txt
```
Crea un archivo `.env` (nunca se sube a GitHub) con:
```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TRAVELPAYOUTS_TOKEN=...
SERPAPI_KEY=...
```
```bash
python -m vuelos --test-telegram
```
```bash
python -m vuelos --dry-run
```
`--dry-run` busca de verdad, pero imprime los mensajes en lugar de enviarlos.

## Ajustes típicos (`config.yaml`)
- **Otro destino**: añade una línea en `meetup.destinations` (`city` = código IATA de la ciudad).
- **Tope de una quedada concreta**: `max_total: 180` en esa línea.
- **Otros fines de semana** (p. ej. jueves → domingo): añade `[3, 6]` a `weekend_patterns`.
- **Otra ciudad a la que puedas ir en tren**: añádela a `visit.from_paris_to` (y su nombre en `CITIES`, en `vuelos/models.py`).
- **Más o menos frecuencia**: cambia el `cron` en `.github/workflows/vuelos.yml`.

## Notas
- Los precios son por persona, ida y vuelta, en euros, sin equipaje facturado.
- ✅ = comprobado en tiempo real; ⚠️ = precio de caché (puede haber cambiado).
- 🔥 aparece cuando hay al menos 5 ejecuciones de historial y el precio está un 25 % por debajo de lo habitual en esa ruta.
- Un repositorio privado tiene 2.000 minutos gratis de Actions al mes; esto gasta unos 1.000–1.200 (si el repositorio es público, es ilimitado).
- Si Google cambia su web, `fast-flights` puede dejar de funcionar hasta que lo actualicen. Mientras tanto, SerpApi sigue cubriendo las comprobaciones, y si no se puede consultar nada te llega un aviso por Telegram (como mucho uno al día).
