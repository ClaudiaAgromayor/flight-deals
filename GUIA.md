# Guía: cómo se construye esto desde cero (y por qué así)

Esta guía explica el proceso que seguí, para que puedas repetirlo tú con este u otro proyecto.

---

## 0. El orden de trabajo, en resumen

1. **Convertir el deseo en reglas concretas.** "Avísame de chollos" no se puede programar; "ida y vuelta, directo, MAD→CDG/ORY, vie/sáb→dom/lun, ≤150 €" sí.
2. **Comprobar que existen los datos** y que puedo conseguirlos gratis (viabilidad).
3. **Probar la fuente más arriesgada antes de escribir nada más.** Si no consigo precios, el resto no sirve.
4. **Prototipo mínimo:** una ruta, una fecha, imprimir el precio.
5. **Generalizar:** todas las rutas y fechas, y las reglas de chollo.
6. **Memoria:** historial y "ya te avisé".
7. **Salida:** mensaje de Telegram.
8. **Automatizar:** que se ejecute solo.
9. **Endurecer:** qué pasa si algo falla, si me bloquean, si se repiten los avisos…

---

## 1. Convertir el problema en reglas

Antes de programar escribí lo que me pediste como reglas que un ordenador puede comprobar:

| Lo que dijiste | Regla en el código |
|---|---|
| "No quiero Ryanair a París porque te deja en Beauvais" | Prohibir el **aeropuerto** BVA, no la aerolínea (lo que molesta es el aeropuerto). Así también caen otras aerolíneas que vuelan a Beauvais y Vatry (XCR) |
| "Tope 150 €, ida y vuelta, por persona" | Buscar **ida y vuelta** con 1 adulto y precio ≤ 150 |
| "Sin escalas" | `max_stops=0` y descartar todo resultado con más de un tramo |
| "Viernes o sábado → domingo o lunes" | Generar las 4 combinaciones de fechas de cada fin de semana |
| "Yo voy solo desde Madrid; él puede ir a Valencia, Zaragoza o Barcelona y yo voy en tren" | Dos listas distintas: `to_paris_from: [MAD]` y `from_paris_to: [MAD, VLC, ZAZ, BCN]` |
| "Quedar en otro sitio" | Los dos vuelos, el **mismo fin de semana**, al mismo destino, con la **suma** por debajo de un tope |

💡 **Lección:** muchos fallos de software vienen de requisitos ambiguos. Por eso al principio te hice preguntas (¿el tope es ida y vuelta o por trayecto? ¿qué días?).

---

## 2. ¿Se puede hacer? Dónde están los datos

La pregunta clave era **de dónde saco los precios**. Hay tres tipos de fuente:

1. **APIs oficiales de agregadores** (Skyscanner, Kayak…): normalmente solo para empresas o socios, no para estudiantes.
2. **APIs gratuitas con limitaciones**: por ejemplo **Travelpayouts** (Aviasales). Es gratis porque vive de comisiones por afiliación. A cambio, sus precios son los que otros usuarios buscaron hace poco (caché), no en tiempo real.
3. **Scraping de una web pública**: por ejemplo **Google Flights**. Tiene los mejores datos, pero no hay API oficial, así que hay que leer la web "como un navegador".
4. **APIs de scraping de pago**: por ejemplo **SerpApi**. Ellos hacen el scraping y te dan JSON limpio. Es fiable, pero el plan gratis es pequeño.

### Cómo evalúo una fuente
- **Busco:** "flight prices API free", "google flights python", "skyscanner api free tier".
- **Miro la página de precios** y los límites del plan gratis: cuántas peticiones al mes y si piden tarjeta.
- **Leo la documentación:** qué parámetros acepta (¿puedo pedir "solo directos"? ¿ida y vuelta?) y qué devuelve (¿me dice el **aeropuerto**? Sin eso no puedo filtrar Beauvais).
- **Hago una petición de prueba** con `curl` antes de escribir código. Por ejemplo, Travelpayouts sin token me devolvió `Unauthorized`, lo que confirma que la URL existe y solo falta la clave.

### Cómo evalúo una librería gratuita (repositorio de GitHub o PyPI)
Con `fast-flights` hice esto:
1. **En GitHub:** estrellas, **fecha del último commit** (si lleva un año sin tocarse y es scraping, casi seguro está roto), issues abiertos tipo "no funciona desde…" y la licencia.
2. **La instalo en un entorno aislado** (`python -m venv`), para no ensuciar mi Python.
3. **Leo el código instalado**, no solo el README. Gracias a eso vi que la versión 3 había cambiado por completo la forma de usarla respecto a lo que yo recordaba, y que ahora devuelve los códigos de aeropuerto (justo lo que necesitaba).
4. **La pruebo en vivo** con una búsqueda real. Falló: Google me enseñaba la pantalla europea de "Antes de continuar" (cookies). Esto lo cuento en el apartado 5.

💡 **Lección:** prueba primero lo más arriesgado. Si Google no hubiera funcionado, el diseño habría sido otro.

---

## 3. Decisiones de diseño (y por qué no otras)

### ¿Por qué tres fuentes y no una?
Cada una cubre el punto débil de las otras:
- **Travelpayouts = radar.** Con 1 consulta ve un mes entero de una ruta. Es barato y amplio, pero puede estar desactualizado.
- **Google Flights = verdad.** Da el precio real, pero hace falta 1 consulta por ruta y fecha, y si abusas te bloquean.
- **SerpApi = plan B.** Solo entra si Google falla, con un contador mensual para no pasar del plan gratis.

Así el radar encuentra **candidatos** baratos y Google **confirma** solo esos. Es mucho más eficiente que preguntar a Google todo.

### ¿Por qué GitHub Actions y no otra cosa?
| Opción | Problema |
|---|---|
| Tu ordenador con una tarea programada | Tiene que estar encendido |
| Un servidor (VPS) | Cuesta dinero y hay que mantenerlo |
| Funciones en la nube (Vercel, AWS Lambda) | Límites de tiempo, y hace falta una base de datos aparte |
| **GitHub Actions** | Gratis, con programación tipo cron integrada, secretos seguros, y el propio repositorio sirve de "base de datos" |

### ¿Por qué un JSON en el repositorio y no una base de datos?
Son pocos datos (unos KB). Un JSON se lee a simple vista, no necesita ningún servicio extra y con git tienes el **historial de cambios gratis**. Con miles de rutas usaría SQLite o Postgres.

### ¿Por qué Telegram y no WhatsApp o email?
- **Telegram:** crear un bot es gratis, se hace en 2 minutos y se manda con una sola petición HTTP.
- **WhatsApp:** su API oficial es de empresa, de pago y con plantillas aprobadas.
- **Email:** se pierde entre otros correos y hay que configurar SMTP.

### Otras decisiones pequeñas
- **Buscar por aeropuerto (CDG, ORY) y no por ciudad (PAR):** "PAR" incluye Beauvais. Pidiendo los aeropuertos exactos, Beauvais ni aparece. Además, filtro BVA en los resultados por si acaso (doble seguridad).
- **Tolerancia del 15 %:** si el radar dice 160 € y el tope es 150, lo compruebo igualmente, porque el precio real puede haber bajado.
- **Pausa de 2,5 s entre búsquedas en Google:** para no parecer un robot agresivo ni sobrecargar a nadie.
- **Agrupar por fin de semana:** si MAD→CDG y MAD→ORY salen el mismo finde, solo te aviso del más barato.

---

## 4. "¿Qué modelo usas?"

**No hay inteligencia artificial ni machine learning.** Son **reglas** más **estadística sencilla**:

- **Reglas fijas:** ¿precio ≤ tope? ¿directo? ¿no es Beauvais?
- **"Lo habitual":** en cada ejecución guardo la **mediana** de los precios vistos en cada ruta. 🔥 = precio ≤ 75 % de la mediana del historial, y solo cuando hay al menos 5 datos.
- **Por qué mediana y no media:** la media se dispara con un precio absurdo de 900 € en Navidad; la mediana no.

¿Podría usarse ML para **predecir** si un precio va a bajar? Sí, pero haría falta mucho historial (meses), y lo que buscas (avisar cuando algo está barato **ahora**) se resuelve bien con reglas. Primero lo simple y que funcione; luego, si hace falta, lo sofisticado.

### El modelo de datos (cómo represento la información)
```
Offer (un vuelo de ida y vuelta)
  origen, destino, fecha ida, fecha vuelta, precio, aerolínea,
  fuente (google/serpapi/travelpayouts), enlace,
  verificado (✅ tiempo real / ⚠️ caché)

Deal (un chollo para avisar)
  tipo (visita a París / visita a España / quedada),
  1 Offer (visita) o 2 Offers (quedada: el tuyo y el suyo),
  tope, clave de historial, ¿🔥?
```
Separar "lo que encontré" (Offer) de "lo que te aviso" (Deal) permite que una quedada sean dos vuelos sumados.

---

## 5. Cómo funciona el scraping de Google Flights

Hacer scraping es **leer una web con un programa** en vez de con los ojos. Los pasos para descubrir cómo hacerlo en cualquier web:

1. **Abre la web en Chrome → F12 (DevTools) → pestaña Network.** Haz una búsqueda y mira qué peticiones salen.
2. **Fíjate en la URL.** Google Flights codifica toda la búsqueda en un parámetro `tfs=...`. Es un **protobuf** (formato binario de Google) pasado a base64. `fast-flights` sabe construirlo: ese es su gran trabajo.
3. **Mira dónde vienen los datos.** Clic derecho → "Ver código fuente" y busca un precio que veas en pantalla. En Google Flights, los resultados vienen dentro de la propia página como un bloque de JavaScript: `<script class="ds:1">…data:[…]</script>`. Se recorta ese trozo y se lee como JSON.
4. **Hazte pasar por un navegador real.** Las webes detectan robots por cómo "se presenta" la conexión (la huella TLS y las cabeceras). `fast-flights` usa la librería `primp`, que imita a Chrome.
5. **Resuelve los obstáculos.** Desde Europa, Google enseña primero el aviso de cookies. Lo detecté porque el título de la página devuelta era "Before you continue". Lo resolví enviando la cookie de "consentimiento aceptado" (`SOCS`), igual que haría tu navegador tras aceptar.
6. **Prepárate para que se rompa.** Si Google cambia su web, el código que lee `ds:1` deja de funcionar. Por eso:
   - la versión de la librería está fijada en `requirements.txt` (`fast-flights==3.1.0`), así no cambia sola;
   - si Google falla, se usa SerpApi;
   - si no hay ningún precio, te llega un aviso por Telegram.

⚖️ **Ética y legalidad:** las condiciones de Google no permiten el scraping automatizado. Para uso personal, con pocas consultas y pausas, el riesgo práctico es bajo (como mucho, un bloqueo temporal de la IP). Nunca lo usaría para algo comercial o masivo; para eso están APIs como SerpApi.

---

## 6. Lista de cosas que hay que pensar (checklist)

- **Límites y costes:** cuántas peticiones haces por ejecución × ejecuciones al día × 30. Aquí son ~130 a Google por ejecución, 4 ejecuciones al día y unos 1.000–1.200 minutos de Actions al mes.
- **Fallos silenciosos:** lo peor es que deje de funcionar sin que lo sepas. Por eso hay un aviso de error (como mucho uno al día).
- **Spam:** sin memoria te avisaría 4 veces al día del mismo vuelo. Por eso se guarda "ya avisado a X €" y solo se repite si baja otro 10 %.
- **Secretos:** las claves **nunca** van en el código. En local van en `.env` (está en `.gitignore`) y en GitHub, en *Secrets*.
- **Zonas horarias:** el cron de GitHub va en **UTC**; Madrid está a +1 o +2 horas.
- **Calidad del dato:** un precio en caché (⚠️) no es igual que uno comprobado (✅), y el mensaje lo dice.
- **Probar sin molestar:** `--dry-run` busca de verdad pero no envía nada. Además, para probar las quedadas metí a propósito un precio falso de 60 € y comprobé que el sistema lo corregía al real (112 €).
- **Mantenimiento:** versiones fijadas, un README y una configuración separada del código (`config.yaml`) para cambiar rutas sin tocar Python.

---

## 7. ¿Dónde se guarda el historial?

En **`data/state.json`**, dentro del propio repositorio. Tras cada ejecución, GitHub Actions hace un commit automático con los cambios ("Actualizar historial de precios"). Su aspecto es este:

```json
{
  "history": {
    "visit_paris|París":   [["2026-10-02", 187.0], ["2026-10-03", 179.0], ...],
    "visit_spain|Barcelona": [...],
    "meetup|Lisboa":       [...]
  },
  "alerted": {
    "visit_paris|Visita a París|2026-11-13|2026-11-16": {"price": 98.0, "depart": "2026-11-13"}
  },
  "serpapi": {"month": "2026-10", "used": 12}
}
```

- **`history`:** la mediana de precios de cada ejecución, por ruta (se guardan las 120 últimas). Con esto se calcula "lo habitual" para el 🔥.
- **`alerted`:** de qué ya te avisé y a qué precio. Los viajes pasados se borran solos.
- **`serpapi`:** cuántas búsquedas de SerpApi llevas este mes.

En GitHub puedes abrir el archivo y, con **History**, ver cómo cambian los precios con el tiempo.

---

## 8. Conectar tu Telegram (paso a paso)

1. En Telegram busca **@BotFather** (el que tiene el tick azul) y escribe `/newbot`.
2. Te pide un nombre (por ejemplo "Chollos Vuelos") y un usuario que acabe en `bot` (por ejemplo `chollos_claudia_bot`).
3. Te da un **token** del tipo `123456789:AAF...`. **No lo compartas con nadie**: quien lo tenga controla el bot.
4. **¿Solo tú o los dos?**
   - Solo tú: abre tu bot, pulsa **Iniciar** y escríbele "hola".
   - Los dos: crea un grupo con tu novio, añade el bot y escribe "hola" en el grupo.
5. Consigue el **chat id**. En la carpeta del proyecto:
   ```bash
   pip install -r requirements.txt
   ```
   ```bash
   python -m vuelos.telegram_setup TU_TOKEN
   ```
   Saldrá algo como `TELEGRAM_CHAT_ID=123456789` (en los grupos es un número negativo, `-100...`; cópialo con el signo).
6. Crea un archivo `.env` en la carpeta del proyecto con:
   ```
   TELEGRAM_BOT_TOKEN=123456789:AAF...
   TELEGRAM_CHAT_ID=123456789
   ```
   y comprueba que llega el mensaje:
   ```bash
   python -m vuelos --test-telegram
   ```
7. En GitHub: tu repositorio → **Settings → Secrets and variables → Actions → New repository secret**. Crea `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` con esos valores, y lo mismo con `TRAVELPAYOUTS_TOKEN` y `SERPAPI_KEY`.

---

## 9. Subirlo a tu repositorio

Desde la carpeta del proyecto (`Documentos\GitHub\vuelos-chollos`), en una terminal (Git Bash o PowerShell):

```bash
git init -b main
```
```bash
git add .
```
```bash
git commit -m "Primera versión del buscador de chollos"
```
```bash
git remote add origin https://github.com/ClaudiaAgromayor/vuelos-chollos.git
```
```bash
git push -u origin main
```

Antes del `git add`, comprueba con `git status` que **no aparece `.env`**. Si aparece, no hagas commit.

Después: pestaña **Actions** del repositorio → "Buscar chollos de vuelos" → **Run workflow**. La primera ejecución tarda unos 10 minutos. A partir de ahí se ejecuta sola 4 veces al día.
