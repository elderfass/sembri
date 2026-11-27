"""Herramientas que Gemini puede llamar. Son la ÚNICA fuente de hechos de Sembri.

Cada herramienta devuelve un dict. Las claves que empiezan por «_» son metadatos para la
interfaz (reglas aplicadas, botones sugeridos, gráficos): no se envían al modelo.
"""
import logging
import re

from . import reglas as R
from .datos import CLAVES_PRODUCTO, FAQ, PRODUCTOS, TEMAS_FAQ, cop, norm


log = logging.getLogger("sembri")


def _chip(label, texto=None):
    return {"label": label, "texto": texto or label}


# ---------- 1. Preguntas frecuentes ----------
_SEGUIR_FAQ = {
    "envios": [_chip("¿Cuánto cuesta el envío?")],
    "costo_envio": [_chip("¿Qué métodos de pago aceptan?")],
    "pagos": [_chip("¿Cómo hago un pedido?")],
    "devoluciones": [_chip("¿Cómo hago un pedido?")],
    "horario_contacto": [_chip("¿Cómo hago un pedido?")],
    "como_comprar": [_chip("¿Qué métodos de pago aceptan?")],
    "factura": [_chip("¿Cómo hago un pedido?")],
    "asesoria": [_chip("Recomiéndame un cultivo")],
    "empresa": [_chip("¿Hacen envíos a todo el país?")],
}


def consultar_faq(tema=None):
    if tema not in FAQ:
        return {"error": "Tema no reconocido.", "temas_validos": TEMAS_FAQ}
    out = {"tema": tema, "informacion": FAQ[tema],
           "instruccion": ("Redacta la respuesta con tus palabras, usando solo lo que la persona preguntó "
                           "y manteniendo exactas las cifras, plazos y condiciones.")}
    if tema in _SEGUIR_FAQ:
        out["_chips"] = _SEGUIR_FAQ[tema]
    return out


# ---------- 2. Catálogo y precios ----------
def _ficha(p):
    return {"producto": p["nombre"], "categoria": p["categoria"],
            "precio": cop(p["precio"])}


_GENERICAS = {"cultivo", "cultivos"}


def _raiz(palabra):
    """Quita la «s» final para que «fertilizante» encuentre «fertilizantes»."""
    return palabra[:-1] if palabra.endswith("s") else palabra


def _palabras(texto):
    return {_raiz(w) for w in texto.split() if len(w) > 3 and w not in _GENERICAS}


def _buscar_productos(texto):
    t = " " + norm(texto) + " "
    hallados = [p for p in PRODUCTOS if any(re.search(k, t) for k in CLAVES_PRODUCTO[p["id"]])]
    if hallados:
        return hallados
    hallados = [p for p in PRODUCTOS if norm(p["categoria"]) in t or norm(p["nombre"]) in t]
    if hallados:
        return hallados
    palabras = _palabras(t)
    return [p for p in PRODUCTOS if palabras & _palabras(norm(p["categoria"]))]


def consultar_catalogo(producto=None):
    if not producto or not str(producto).strip():
        return {"productos": [_ficha(p) for p in PRODUCTOS],
                "_chips": [_chip("¿Cómo hago un pedido?"), _chip("Recomiéndame un cultivo")]}
    hallados = _buscar_productos(str(producto))
    if not hallados:
        return {"encontrado": False,
                "mensaje": "Ese producto no está en el catálogo de AgroExpert Store.",
                "catalogo": [p["nombre"] for p in PRODUCTOS]}
    return {"encontrado": True, "productos": [_ficha(p) for p in hallados],
            "_chips": [_chip("¿Cómo hago un pedido?"), _chip("Recomiéndame un cultivo")]}


# ---------- 3. Asesoría de cultivos (motor AgroExpert) ----------
_PREGUNTAS = {
    "suelo": "¿Qué tipo de suelo tiene tu terreno?",
    "clima": "¿Cómo es el clima de la zona?",
    "agua": "¿Cuánta agua tienes disponible (lluvia o riego)?",
    "ph": "¿Cuál es el pH del suelo? Un número entre 0 y 14 (si no lo sabes, 6.5).",
    "sol": "¿Cuánta exposición solar recibe?",
}
_FRASE = {"suelo": "Mi suelo es {}", "clima": "El clima es {}", "agua": "El agua disponible es {}",
          "sol": "La exposición solar es {}"}


def _opcion(valor, opciones):
    v = norm(valor)
    return next((o for o in opciones if norm(o) == v), None)


def _chips_para(campo):
    if campo == "ph":
        return [_chip(x, f"El pH es {x}") for x in ("5.5", "6.5", "7.5")]
    orden = ["Alta", "Media", "Baja"] if campo == "sol" else R.OPCIONES[campo]
    return [_chip(o, _FRASE[campo].format(o.lower())) for o in orden]


def recomendar_cultivo(suelo=None, clima=None, agua=None, ph=None, sol=None):
    datos, invalidos = {}, []
    for campo, valor in (("suelo", suelo), ("clima", clima), ("agua", agua), ("sol", sol)):
        if valor in (None, ""):
            continue
        op = _opcion(valor, R.OPCIONES[campo])
        if op:
            datos[campo] = op
        else:
            invalidos.append(campo)
    if ph not in (None, ""):
        try:
            v = float(str(ph).strip().replace(",", "."))
            if 0 <= v <= 14:
                datos["ph"] = v
            else:
                invalidos.append("ph")
        except ValueError:
            invalidos.append("ph")

    orden = ["suelo", "clima", "agua", "ph", "sol"]
    faltan = [k for k in orden if k not in datos]
    if faltan:
        sig = faltan[0]
        return {
            "estado": "faltan_datos", "datos_recibidos": datos, "faltan": faltan,
            "valores_invalidos": invalidos,
            "siguiente_pregunta": _PREGUNTAS[sig],
            "opciones_validas": {k: R.OPCIONES[k] for k in R.OPCIONES},
            "instruccion": "Pregunta solo el siguiente dato, un paso a la vez, sin inventar valores.",
            "_chips": _chips_para(sig),
        }

    r = R.evaluar(datos)
    if not r:
        return {"estado": "sin_resultados",
                "mensaje": "Ningún cultivo alcanza el 30 % de compatibilidad con esas condiciones.",
                "_chips": [_chip("Recomiéndame un cultivo")]}
    top = r[:3]
    mejor = top[0]["c"]
    semilla = next((p for p in PRODUCTOS if mejor["id"] in p["cultivos"]), None)
    ins = R.insumos_para(datos, mejor)
    out = {
        "estado": "ok",
        "terreno": datos,
        "cultivos_mas_compatibles": [{"cultivo": x["c"]["nombre"], "compatibilidad_pct": x["comp"]} for x in top],
        "consejo_cultivo_principal": {"cultivo": mejor["nombre"], "consejo": mejor["consejos"]},
        "semilla_en_tienda": ({"producto": semilla["nombre"], "precio": cop(semilla["precio"])} if semilla else
                              f"Por ahora no vendemos semilla de {mejor['nombre'].lower()}; se puede consultar al equipo agronómico."),
        "insumos_que_corrigen_R4": [{"producto": p["nombre"], "precio": cop(p["precio"]), "motivo": por}
                                    for p, por in ins],
        "formula": "(1.2·suelo + 1.2·clima + 1.0·agua + 1.0·pH + 0.6·sol) / 5 × 100",
        "aviso": "Estimación orientativa; no es una garantía de cosecha ni reemplaza un análisis de suelo.",
        "_visual": {"tipo": "compatibilidad", "items": [
            {"nombre": x["c"]["nombre"], "pct": x["comp"]} for x in top]},
        "_chips": [_chip("Recomiéndame un cultivo"), _chip("¿Cuánto cuesta el envío?")],
    }
    if ins:
        out["_reglas"] = ["R4"]
    return out


# ---------- registro ----------
FUNCIONES = {
    "consultar_faq": consultar_faq,
    "consultar_catalogo": consultar_catalogo,
    "recomendar_cultivo": recomendar_cultivo,
}

DECLARACIONES = [
    {
        "name": "consultar_faq",
        "description": ("Devuelve la información oficial de AgroExpert Store para que redactes la respuesta a una pregunta frecuente: "
                        "envíos, costo de envío, pagos, devoluciones, horario y contacto, cómo comprar, factura, "
                        "asesoría o información de la empresa."),
        "parameters": {"type": "object", "properties": {
            "tema": {"type": "string", "enum": TEMAS_FAQ, "description": "Tema de la pregunta."}},
            "required": ["tema"]},
    },
    {
        "name": "consultar_catalogo",
        "description": ("Consulta el catálogo de AgroExpert Store y el precio de referencia de un producto, o la "
                        "lista completa si no se indica producto. Los 10 productos son semillas (maíz, frijol, "
                        "tomate, lechuga), cal agrícola, compost, azufre, kit de riego, malla sombra y kit de pH. "
                        "No contiene existencias ni disponibilidad actual."),
        "parameters": {"type": "object", "properties": {
            "producto": {"type": "string", "description": "Nombre o parte del nombre del producto. Vacío = todo el catálogo."}}},
    },
    {
        "name": "recomendar_cultivo",
        "description": ("Recomienda los 3 cultivos más compatibles con el terreno del cliente (motor AgroExpert) y los "
                        "insumos de la tienda que corrigen condiciones no óptimas (regla R4). Necesita los 5 datos: "
                        "suelo, clima, agua, pH y sol. Si falta alguno, la herramienta indica cuál preguntar. "
                        "Nunca inventes un dato que el cliente no dio."),
        "parameters": {"type": "object", "properties": {
            "suelo": {"type": "string", "enum": R.OPCIONES["suelo"]},
            "clima": {"type": "string", "enum": R.OPCIONES["clima"]},
            "agua": {"type": "string", "enum": R.OPCIONES["agua"]},
            "ph": {"type": "number", "description": "pH del suelo, entre 0 y 14."},
            "sol": {"type": "string", "enum": R.OPCIONES["sol"], "description": "Exposición solar."}}},
    },
]


def ejecutar(nombre, args):
    """Ejecuta una herramienta y separa el resultado para el modelo de los metadatos de la interfaz."""
    f = FUNCIONES.get(nombre)
    if not f:
        return {"error": "Herramienta desconocida."}, {}
    try:
        crudo = f(**{k: v for k, v in (args or {}).items()})
    except TypeError:
        crudo = {"error": "Argumentos no válidos."}
    except Exception:
        log.exception("Falló la herramienta %s", nombre)
        crudo = {"error": "La herramienta falló. No inventes datos; ofrece intentar de nuevo."}
    meta = {k[1:]: v for k, v in crudo.items() if k.startswith("_")}
    limpio = {k: v for k, v in crudo.items() if not k.startswith("_")}
    return limpio, meta