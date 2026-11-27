"""Catálogo de referencia, cultivos y textos de políticas de AgroExpert Store.

Todo lo que Sembri puede afirmar sale de este módulo y de los JSON de /data.
"""
import json
import re
import unicodedata
from pathlib import Path

RUTA_DATOS = Path(__file__).resolve().parent.parent / "data"


def _cargar(nombre):
    with open(RUTA_DATOS / nombre, encoding="utf-8") as f:
        return json.load(f)


NEGOCIO = _cargar("negocio.json")
CULTIVOS = _cargar("cultivos.json")          # base de 13 cultivos de AgroExpert

PRODUCTOS = NEGOCIO["productos"]


def norm(texto):
    """Minúsculas, sin tildes ni signos: la misma normalización del prototipo."""
    t = unicodedata.normalize("NFD", str(texto))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").lower()
    t = re.sub(r"[¿?¡!.,;:()\"']", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def cop(valor):
    """$ 28.000"""
    return "$\u00a0" + f"{round(valor):,}".replace(",", ".")


# Textos de preguntas frecuentes (contenido del taller, Reto 3).
FAQ = {
    "envios": (
        "Sí, enviamos a todo Colombia desde la bodega en Funza (Cundinamarca). "
        "Bogotá y Sabana: 1 a 2 días hábiles. Ciudades principales: 2 a 4 días hábiles. "
        "Municipios y zonas rurales: 4 a 7 días hábiles. "
        "Al despachar se envía el número de guía por correo y WhatsApp."
    ),
    "costo_envio": (
        "El envío es gratis en compras desde $ 250.000. Por debajo de ese valor cuesta "
        "$ 12.000 en Bogotá y $ 18.000 en el resto del país. Los bultos de 40 a 50 kg pueden "
        "tener un recargo por peso que se muestra antes de pagar."
    ),
    "pagos": (
        "Se aceptan tarjeta débito y crédito, PSE, Nequi y Daviplata. En Bogotá, Medellín, Cali y "
        "Bucaramanga también hay pago contraentrega para pedidos hasta $ 600.000."
    ),
    "devoluciones": (
        "Hay 15 días calendario desde que se recibe el pedido para solicitar cambio o devolución. "
        "Las semillas deben estar en su empaque sellado; herramientas y kits, sin uso. "
        "Si el producto llegó dañado, se repone sin costo: se debe escribir con el número de "
        "pedido y una foto."
    ),
    "horario_contacto": (
        "Atención de lunes a sábado, de 7:00 a. m. a 6:00 p. m. La tienda en línea recibe pedidos "
        "las 24 horas. WhatsApp: 300 000 0000. Correo: atencion@agroexpertstore.example "
        "(datos de contacto ficticios)."
    ),
    "como_comprar": (
        "1) Buscar el producto en el catálogo o pedir una recomendación. 2) Agregarlo al carrito y "
        "elegir la cantidad. 3) Ingresar la dirección de entrega y el método de pago. "
        "4) Confirmar el pedido: llega un correo con el resumen y luego la guía de envío."
    ),
    "factura": (
        "Todas las compras generan factura electrónica. Si se necesita a nombre de una empresa o "
        "finca, se escribe el NIT o la cédula en el paso de pago; llega al correo registrado en "
        "menos de 24 horas."
    ),
    "asesoria": (
        "La asesoría básica es gratuita: Sembri puede estimar qué cultivos se adaptan al terreno. "
        "Para casos puntuales, el equipo agronómico responde por WhatsApp en horario de atención. "
        "Las recomendaciones son orientativas y no reemplazan un análisis de suelo."
    ),
    "empresa": (
        "AgroExpert Store es una tienda en línea colombiana (ficticia) que vende semillas, "
        "fertilizantes y enmiendas, sistemas de riego, protección de cultivos y herramientas a "
        "agricultores, viveros y huertas urbanas. Despacha a todo el país desde una bodega en Funza "
        "(Cundinamarca). Su diferencial es el selector de cultivos AgroExpert: antes de comprar, el "
        "cliente describe su terreno (suelo, clima, agua, pH y sol) y la tienda indica qué cultivos "
        "se adaptan mejor y qué insumos le sirven."
    ),
}

TEMAS_FAQ = list(FAQ.keys())

# Palabras que identifican cada producto en una búsqueda (patrones sobre texto normalizado).
CLAVES_PRODUCTO = {
    "P01": [r"\bmaiz\b"],
    "P02": [r"\bfrijol\b"],
    "P03": [r"\btomate\b"],
    "P04": [r"\blechuga\b"],
    "P05": [r"\bcal\b", r"cal agricola", r"calcare"],
    "P06": [r"compost", r"\babono\b"],
    "P07": [r"azufre"],
    "P08": [r"riego", r"goteo"],
    "P09": [r"malla", r"polisombra", r"sombra"],
    "P10": [r"kit de ph", r"analisis de ph", r"medidor", r"kit de analisis", r"\bph\b"],
}
