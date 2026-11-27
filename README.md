# Sembri, asistente de AgroExpert Store (Python + API de Gemini)

Versión en Python del chatbot del *Taller Final: Chatbot Sembri para AgroExpert Store*.
Usa Gemini para entender las preguntas y redactar respuestas. Incluye preguntas frecuentes,
un catálogo de referencia y asesoría de cultivos. No muestra ni responde con datos de existencias o ventas.

## Cómo ejecutarlo

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # escribe GEMINI_API_KEY en .env
python app.py
```

Abre http://127.0.0.1:5000. La clave se crea en https://aistudio.google.com/apikey.
El modelo se cambia con `GEMINI_MODEL` en `.env` (por defecto `gemini-3.5-flash-lite`).
`GEMINI_TIMEOUT_MS` limita la espera de Gemini (por defecto `30000`).

## Alcance

1. **Preguntas frecuentes** de la tienda.
2. **Catálogo y precios de referencia**; no se informa disponibilidad.
3. **Asesoría de cultivos** usando el motor AgroExpert y la regla R4.

El chatbot rechaza consultas de inventario, existencias, ventas e indicadores porque no hay datos reales conectados.
Las sugerencias de seguimiento aparecen después de las respuestas, dentro de la conversación.

## Estructura

```
app.py                    servidor Flask (/, /api/estado, /api/chat, /salud)
sembri/datos.py           catálogo de referencia, políticas y utilidades
sembri/reglas.py          motor AgroExpert y regla R4
sembri/herramientas.py    herramientas de FAQ, catálogo y asesoría
sembri/asistente.py       instrucciones y bucle de function calling
data/                     catálogo ficticio y cultivos.json (13 cultivos)
templates/, static/       interfaz del chat
tests/                    pruebas del catálogo, el chat y la asesoría
```

## Pruebas

```bash
python -m unittest discover -s tests -v
```

No consumen la API de Gemini.

Los nombres y precios del catálogo son ficticios y no representan una tienda real.
