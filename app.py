"""Servidor web de Sembri, asistente de AgroExpert Store (Flask + API de Gemini)."""
import logging
import os
import threading
import time
import uuid
from collections import deque

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

from sembri.asistente import ErrorSembri, Sembri      # noqa: E402

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

MAX_CARACTERES = 500
MODELO = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_TIMEOUT_MS = int(os.getenv("GEMINI_TIMEOUT_MS", "30000"))        # por llamada a Gemini
GEMINI_PRESUPUESTO_MS = int(os.getenv("GEMINI_PRESUPUESTO_MS", "28000"))  # total por solicitud (< 35 s del navegador)
LIMITE_POR_MINUTO = int(os.getenv("RATE_LIMIT_PER_MIN", "20"))
sembri = (Sembri(API_KEY, MODELO, timeout_ms=GEMINI_TIMEOUT_MS, presupuesto_ms=GEMINI_PRESUPUESTO_MS)
          if API_KEY else None)

_peticiones = {}                  # ip -> marcas de tiempo de la última ventana de 60 s
_candado = threading.Lock()


def excede_limite(ip):
    """Límite sencillo por IP para no gastar la cuota de Gemini."""
    ahora = time.monotonic()
    with _candado:
        if len(_peticiones) > 5000:
            for k in [k for k, v in _peticiones.items() if not v or ahora - v[-1] > 60]:
                del _peticiones[k]
        cola = _peticiones.setdefault(ip, deque())
        while cola and ahora - cola[0] > 60:
            cola.popleft()
        if len(cola) >= LIMITE_POR_MINUTO:
            return True
        cola.append(ahora)
        return False

SALUDO = {
    "texto": ("¡Hola! Soy **Sembri**, el asistente de AgroExpert Store. Puedo ayudarte con envíos, pagos y "
              "devoluciones, consultar productos y precios, y recomendarte qué sembrar según tu terreno."),
}


@app.get("/")
def inicio():
    return render_template("index.html", modelo=MODELO)


@app.get("/api/estado")
def estado():
    """Estado del asistente para iniciar la interfaz."""
    return jsonify({
        "saludo": SALUDO,
        "configurado": sembri is not None,
    })


@app.post("/api/chat")
def chat():
    if excede_limite(request.remote_addr or "?"):
        return jsonify({"error": "Estás enviando mensajes muy rápido. Espera un momento e intenta de nuevo."}), 429
    cuerpo = request.get_json(silent=True) or {}
    mensaje = str(cuerpo.get("mensaje", "")).strip()
    if not mensaje:
        return jsonify({"error": "Escribe una pregunta para poder ayudarte."}), 400
    if len(mensaje) > MAX_CARACTERES:
        return jsonify({"error": f"El mensaje es muy largo (máximo {MAX_CARACTERES} caracteres)."}), 400
    if sembri is None:
        return jsonify({"error": "Falta configurar GEMINI_API_KEY en el archivo .env del servidor."}), 503

    sid = str(cuerpo.get("sesion") or uuid.uuid4())[:64]
    try:
        respuesta = sembri.responder(sid, mensaje)
    except ErrorSembri as e:
        return jsonify({"error": e.mensaje}), e.estado
    except Exception:
        logging.exception("Error inesperado en /api/chat")
        return jsonify({"error": "Ocurrió un error inesperado. Intenta de nuevo."}), 500
    return jsonify({"sesion": sid, **respuesta})


@app.get("/salud")
def salud():
    return jsonify({"ok": True, "modelo": MODELO, "gemini_configurado": sembri is not None})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
