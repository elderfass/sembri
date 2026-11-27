"""Motor de compatibilidad de cultivos y regla de recomendación R4.

Gemini nunca calcula la compatibilidad: se calcula aquí con los datos de cultivos.
"""
import math

from .datos import CULTIVOS, PRODUCTOS, norm

P = PRODUCTOS


def producto_por_id(pid):
    return next(p for p in P if p["id"] == pid)


# ---------- motor AgroExpert (misma fórmula del proyecto anterior) ----------
PESOS = {"suelo": 1.2, "clima": 1.2, "agua": 1.0, "ph": 1.0, "sol": 0.6}
OPCIONES = {
    "suelo": ["Arcilloso", "Arenoso", "Limoso", "Franco"],
    "clima": ["Cálido", "Templado", "Frío", "Árido"],
    "agua": ["Escasa", "Moderada", "Abundante"],
    "sol": ["Baja", "Media", "Alta"],
}
CAMPO_KB = {"suelo": "suelos", "clima": "climas", "agua": "agua", "sol": "sol"}


def _p_cat(valor, req):
    if valor in req["optimo"]:
        return 1
    if valor in req["tolerable"]:
        return 0.6
    return 0


def _p_ph(ph, c):
    if c["ph_min"] <= ph <= c["ph_max"]:
        return 1
    if ph < c["ph_min"]:
        ancho = c["ph_min"] - c["ph_tolerancia_min"]
        d = c["ph_min"] - ph
    else:
        ancho = c["ph_tolerancia_max"] - c["ph_max"]
        d = ph - c["ph_max"]
    if ancho <= 0 or d > ancho:
        return 0
    return max(0, 1 - d / ancho)


def evaluar(t):
    """Compatibilidad = (1.2·S + 1.2·C + 1.0·A + 1.0·pH + 0.6·E) / 5 × 100."""
    res = []
    for c in CULTIVOS:
        s = {
            "suelo": _p_cat(t["suelo"], c["suelos"]),
            "clima": _p_cat(t["clima"], c["climas"]),
            "agua": _p_cat(t["agua"], c["agua"]),
            "ph": _p_ph(t["ph"], c),
            "sol": _p_cat(t["sol"], c["sol"]),
        }
        bruto = sum(PESOS[k] * s[k] for k in PESOS) / 5 * 100
        comp = math.floor(bruto * 100 + 0.5) / 100
        res.append({"c": c, "comp": comp})
    res = [r for r in res if r["comp"] >= 30]
    res.sort(key=lambda r: (-r["comp"], norm(r["c"]["nombre"])))
    return res


def insumos_para(t, c):
    """Regla R4: una condición del terreno no es óptima -> sugerir el insumo que la corrige."""
    out = []
    if t["ph"] < c["ph_min"]:
        out.append((producto_por_id("P05"), f"el pH {t['ph']} está por debajo del óptimo ({c['ph_min']}–{c['ph_max']})"))
    if t["ph"] > c["ph_max"]:
        out.append((producto_por_id("P07"), f"el pH {t['ph']} está por encima del óptimo ({c['ph_min']}–{c['ph_max']})"))
    if t["ph"] < c["ph_min"] or t["ph"] > c["ph_max"]:
        out.append((producto_por_id("P10"), "conviene confirmar el pH antes de aplicar enmiendas"))
    if t["suelo"] not in c["suelos"]["optimo"] and t["suelo"] != "Franco":
        out.append((producto_por_id("P06"), f"mejora la estructura del suelo {t['suelo'].lower()}"))
    ag = OPCIONES["agua"]
    if ag.index(t["agua"]) < min(ag.index(o) for o in c["agua"]["optimo"]):
        out.append((producto_por_id("P08"), f"el agua disponible ({t['agua'].lower()}) es menor a la óptima"))
    so = OPCIONES["sol"]
    if so.index(t["sol"]) > max(so.index(o) for o in c["sol"]["optimo"]):
        out.append((producto_por_id("P09"), f"la exposición solar ({t['sol'].lower()}) supera la óptima"))
    return out