#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GATÓPOLIS: la ciudad de los gatos digitales (juego educativo)
Asignatura: Ética y Legislación en Tecnologías de la Información (E-ELTI-3)
Proyecto final - Diciembre 2026

Cuatro distritos, cuatro modos de juego (uno por unidad):
  I   Casa de la Moral ........ historia en chat
  II  Oficina de Datos ........ inspección de oficina
  III Tribunal Gatuno ......... juicio: falta ética, infracción o delito
  IV  Laboratorio ............. revisión de cumplimiento y lanzamiento

Licencia del código: MIT.  Licencia del contenido (textos, escenarios): CC BY-SA 4.0.
Interfaz gráfica con tkinter (incluido en Python). No requiere instalar nada.
Ejecutar:  python gatopolis.py
"""
import json
import math
import os
import random
import re
import sys
import time

if sys.version_info < (3, 8):
    print("Gatópolis necesita Python 3.8 o superior. Tienes: " + sys.version.split()[0])
    input("Presiona Enter para cerrar...")
    sys.exit(1)

try:
    import tkinter as tk
except ImportError:
    print("Este juego necesita tkinter (viene con el instalador de Python de python.org).")
    input("Presiona Enter para cerrar...")
    sys.exit(1)

AUTORES = "[Escribir aquí los integrantes del equipo]"
VERSION = "2.0"

REFERENCIAS = [
 "Constitución Política de los Estados Unidos Mexicanos (Arts. 1, 6, 7, 8 y 16).",
 "Ley Federal de Protección de Datos Personales en Posesión de los Particulares (LFPDPPP).",
 "Ley Federal del Derecho de Autor (LFDA).",
 "Ley Federal de Protección a la Propiedad Industrial (LFPPI).",
 "Código Penal Federal (Arts. 211 bis 1 y ss., 386, 397 y ss., 424 bis) y Ley Olimpia.",
 "Ley Federal de Protección al Consumidor (Art. 76 bis) y Código de Comercio (Arts. 89 y ss.).",
 "NOM-035-STPS-2018; Ley Federal para Prevenir y Eliminar la Discriminación.",
 "Convenio de Budapest (2001); Recomendación UNESCO sobre ética de la IA (2021); Reglamento (UE) 2024/1689.",
 "Códigos de ética ACM e IEEE.",
]


W, H = 1100, 640

# ----------------------------------------------------------------------
#  HOJA DE ESTILOS (mini-CSS). tkinter no lee CSS real, así que el juego
#  incluye este pequeño intérprete: cambia colores y medidas aquí.
# ----------------------------------------------------------------------
CSS = """
/* ===== Michi Survivor · hoja de estilos ===== */
:root {
  --pared: #f5ead8;   --pared2: #f0e1cb;  --piso: #e8d3b3;   --tablon: #d9bf9a;
  --tarjeta: #fffaf0; --borde: #d6bf9f;   --sombra: #e2d0b4;
  --tinta: #5a4636;   --tinta2: #8c7561;  --oro: #e3a82f;
  --durazno: #f8c8a8; --rosa: #f6b9c6;    --menta: #b8e2c4;  --cielo: #b6d9f0;
  --lavanda: #d2c6ec; --mantequilla: #fae3a2; --coral: #f4a9a0;
  --bloqueado: #ddd2c0;
}
.boton     { border-radius: 16px; box-shadow: 5px; border-width: 2px; gloss: 0.30; lift: 2px; }
.panel     { border-radius: 16px; box-shadow: 5px; border-width: 3px; }
.pildora   { box-shadow: 3px; border-width: 2px; }
.animacion { fps: 6; hover-ms: 50; }
"""


def _parse_css(texto):
    texto = re.sub(r"/\*.*?\*/", "", texto, flags=re.S)
    reglas = {}
    for sel, cuerpo in re.findall(r"([^{}]+)\{([^}]*)\}", texto):
        d = reglas.setdefault(sel.strip(), {})
        for decl in cuerpo.split(";"):
            if ":" in decl:
                k, v = decl.split(":", 1)
                d[k.strip()] = v.strip()
    return reglas


REGLAS = _parse_css(CSS)


def _val(v):
    m = re.fullmatch(r"var\((--[\w-]+)\)", v)
    if m:
        return _val(REGLAS[":root"][m.group(1)])
    if re.fullmatch(r"-?[\d.]+(px)?", v):
        return float(v.replace("px", ""))
    return v


def css(sel, prop, default=None):
    v = REGLAS.get(sel, {}).get(prop)
    return default if v is None else _val(v)


def C(nombre):
    return _val(f"var(--{nombre})")


WALL, WALL2, FLOOR, PLANK = C("pared"), C("pared2"), C("piso"), C("tablon")
CARD, BORDER, SHADOW = C("tarjeta"), C("borde"), C("sombra")
INK, INK2, GOLD = C("tinta"), C("tinta2"), C("oro")
PEACH, PINK, MINT, SKY = C("durazno"), C("rosa"), C("menta"), C("cielo")
LAV, BUTTER, CORAL, LOCK = C("lavanda"), C("mantequilla"), C("coral"), C("bloqueado")
UCOL = [SKY, LAV, MINT, PEACH]
FONT = "Segoe UI"
SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gatopolis_progreso.json")
XP_LVL = 250

# ----------------------------------------------------------- color
def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def shade(c, t=0.25):
    return mix(c, INK, t)


def light(c, t=0.35):
    return mix(c, "#ffffff", t)


# ======================================================================
#                   PERSONAJES ANIMADOS (gatos y ratones)
# ======================================================================
class Actor:
    """Dibuja una vez y luego anima moviendo grupos de figuras (rápido y fluido)."""
    _n = 0

    def __init__(self, c, cx, cy, s, extra=()):
        Actor._n += 1
        self.c, self.cx, self.cy, self.s = c, cx, cy, s
        self.uid = f"ac{Actor._n}_"
        self.extra = tuple(extra)
        self.off = {}
        self.est = {}
        self.cache = {}
        self.t0 = time.time()

    def X(self, v): return self.cx + v * self.s
    def Y(self, v): return self.cy + v * self.s

    def tg(self, g):
        gs = (g,) if isinstance(g, str) else tuple(g)
        return (self.uid,) + tuple(self.uid + x for x in gs if x) + self.extra

    def oval(self, a, b, d, e, g="", **k):
        return self.c.create_oval(self.X(a), self.Y(b), self.X(d), self.Y(e), tags=self.tg(g), **k)

    def rect(self, a, b, d, e, g="", **k):
        return self.c.create_rectangle(self.X(a), self.Y(b), self.X(d), self.Y(e), tags=self.tg(g), **k)

    def poly(self, pts, g="", **k):
        flat = []
        for px, py in pts:
            flat += [self.X(px), self.Y(py)]
        return self.c.create_polygon(*flat, tags=self.tg(g), **k)

    def line(self, pts, w=2, color=INK, g="", smooth=False, **k):
        flat = []
        for px, py in pts:
            flat += [self.X(px), self.Y(py)]
        return self.c.create_line(*flat, width=max(1, w * self.s), fill=color, smooth=False,
                                  capstyle="round", tags=self.tg(g), **k)

    def text(self, x, y, t, size, color, g=""):
        return self.c.create_text(self.X(x), self.Y(y), text=t, tags=self.tg(g),
                                  font=("Consolas", max(6, int(size * self.s)), "bold"), fill=color)

    def mover(self, g, dx, dy):
        dx, dy = round(dx), round(dy)          # píxeles enteros: sin redibujos invisibles
        ox, oy = self.off.get(g, (0, 0))
        if dx != ox or dy != oy:
            self.c.move(self.uid + g, dx - ox, dy - oy)
            self.off[g] = (dx, dy)

    def setpts(self, item, pts, g=""):
        o1 = self.off.get("", (0, 0))
        o2 = self.off.get(g, (0, 0)) if g else (0, 0)
        flat = []
        for px, py in pts:
            flat += [round(self.X(px) + o1[0] + o2[0]), round(self.Y(py) + o1[1] + o2[1])]
        key = tuple(flat)
        if self.cache.get(item) != key:
            self.cache[item] = key
            self.c.coords(item, *flat)

    def cambio(self, clave, valor):
        if self.est.get(clave) != valor:
            self.est[clave] = valor
            return True
        return False

    def parpadeo(self, cerrado):
        if self.cambio("blink", cerrado):
            self.c.itemconfigure(self.uid + "eo", state="hidden" if cerrado else "normal")
            self.c.itemconfigure(self.uid + "ec", state="normal" if cerrado else "hidden")


class CatActor(Actor):
    """Michi, el gato defensor ético. mood: happy | neutral | sad"""

    def __init__(self, c, cx, cy, s=1.0, mood="neutral", extra=(), salto=False, peluca=False):
        super().__init__(c, cx, cy, s, extra)
        self.mood, self.salto = mood, salto
        FUR, DK, LT = "#f4b883", "#c98550", "#fbd9b6"
        # cola
        self.tail = self.line([(34, 48), (62, 46), (74, 16), (64, -12)], w=11, color=FUR, g="b", smooth=False)
        # patas
        for x1 in (-28, 6):
            self.oval(x1, 70, x1 + 22, 88, fill=FUR, outline=DK)
            self.line([(x1 + 7, 80), (x1 + 7, 86)], w=1.5, color=DK)
            self.line([(x1 + 15, 80), (x1 + 15, 86)], w=1.5, color=DK)
        # cuerpo con suéter y corbata
        self.oval(-38, -8, 38, 78, g="b", fill="#a9cdea", outline="#79a4c9", width=2)
        self.oval(-24, 14, 24, 70, g="b", fill="#c5e0f4", outline="")
        self.poly([(-14, -2), (0, 22), (14, -2)], g="b", fill="white", outline="#d0d8e2")
        self.poly([(-5, 12), (5, 12), (8, 44), (0, 54), (-8, 44)], g="b", fill="#f29db4", outline="#d8798f")
        self.line([(-17, 0), (0, 9), (17, 0)], w=4, color="#f29db4", g="b", smooth=False)
        self.oval(-4, 8, 4, 16, g="b", fill="#f2c94c", outline="#c9a227")
        # brazo derecho con tablet
        self.oval(30, 24, 50, 46, g="b", fill=FUR, outline=DK)
        self.tab = self.rect(40, 26, 72, 52, g="b", fill=BUTTER, outline=DK)
        self.text(56, 39, "</>", 7, INK, g="b")
        # brazo izquierdo (saluda)
        self.oval(-50, 24, -30, 46, g="lp", fill=FUR, outline=DK)
        self.line([(-43, 38), (-43, 43)], w=1.5, color=DK, g="lp")
        self.line([(-37, 38), (-37, 43)], w=1.5, color=DK, g="lp")
        # orejas
        sad = mood == "sad"
        self.bL = [(-42, -60), (-56, -92), (-12, -74)] if sad else [(-42, -60), (-38, -104), (-10, -76)]
        self.iL = [(-37, -67), (-47, -86), (-19, -76)] if sad else [(-36, -68), (-34, -94), (-18, -78)]
        self.bR = [(-x, y) for x, y in self.bL]
        self.iR = [(-x, y) for x, y in self.iL]
        self.eL = self.poly(self.bL, g="h", fill=FUR, outline=DK)
        self.eLi = self.poly(self.iL, g="h", fill="#f7c6cf")
        self.eR = self.poly(self.bR, g="h", fill=FUR, outline=DK)
        self.eRi = self.poly(self.iR, g="h", fill="#f7c6cf")
        # cabeza
        self.oval(-46, -88, 46, -8, g="h", fill=FUR, outline=DK, width=2)
        for dx in (-14, 0, 14):
            self.line([(dx, -87), (dx * 0.85, -75)], w=3, color=DK, g="h")
        if peluca:
            for wx, wy in ((-34, -90), (-17, -98), (0, -100), (17, -98), (34, -90)):
                self.oval(wx - 13, wy - 8, wx + 13, wy + 14, g="h", fill="#fdfbff", outline="#cfc6d8", width=1.5)
        self.oval(-16, -36, 0, -20, g="h", fill=LT, outline="")
        self.oval(0, -36, 16, -20, g="h", fill=LT, outline="")
        # ojos
        if mood == "happy":
            self.line([(-30, -48), (-21, -60), (-12, -48)], w=3, g="h", smooth=False)
            self.line([(12, -48), (21, -60), (30, -48)], w=3, g="h", smooth=False)
            self.oval(-43, -38, -28, -27, g="h", fill="#f7b5bf", outline="")
            self.oval(28, -38, 43, -27, g="h", fill="#f7b5bf", outline="")
        else:
            for ex in (-22, 22):
                self.oval(ex - 9, -62, ex + 9, -38, g=("h", "eo"), fill="#8fd0a4", outline=INK, width=1.5)
                self.oval(ex - 3.5, -58, ex + 3.5, -42, g=("h", "eo", "pu"), fill=INK, outline="")
                self.oval(ex - 6, -58, ex - 2, -54, g=("h", "eo", "pu"), fill="white", outline="")
                self.line([(ex - 10, -50), (ex, -47), (ex + 10, -50)], w=3, g=("h", "ec"), smooth=False, state="hidden")
            if sad:
                self.line([(-32, -66), (-14, -60)], w=3, g="h")
                self.line([(32, -66), (14, -60)], w=3, g="h")
                self.oval(-28, -36, -22, -28, g=("h", "tear"), fill="#8fd0f2", outline="")
        self.poly([(-5, -38), (5, -38), (0, -32)], g="h", fill="#f2899f")
        if mood == "happy":
            self.poly([(-10, -29), (-6, -17), (0, -14), (6, -17), (10, -29)], g="h", smooth=False,
                      fill="#d4707f", outline=DK)
            self.oval(-4, -22, 4, -15, g="h", fill="#f7a1ae", outline="")
        elif sad:
            self.line([(-10, -20), (0, -28), (10, -20)], w=2, g="h", smooth=False)
        else:
            self.line([(-12, -28), (-6, -22), (0, -30), (6, -22), (12, -28)], w=2, g="h", smooth=False)
        # bigotes
        self.wh = []
        for sg in (-1, 1):
            for y0, y1 in ((-36, -42), (-30, -28)):
                it = self.line([(sg * 46, y0), (sg * 74, y1)], w=1.5, color=DK, g="h")
                self.wh.append((it, sg, y0, y1))
        self.update(time.time())

    def update(self, t):
        s, m = self.s, self.mood
        resp = math.sin(t * 2.4)
        sal = abs(math.sin(t * 5)) * 18 * s if self.salto else 0
        self.mover("", 0, -sal)
        self.mover("b", 0, resp * s)
        self.mover("h", 0, resp * 1.8 * s)
        a = math.sin(t * (6.5 if m == "happy" else 3.0)) * (0.3 if m == "sad" else 1.0)
        self.setpts(self.tail, [(34, 48), (62, 46 + a * 3), (74 + a * 8, 16 + a * 6), (64 + a * 14, -12 + a * 3)], "b")
        if m == "happy":
            self.mover("lp", -8 * s, (-34 + math.sin(t * 10) * 7) * s)
        else:
            self.mover("lp", 0, resp * s)
        if m != "happy":
            self.parpadeo((t % 3.6) > 3.45)
            self.mover("pu", math.sin(t * 0.8) * 2.2 * s, 0)
        if m == "sad":
            self.mover("tear", 0, ((t * 16) % 26) * s)
        # orejas
        f, f2 = t % 4.3, (t + 1.7) % 5.7
        tw = 7 * math.sin(f / 0.3 * math.pi) if f < 0.3 else 0
        tw2 = 7 * math.sin(f2 / 0.3 * math.pi) if f2 < 0.3 else 0
        if m == "happy":
            tw += math.sin(t * 6) * 1.5
            tw2 += math.sin(t * 6 + 1) * 1.5
        k = (round(tw, 1), round(tw2, 1))
        if self.cambio("ears", k):
            for it, base, d in ((self.eL, self.bL, tw), (self.eLi, self.iL, tw), (self.eR, self.bR, -tw2),
                                (self.eRi, self.iR, -tw2)):
                self.setpts(it, [base[0], (base[1][0] - d * 0.6, base[1][1] + abs(d) * 0.5), base[2]], "h")
        wob = math.sin(t * 2.2) * 2
        for it, sg, y0, y1 in self.wh:
            self.setpts(it, [(sg * 46, y0), (sg * 74, y1 + wob * (1 if y0 < -33 else -1))], "h")
        if self.cambio("tab", int(t * 1.4) % 2):
            self.c.itemconfigure(self.tab, fill=BUTTER if self.est["tab"] else "#fff3c8")


class MouseActor(Actor):
    """Enemigos: ratones tecnológicos. kind: troll | auditor | hacker | algo"""

    def __init__(self, c, cx, cy, s=1.0, kind="troll", hurt=False, extra=()):
        super().__init__(c, cx, cy, s, extra)
        self.kind, self.hurt = kind, hurt
        skin = {"troll": "#a9dcb1", "auditor": "#ddd7e8", "hacker": "#c3c5da", "algo": "#c9d4de"}[kind]
        body = {"troll": "#bcaee3", "auditor": "#fffdf7", "hacker": "#7b7c9f", "algo": "#a3b4c6"}[kind]
        DK = "#7a6656"
        self.tail = self.line([(-34, 50), (-58, 56), (-74, 44), (-84, 24)], w=5, color="#f4a9bf", g="b", smooth=False)
        for x1 in (-26, 8):
            self.oval(x1, 66, x1 + 20, 82, fill=skin, outline=DK)
        self.oval(-36, -8, 36, 72, g="b", fill=body, outline=DK)
        self.oval(-22, 10, 22, 64, g="b", fill=mix(body, "#ffffff", 0.35), outline="")
        self.oval(-48, 22, -30, 46, g="b", fill=skin, outline=DK)
        self.oval(30, 22, 48, 46, g="b", fill=skin, outline=DK)
        if kind == "auditor":
            self.poly([(-4, 8), (4, 8), (6, 36), (0, 44), (-6, 36)], g="b", fill=CORAL, outline=DK)
        if kind == "hacker":
            self.rect(-34, 34, 34, 62, g="b", fill="#3f3f5e", outline=DK, width=2)
            self.lt = self.text(0, 48, ">_ 0101", 8, "#b9f0c8", g="b")
        if kind == "algo":
            self.rect(-22, 8, 22, 40, g="b", fill="#6c7a8d", outline=DK, width=2)
            self.text(0, 24, "0101", 8, "#d9f5e0", g="b")
        # orejas
        self.oval(-56, -100, -12, -56, g=("h", "ea"), fill=skin, outline=DK)
        self.oval(-48, -92, -20, -64, g=("h", "ea"), fill="#f7c6cf", outline="")
        self.oval(12, -100, 56, -56, g=("h", "eb"), fill=skin, outline=DK)
        self.oval(20, -92, 48, -64, g=("h", "eb"), fill="#f7c6cf", outline="")
        self.oval(-42, -84, 42, -4, g="h", fill=skin, outline=DK, width=2)
        if kind == "troll":
            self.poly([(-30, -78), (-24, -108), (-14, -82), (-6, -114), (2, -82), (12, -110),
                       (18, -80), (28, -102), (32, -76)], g="h", fill="#f4a6c0", outline=DK)
        if kind == "hacker":
            self.poly([(-46, -58), (-36, -96), (0, -104), (36, -96), (46, -58), (34, -50), (-34, -50)],
                      g="h", fill="#7b7c9f", outline=DK, width=2)
        if kind == "algo":
            self.line([(0, -84), (0, -108)], w=3, color=DK, g="h")
            self.led = self.oval(-6, -118, 6, -106, g="h", fill=CORAL, outline=DK)
            self.rect(-38, -70, 38, -36, g="h", fill="#6c7a8d", outline=DK, width=2)
            if hurt:
                self.text(0, -53, "x   x", 12, "#ffffff", g="h")
            else:
                self.oval(-26, -62, -10, -44, g=("h", "pu"), fill="#ffd3d0", outline="")
                self.oval(10, -62, 26, -44, g=("h", "pu"), fill="#ffd3d0", outline="")
        else:
            if hurt:
                for ox in (-21, 21):
                    self.line([(ox - 7, -58), (ox + 7, -44)], w=3, g="h")
                    self.line([(ox - 7, -44), (ox + 7, -58)], w=3, g="h")
            else:
                for ox in (-21, 21):
                    self.oval(ox - 9, -60, ox + 9, -42, g=("h", "eo"), fill="white", outline=DK)
                    self.oval(ox - 4, -55, ox + 4, -47, g=("h", "eo", "pu"), fill=INK, outline="")
                    self.oval(ox - 3, -54, ox, -51, g=("h", "eo", "pu"), fill="white", outline="")
                    self.line([(ox - 9, -51), (ox + 9, -51)], w=3, g=("h", "ec"), state="hidden")
            self.line([(-34, -70), (-10, -60)], w=3, g="h")
            self.line([(34, -70), (10, -60)], w=3, g="h")
        self.oval(-6, -34, 6, -24, g="h", fill="#f2899f", outline="")
        if hurt:
            self.line([(-14, -14), (-7, -20), (0, -14), (7, -20), (14, -14)], w=2, g="h", smooth=False)
        else:
            self.line([(-16, -18), (-8, -11), (0, -18), (8, -11), (16, -18)], w=2, g="h")
            self.rect(-5, -14, 0, -6, g="h", fill="white", outline=DK)
            self.rect(0, -14, 5, -6, g="h", fill="white", outline=DK)
        self.wh = []
        for sg in (-1, 1):
            for y0, y1 in ((-30, -36), (-24, -22)):
                it = self.line([(sg * 42, y0), (sg * 68, y1)], w=1.5, color=DK, g="h")
                self.wh.append((it, sg, y0, y1))
        # accesorios
        if kind == "troll":
            self.rect(22, 22, 82, 54, g="ac", fill=BUTTER, outline=DK)
            self.text(52, 38, "FAKE\nNEWS", 7, INK, g="ac")
        elif kind == "auditor":
            for ox in (-21, 21):
                self.oval(ox - 15, -64, ox + 15, -38, g="h", outline=INK, width=3, fill="")
            self.line([(-6, -51), (6, -51)], w=3, g="h")
            self.oval(44, 14, 72, 42, g="ac", outline=GOLD, width=3, fill="")
            self.line([(68, 40), (82, 58)], w=4, color=GOLD, g="ac")
        self.update(time.time())

    def update(self, t):
        s, k = self.s, self.kind
        dt = time.time() - self.t0
        resp = math.sin(t * 2.6)
        sh = 3 * s * math.exp(-2.5 * dt) * math.sin(dt * 45) if self.hurt else 0.0
        self.mover("b", sh * 0.6, resp * s)
        self.mover("h", sh, resp * 1.8 * s)
        a = math.sin(t * 2.8)
        self.setpts(self.tail, [(-34, 50), (-58, 56), (-74 + a * 4, 44 + a * 6), (-84 + a * 10, 24 + a * 5)], "b")
        self.mover("ea", math.sin(t * 3.1) * 1.5 * s, 0)
        self.mover("eb", math.sin(t * 3.1 + 1.3) * 1.5 * s, 0)
        if not self.hurt:
            if k == "algo":
                self.mover("pu", math.sin(t * 2.2) * 8 * s, 0)
                if self.cambio("led", int(t * 2) % 2):
                    self.c.itemconfigure(self.led, fill=CORAL if self.est["led"] else "#ffffff")
            else:
                self.parpadeo((t % 3.1) > 2.96)
                self.mover("pu", math.sin(t * 1.1) * 2 * s, 0)
        wob = math.sin(t * 2.6) * 2
        for it, sg, y0, y1 in self.wh:
            self.setpts(it, [(sg * 42, y0), (sg * 68, y1 + wob * (1 if y0 < -27 else -1))], "h")
        if k == "troll":
            self.mover("ac", math.sin(t * 2) * 2 * s, math.sin(t * 4) * 3 * s)
        elif k == "auditor":
            self.mover("ac", math.sin(t * 2.5) * 5 * s, math.cos(t * 2.5) * 3 * s)
        elif k == "hacker":
            i = int(t * 3) % 4
            if self.cambio("lt", i):
                self.c.itemconfigure(self.lt, text=["> _0101", "> 1010_", "> _1101", "> 0110_"][i])



# ======================================================================
#                  GATÓPOLIS · CONTENIDO EDUCATIVO
# ======================================================================
RETARDO = 900          # ms entre mensajes del chat

DIST = [
    {"n": "Casa de la Moral", "modo": "Historia en chat", "u": "I", "col": SKY, "enem": "troll",
     "tema": "Fundamentos de la Ética en TIC"},
    {"n": "Oficina de Datos", "modo": "Inspección de oficina", "u": "II", "col": LAV, "enem": "auditor",
     "tema": "Datos Personales y Derecho de la Propiedad"},
    {"n": "Tribunal Gatuno", "modo": "Juicio: ¿falta, infracción o delito?", "u": "III", "col": MINT,
     "enem": "hacker", "tema": "Delitos Informáticos"},
    {"n": "Laboratorio de Lanzamiento", "modo": "Revisión de cumplimiento", "u": "IV", "col": PEACH,
     "enem": "algo", "tema": "Aplicaciones de la Ética y la Legislación en TIC"},
]
RANGOS = ["Gatito Becario", "Gato Junior", "Gato Dev", "Gato Auditor Tech", "Gato Estratega"]
PERSONAS = {"Luis": SKY, "Ana": PINK, "Beto": BUTTER, "Chuy": MINT, "Jefa Mora": LAV, "Dir. Tigre": PEACH}

AVISO_G = """AVISO DE PRIVACIDAD SIMPLIFICADO
Responsable: {a}.
Datos que se recaban: un alias (opcional) y tu progreso en el juego (puntos, estrellas y mejores respuestas).
Finalidad: continuar tu partida y mostrar tus resultados y tu álbum.
Almacenamiento: SOLO si aceptas, en el archivo local gatopolis_progreso.json de esta computadora. No se envía nada por internet.
Transferencias: ninguna.
Derechos ARCO (Acceso, Rectificación, Cancelación y Oposición): desde Ajustes puedes cambiar tu alias o borrar todo tu progreso; también puedes eliminar el archivo o contactar al responsable.
Si no aceptas, puedes jugar normalmente y no se guardará nada."""

TERMINOS_G = """TÉRMINOS DE USO Y LICENCIA
• Juego con fines educativos; no constituye asesoría legal. Verifica siempre la normatividad vigente.
• Código fuente: licencia MIT. Textos y escenarios: Creative Commons BY-SA 4.0.
• Atribuciones: no se usan imágenes, audio ni bibliotecas de terceros. Los gráficos (gatos, ratones, ciudad) se dibujan por código; solo se usa la biblioteca estándar de Python (tkinter). Los fundamentos jurídicos provienen de las normas citadas en las referencias.
• Personajes, empresas y situaciones son ficticios."""

INSTRUCCIONES_G = """OBJETIVO
Michi, un gato desarrollador, debe cuidar Gatópolis, la ciudad de los gatos digitales. Cada distrito representa una unidad del programa E-ELTI-3 y tiene su propio modo de juego.

LOS 4 DISTRITOS
• I · CASA DE LA MORAL (historia en chat): lee la conversación del equipo y responde como Michi en 8 escenas. Tus decisiones suben o bajan Ética, Legal y Confianza.
• II · OFICINA DE DATOS (inspección): recorre la oficina y haz clic en los 9 objetos sospechosos; decide qué norma se vulnera y qué hacer. Tienes 2 pistas.
• III · TRIBUNAL GATUNO (juicio): eres la jueza Michi. Clasifica 10 expedientes (de un total de 17) como falta ética, infracción o delito y revisa sanción y prevención.
• IV · LABORATORIO DE LANZAMIENTO (revisión): responde Sí o No a 22 puntos del checklist de cumplimiento de la app MichiShop y lánzala.

PUNTOS, ESTRELLAS Y TEMARIO
• Cada decisión vale hasta 10 pts y recibe retroalimentación inmediata con su fundamento ético o legal.
• Estrellas por distrito según tu mejor partida: 60% = 1, 80% = 2, 90% = 3 (12 en total).
• El TEMARIO muestra qué temas del programa ya dominas (✓), cuáles vas a medias (~) y cuáles faltan (○).
• El ÁLBUM guarda una huellita con el fundamento de cada decisión correcta.
• El CERTIFICADO resume tu desempeño con la escala por competencias."""

INTRO = [
    "UNIDAD I · FUNDAMENTOS DE LA ÉTICA EN TIC\n\nMoral: valores y costumbres de una persona o grupo. Valores: lo que consideramos importante (honestidad, respeto). Principios: reglas generales que orientan la conducta. Dilema ético: cuando dos valores chocan y hay que elegir. Ética: reflexión crítica sobre todo ello. Derecho: normas obligatorias con sanción. Algo puede ser legal y no ético.\n\nElementos éticos fundamentales de las TIC: privacidad, seguridad, responsabilidad, propiedad intelectual y acceso equitativo.\n\nCómo se juega: estás en el chat del equipo (un juego de roles de situaciones que viven empleados y usuarios de TI). Usa la Brújula ética: identifica el dilema, ubica a los afectados, revisa normas y la ley, y decide. Son 8 escenas.",
    "UNIDAD II · DATOS PERSONALES Y DERECHO DE LA PROPIEDAD\n\nMarco constitucional: Art. 6° (derecho a la información), Art. 7° (libertad de difusión), Art. 8° (derecho de petición) y Art. 16 (privacidad y datos personales, derechos ARCO). Régimen jurídico en México: LFPDPPP (datos personales), LFDA (derechos de autor), LFPPI (propiedad industrial) y las normas de transparencia.\n\nCómo se juega: recorre la oficina e inspecciona los 9 objetos sospechosos. Haz clic en cada uno, decide qué hacer y revisa el fundamento. Pasa el cursor sobre los objetos para resaltarlos; si te atoras, usa una pista.",
    "UNIDAD III · DELITOS INFORMÁTICOS\n\nFalta ética: daña valores, pero no tiene sanción legal directa. Infracción: sanción administrativa o civil (PROFECO, IMPI, autoridad de datos). Delito: conducta tipificada en leyes penales (Código Penal Federal, Ley Olimpia): contra el patrimonio (estafa, defraudación, daño), contra la propiedad intelectual o con las TI como medio. Marcos internacionales: Convenio de Budapest (2001); IA: UNESCO (2021) y Reglamento de IA de la UE (2024).\n\nCómo se juega: eres la jueza Michi. Cada expediente debe clasificarse como falta ética, infracción o delito (10 de 17 expedientes). Cada veredicto explica el fundamento, la sanción y la prevención (cumplimiento normativo).",
    "UNIDAD IV · APLICACIONES DE LA ÉTICA Y LA LEGISLACIÓN EN TIC\n\nInvestigación en línea y redes sociales: consentimiento, anonimización y normas de uso. Propiedad industrial, licenciamiento y derechos de autor: marcas, patentes, copyright y copyleft (GPL, MIT). Comercio electrónico y protección al consumidor: Código de Comercio y LFPC (Art. 76 bis). IA y ética: sesgos algorítmicos, discriminación y privacidad.\n\nCómo se juega: vas a lanzar la app MichiShop. Revisa las 4 pestañas y decide Sí o No en cada punto del checklist (22 puntos). Cada decisión te da retroalimentación al instante. Cuando termines, pulsa Lanzar app.",
]

# ---------------------------------------------------------------- D1: chat
# opción: (texto, puntos, dÉtica, dLegal, dConfianza, consecuencia)
CHAT = [
    {"id": "plagio", "t": "Plagio en el repositorio", "canal": "#equipo-michitech",
     "msgs": [("Luis", "Terminé el módulo de login. Lo copié casi igual de un repo público; ni revisé la licencia."),
              ("Ana", "Funciona y la entrega es mañana… no compliquemos."),
              ("Luis", "Nadie se va a dar cuenta, ¿verdad, Michi?")],
     "o": [("Mejor lo hablamos: lo reescribimos o lo atribuimos y revisamos la licencia antes de entregar.", 10, 10, 8, 5,
            "Resuelves el problema desde la raíz y proteges al equipo."),
           ("Tranquilo, el módulo funciona. Entreguémoslo así.", 0, -15, -10, -5,
            "Participas por omisión en un plagio. Si el autor original reclama, el riesgo recae en todo el equipo."),
           ("Voy a exhibir esto en el grupo general de la empresa.", 4, -5, 0, -10,
            "El fondo es correcto, pero la forma humilla a un compañero. Primero se dialoga y se corrige.")],
     "f": "Plagiar es presentar como propia una obra ajena. Éticamente vulnera la honestidad y la integridad profesional; jurídicamente puede violar derechos morales (atribución) y patrimoniales de la LFDA.",
     "e": "Deontológico (deber de honestidad) y ética de virtudes (integridad)."},
    {"id": "acoso", "t": "Chat tóxico", "canal": "#memes-oficina",
     "msgs": [("Beto", "Miren el meme nuevo de Lupita y su acento, jajaja."),
              ("Chuy", "Y lo de su peso… ¡qué risa!"),
              ("Sistema", "Lupita salió del grupo.")],
     "o": [("Apoyo a Lupita, guardo la evidencia y lo reporto al comité o a Recursos Humanos.", 10, 10, 8, 8,
            "Actúas con empatía y por la vía institucional, con evidencia."),
           ("Ignorarlo: son bromas y no es mi problema.", 0, -15, -5, -10,
            "El silencio normaliza el ciberacoso y deteriora el ambiente de trabajo."),
           ("Respondo con otro meme para aligerar el ambiente.", 1, -15, -5, -5,
            "Terminas sumándote al acoso.")],
     "f": "El ciberacoso es acoso mediante medios digitales. En el ámbito laboral se vincula con la NOM-035-STPS-2018 (riesgos psicosociales) y con el derecho a un trato libre de discriminación (Art. 1° constitucional).",
     "e": "Ética del cuidado (proteger a quien es vulnerable) y utilitarista (evitar un daño mayor al clima laboral)."},
    {"id": "bots", "t": "Campaña con bots", "canal": "#marketing",
     "msgs": [("Jefa Mora", "Michi, necesito 50 cuentas falsas que difundan reseñas positivas y rumores de la competencia."),
              ("Jefa Mora", "Es solo marketing. ¿Lo tienes para el viernes?")],
     "o": [("No lo haré, pero propongo una campaña con reseñas reales y publicidad veraz.", 10, 10, 8, 8,
            "Defiendes la veracidad y ofreces una alternativa viable."),
           ("Está bien, jefa. Lo hago para el viernes.", 0, -20, -15, -10,
            "Fabricas desinformación y reseñas engañosas; expones a la empresa a sanciones y a perder su reputación."),
           ("Hago solo las reseñas positivas, sin rumores.", 3, -10, -8, -5,
            "Reducir el daño no lo hace ético: las reseñas falsas siguen engañando al consumidor.")],
     "f": "La desinformación y las reseñas falsas afectan la confianza pública y pueden ser publicidad engañosa (Ley Federal de Protección al Consumidor). Un profesional TI puede objetar y proponer alternativas.",
     "e": "Deontológico (no mentir ni manipular) y utilitarista (la desinformación daña a muchas personas)."},
    {"id": "legal", "t": "¿Legal pero ético?", "canal": "#dirección",
     "msgs": [("Dir. Tigre", "Encontré una laguna: ninguna norma prohíbe revender hábitos de uso de menores 'anonimizados'."),
              ("Dir. Tigre", "Es legal y deja buenas ganancias. ¿Algún problema, Michi?")],
     "o": [("Sí: no lo hagamos. Propongo anonimización robusta y una política de datos de menores.", 10, 10, 8, 10,
            "Aplicas el principio de precaución y el interés superior de la niñez."),
           ("Si es legal, adelante.", 1, -15, -5, -15,
            "Confundes ética con legalidad. Una reidentificación pondría en riesgo a menores y a la empresa."),
           ("Consultemos a Legal y hagamos lo que digan.", 5, 0, 5, 0,
            "Legal responde por la ley, pero el dilema ético sigue siendo tu responsabilidad profesional.")],
     "f": "La ley fija mínimos; la ética exige más. Los códigos profesionales (ACM, IEEE) piden evitar daño, proteger la privacidad y considerar a los grupos vulnerables, aun sin prohibición expresa.",
     "e": "Principio de precaución y ética de virtudes: lo legal no siempre es ético."},
    {"id": "discrim", "t": "Formulario discriminatorio", "canal": "#reclutamiento",
     "msgs": [("Ana", "En el formulario de empleo pedimos edad, estado civil y si planean tener hijos."),
              ("Ana", "Así filtramos rápido a quienes 'no rinden'. ¿Lo programamos así?")],
     "o": [("Propongo quitar esas preguntas y evaluar solo competencias para el puesto.", 10, 10, 10, 8,
            "Promueves la igualdad de oportunidades y reduces el riesgo legal."),
           ("Sí, ahorra tiempo. Lo programo.", 0, -15, -12, -8,
            "Discriminas por motivos prohibidos y expones a la empresa a quejas y sanciones."),
           ("Quitemos solo la pregunta de los hijos.", 5, 2, 3, 2,
            "Mejoras, pero edad y estado civil también discriminan si no son requisito del puesto.")],
     "f": "El Art. 1° de la CPEUM prohíbe discriminar por edad, género, estado civil y otros motivos; la Ley Federal para Prevenir y Eliminar la Discriminación lo desarrolla. En software aplica la minimización: no captures datos que no necesitas.",
     "e": "Ética de la justicia: igualdad de oportunidades."},
    {"id": "acceso", "t": "Acceso equitativo", "canal": "#producto",
     "msgs": [("Ana", "Nuestra app de trámites solo funciona en teléfonos nuevos y con internet rápido."),
              ("Beto", "Con lectores de pantalla se traba, pero no es prioridad. Lancemos así."),
              ("Ana", "¿Tú qué opinas, Michi?")],
     "o": [("Propongo una versión ligera y accesible (lectores de pantalla, poco consumo de datos) antes de lanzar.", 10, 10, 8, 10,
            "Amplías el acceso equitativo: más personas pueden usar el servicio."),
           ("Lancemos así; luego vemos si alguien se queja.", 0, -12, -5, -10,
            "Excluyes a personas con discapacidad o con poca conectividad y reproduces la brecha digital."),
           ("Hagamos solo la versión para lector de pantalla; lo demás no importa.", 5, 3, 2, 2,
            "Ayudas a un grupo, pero la brecha por equipo e internet sigue sin atenderse.")],
     "f": "El acceso equitativo implica que la tecnología pueda ser usada por todas las personas, sin importar discapacidad, ingresos o ubicación. Se vincula con el derecho de acceso a las TIC (Art. 6° constitucional) y con los principios de inclusión y no discriminación.",
     "e": "Ética de la justicia (igualdad de oportunidades) y utilitarista (beneficio para el mayor número de personas)."},
    {"id": "software", "t": "Entrega con vulnerabilidad", "canal": "#desarrollo",
     "msgs": [("Jefa Mora", "El cliente quiere la app mañana. Sé que la prueba de seguridad falló, pero no hay tiempo."),
              ("Luis", "Podemos corregirlo después del lanzamiento, ¿no?"),
              ("Jefa Mora", "Michi, eres la desarrolladora principal. ¿Entregamos?")],
     "o": [("Informo el riesgo por escrito, propongo corregir lo crítico antes de entregar y negociar una fecha realista.", 10, 10, 8, 8,
            "Actúas con responsabilidad profesional: proteges a los usuarios y documentas el riesgo."),
           ("Entreguemos; ya lo arreglamos después.", 0, -15, -10, -10,
            "Pones en riesgo datos de las personas usuarias y la responsabilidad recae en el equipo."),
           ("Entrego, pero sin avisarle al cliente de la falla.", 1, -20, -12, -15,
            "Ocultar una vulnerabilidad conocida es faltar a la honestidad y puede generar responsabilidad legal.")],
     "f": "La ética en el desarrollo de software exige calidad, seguridad y honestidad con el cliente. Los códigos de ética de ACM e IEEE piden evitar el daño, ser honestos y asumir la responsabilidad profesional por los riesgos de lo que se construye.",
     "e": "Deontológico (deber profesional) y ética de virtudes (responsabilidad e integridad)."},
    {"id": "politica", "t": "Políticas y procedimientos", "canal": "#ti-interno",
     "msgs": [("Chuy", "Guardé la base de clientes en mi Drive personal para trabajar desde casa."),
              ("Ana", "La empresa no tiene política de uso de recursos ni sabe qué hacer en estos casos."),
              ("Chuy", "Todos lo hacen. ¿Cuál es el problema, Michi?")],
     "o": [("Propongo una política de uso aceptable, herramientas aprobadas, capacitación y un canal de reporte; y mover los datos hoy.", 10, 10, 10, 8,
            "El cumplimiento normativo se construye con políticas claras, procedimientos y capacitación."),
           ("No pasa nada; todos lo hacen.", 0, -10, -10, -5,
            "Normalizas un riesgo de fuga de datos personales y de información confidencial."),
           ("Sanciono a Chuy frente a todos.", 3, -5, -3, -10,
            "Sin una política previa y conocida, sancionar es arbitrario; primero se establecen reglas y procedimientos.")],
     "f": "El cumplimiento normativo requiere políticas (qué se espera), procedimientos (cómo se hace y cómo se reporta) y medidas disciplinarias conocidas por todo el personal. Además, guardar datos personales en cuentas personales vulnera las medidas de seguridad que exige la LFPDPPP.",
     "e": "Ética para empleados y usuarios de TI: legalidad, responsabilidad y justicia en los procedimientos."},
]

# valor en juego, principio y elemento ético fundamental de cada escena
VPE = {
    "plagio": ("Honestidad", "Dar crédito a quien crea una obra", "Propiedad intelectual"),
    "acoso": ("Respeto", "No dañar a otras personas", "Responsabilidad"),
    "bots": ("Veracidad", "No engañar ni manipular", "Responsabilidad"),
    "legal": ("Precaución y protección de menores", "Lo legal no siempre es ético", "Privacidad"),
    "discrim": ("Igualdad", "No discriminar", "Acceso equitativo"),
    "acceso": ("Inclusión", "Diseñar para todas las personas", "Acceso equitativo"),
    "software": ("Responsabilidad profesional", "No poner en riesgo a las personas usuarias", "Seguridad"),
    "politica": ("Integridad", "Las reglas deben ser claras y conocidas", "Responsabilidad y seguridad"),
}

# ---------------------------------------------------------------- D2: inspección
HOT = [
    {"id": "aviso", "t": "Formulario sin aviso de privacidad", "box": (268, 276, 452, 384),
     "x": "En el monitor hay un formulario que recolecta nombre, CURP, correo y diagnósticos médicos. No tiene aviso de privacidad ni casilla de consentimiento.",
     "o": [("Publicar un aviso de privacidad integral, pedir consentimiento expreso para los datos sensibles y habilitar el canal ARCO.", 10,
            "Cumples transparencia, finalidad y consentimiento, y habilitas los derechos ARCO."),
           ("Lanzar así y agregar el aviso si alguien reclama.", 0,
            "Recabas datos, incluso sensibles, sin informar finalidades ni obtener consentimiento."),
           ("Copiar el aviso de privacidad de otra empresa.", 3,
            "El aviso debe reflejar TUS datos, finalidades y responsable; copiarlo puede hacerlo inexacto e ilegal.")],
     "f": "La LFPDPPP exige informar mediante aviso de privacidad, obtener consentimiento (expreso para datos sensibles como salud), proteger los datos con medidas de seguridad y atender solicitudes ARCO. Se vincula con el Art. 16 constitucional."},
    {"id": "peticion", "t": "Petición sin respuesta", "box": (858, 98, 1042, 202),
     "x": "En el buzón hay un escrito de una asociación civil dirigido a una dependencia pública que asesoras. Lleva 4 meses sin respuesta.",
     "o": [("Responder por escrito, de forma fundada, y notificarla a quien la presentó.", 10,
            "Respetas el Art. 8° constitucional: la autoridad debe responder por escrito y en breve término."),
           ("Ignorarla: no es obligatorio contestar.", 0,
            "Violas el derecho de petición; la autoridad debe responder."),
           ("Responder solo por teléfono.", 4,
            "La petición exige respuesta por escrito y notificada al peticionario.")],
     "f": "Art. 8° CPEUM: toda petición hecha por escrito, de manera pacífica y respetuosa, obliga a la autoridad a responder por escrito y en breve término."},
    {"id": "foro", "t": "Censura en el foro", "box": (606, 96, 794, 234),
     "x": "En el corcho del foro hay una orden: «borrar toda crítica al funcionario». Las críticas son duras, pero no contienen amenazas.",
     "o": [("Mantener la crítica y moderar solo amenazas, doxxing o discurso de odio según reglas publicadas.", 10,
            "Equilibras la libertad de expresión (Arts. 6° y 7°) con límites legítimos."),
           ("Borrarlas todas: la dirección manda.", 1,
            "Censuras expresión legítima; la crítica a funcionarios goza de mayor protección."),
           ("Cerrar los comentarios para siempre.", 4,
            "Evitas el problema, pero sacrificas el debate público.")],
     "f": "La libertad de expresión no es absoluta (Art. 6°: límites por ataques a la moral, derechos de terceros, orden público o delito), pero la crítica no es delito. La moderación debe ser transparente y no arbitraria."},
    {"id": "codigo", "t": "Auditoría de código", "box": (476, 306, 606, 384),
     "x": "Revisas un pull request en la laptop. Este es el fragmento:",
     "code": "db_pass = \"admin123\"\nq = \"SELECT * FROM pacientes WHERE correo='\" + correo + \"'\"\nlog.write(paciente.curp + paciente.tarjeta)",
     "o": [("Rechazar: secretos fuera del código, consultas parametrizadas, no registrar CURP/tarjeta y cifrar datos sensibles.", 10,
            "Auditoría correcta: seguridad por diseño y minimización de datos."),
           ("Aprobar: pasa las pruebas funcionales.", 0,
            "Aprobaste vulnerabilidades y un registro en claro de datos personales y financieros."),
           ("Corregir solo la consulta SQL.", 4,
            "Arreglas la inyección SQL, pero dejas la contraseña expuesta y los datos en claro.")],
     "f": "La LFPDPPP exige medidas de seguridad administrativas, técnicas y físicas. Una revisión de código es una medida preventiva: evita fugas y responsabilidad legal del responsable del tratamiento."},
    {"id": "pizarra", "t": "¿Patente, autor o secreto?", "box": (256, 96, 564, 244),
     "x": "En la pizarra está el algoritmo de recomendación y el boceto de la app y su nombre comercial. El equipo quiere protegerlos.",
     "o": [("Código e interfaz: derecho de autor (LFDA); nombre: marca (LFPPI); algoritmo: secreto industrial con acuerdos de confidencialidad.", 10,
            "Identificas correctamente cada figura jurídica."),
           ("Registrar todo como patente: es la protección más fuerte.", 2,
            "Los programas de computación en sí mismos no son patentables; el código se protege por derecho de autor."),
           ("No hace falta nada: el derecho de autor surge solo si se paga el registro.", 3,
            "La protección autoral nace con la creación; el registro ayuda a probar la titularidad, no la crea.")],
     "f": "LFDA: derechos morales (inalienables) y patrimoniales; protege programas de cómputo. LFPPI: patentes, marcas y secretos industriales. No confundas patente con derecho de autor."},
    {"id": "info", "t": "Información pública negada", "box": (46, 246, 204, 454),
     "x": "El archivero guarda el contrato de videovigilancia de la dependencia. Un ciudadano pidió copia por escrito y tu jefe quiere negarla sin dar razones.",
     "o": [("Entregar la información pública y reservar solo lo que la ley permita, explicando el fundamento.", 10,
            "Respetas el derecho de acceso a la información y proteges lo que sí es reservado."),
           ("Negarla sin fundamentar.", 0,
            "Violas el derecho de acceso a la información (Art. 6°); toda negativa debe fundarse y motivarse."),
           ("Entregarla completa, incluidos datos personales de terceros.", 4,
            "Exponer datos personales de terceros vulnera el Art. 16; hay que testarlos.")],
     "f": "Art. 6° CPEUM: la información en poder de las autoridades es pública y solo se reserva en casos previstos por la ley (Ley General de Transparencia y Acceso a la Información Pública). Los datos personales de terceros se protegen (Art. 16)."},
    {"id": "autor", "t": "Imagen sin atribución", "box": (856, 220, 1044, 356),
     "x": "El cuadro de la pared es una ilustración descargada de internet, sin atribución ni licencia. El equipo planea usarla en la app.",
     "o": [("Verificar la licencia (por ejemplo, Creative Commons), pedir autorización o usar un recurso con licencia y dar atribución.", 10,
            "Respetas los derechos morales y patrimoniales del autor."),
           ("Usarla: si está en internet, es libre.", 0,
            "Que algo esté en internet no lo vuelve libre; la obra sigue protegida."),
           ("Cambiarle un poco los colores para que no se note.", 1,
            "Modificarla sin autorización también viola derechos del autor.")],
     "f": "LFDA: las obras están protegidas desde su creación. El autor tiene derechos morales (reconocimiento e integridad) y patrimoniales (explotación). Usa licencias abiertas y da siempre la atribución que pidan."},
    {"id": "camara", "t": "Cámara de reconocimiento facial", "box": (46, 96, 214, 232),
     "x": "En la entrada hay una cámara con reconocimiento facial que registra a todas las personas, incluidas las visitas. Nadie fue informado y no hay letrero.",
     "o": [("Informar con un aviso de videovigilancia visible, limitar la finalidad y el tiempo de conservación, y proteger las imágenes.", 10,
            "El rostro es un dato personal: debe tratarse con aviso, finalidad definida, proporcionalidad y seguridad."),
           ("Dejarla así: es por seguridad y nadie se queja.", 0,
            "Que haya un fin de seguridad no elimina el deber de informar ni de tratar solo lo necesario."),
           ("Poner un letrero que diga «Cámaras» y guardar los videos para siempre.", 4,
            "El letrero ayuda, pero conservar datos sin límite incumple los principios de finalidad y proporcionalidad.")],
     "f": "La privacidad protege la vida privada (Art. 16 CPEUM). Las imágenes y los datos biométricos, como el rostro, son datos personales y requieren aviso de privacidad, finalidad legítima, proporcionalidad y medidas de seguridad (LFPDPPP)."},
    {"id": "arco", "t": "Solicitud de cancelación de datos", "box": (880, 366, 1040, 424),
     "x": "En la tablet de atención llegó el mensaje de un cliente: «Quiero que borren mis datos y que dejen de usarlos para publicidad». Nadie lo ha respondido.",
     "o": [("Atender su solicitud ARCO: verificar su identidad, cancelar u oponerse al uso según corresponda y responderle por escrito en los plazos legales.", 10,
            "Ejerces los derechos ARCO (cancelación y oposición) y cumples con el principio de responsabilidad."),
           ("Ignorarla: ya aceptó el aviso al registrarse.", 0,
            "Los titulares pueden ejercer sus derechos ARCO en cualquier momento; ignorarlos es una infracción."),
           ("Responder que no se puede borrar nada, sin explicar por qué.", 3,
            "Si una cancelación no procede (por ejemplo, por una obligación legal de conservar datos), debe explicarse de forma fundada.")],
     "f": "Derechos ARCO: Acceso, Rectificación, Cancelación y Oposición. El responsable debe tener un procedimiento para recibirlos, verificar la identidad de la persona y responder en los plazos de la ley (LFPDPPP; Art. 16 CPEUM)."},
]

# ---------------------------------------------------------------- D3: tribunal
BINS = [("E", "FALTA ÉTICA", "Daña valores; sin sanción legal directa", LAV),
        ("I", "INFRACCIÓN", "Sanción administrativa o civil", BUTTER),
        ("D", "DELITO", "Conducta tipificada en leyes penales", CORAL)]

CARTAS = [
    {"id": "meme", "t": "Meme en el chat", "cat": "E",
     "x": "Compartes en el chat del equipo un meme que ridiculiza el acento de una compañera.",
     "f": "Es ciberacoso leve: viola el respeto y la dignidad, pero por sí solo no está tipificado como delito. Se atiende con el código de conducta y la NOM-035-STPS-2018. Si hubiera amenazas, extorsión o difusión de contenido íntimo, cambiaría a delito.",
     "s": "Medidas disciplinarias internas y reparación del daño.", "p": "Código de conducta, capacitación en convivencia digital y canal de denuncia."},
    {"id": "plagioac", "t": "Tarea copiada", "cat": "E",
     "x": "Entregas como propio un trabajo que copiaste de un compañero, con su permiso.",
     "f": "Plagio y deshonestidad académica: falta ética e infracción al reglamento escolar. No es delito si no explotas comercialmente una obra ajena.",
     "s": "Sanciones académicas según el reglamento (calificación, baja).", "p": "Citar fuentes, respetar licencias y revisar la originalidad."},
    {"id": "iasin", "t": "IA que filtra currículums", "cat": "E",
     "x": "Usas una IA para filtrar currículums sin explicar sus criterios ni revisar sesgos.",
     "f": "En México no hay una ley general específica de IA. La UNESCO (2021) recomienda transparencia, no discriminación y supervisión humana, y el Reglamento de IA de la UE lo exige en sistemas de alto riesgo. Si el sistema discrimina, puede violar el Art. 1° constitucional.",
     "s": "Riesgo reputacional y legal si discrimina; multas en la UE si aplica su reglamento.", "p": "Auditorías de sesgo, explicabilidad y revisión humana."},
    {"id": "noticia", "t": "Noticia sin verificar", "cat": "E",
     "x": "Compartes una noticia sin verificar y luego resulta falsa.",
     "f": "Desinformación no intencional: falta ética (responsabilidad de verificar). Si se hace de forma deliberada para engañar con fines comerciales, puede volverse infracción (publicidad engañosa) o incluso delito si hay fraude.",
     "s": "Corrección pública y pérdida de credibilidad.", "p": "Verificar fuentes y corregir a tiempo."},
    {"id": "sinaviso", "t": "App sin aviso de privacidad", "cat": "I",
     "x": "Lanzas una app que recaba datos de salud sin aviso de privacidad.",
     "f": "Infracción a la LFPDPPP: obliga a informar mediante aviso de privacidad y a obtener consentimiento (expreso para datos sensibles).",
     "s": "Multas y sanciones administrativas; en casos graves puede haber responsabilidad penal.", "p": "Aviso integral, consentimiento, medidas de seguridad y canal ARCO."},
    {"id": "resenas", "t": "Reseñas falsas", "cat": "I",
     "x": "Publicas reseñas falsas para que tu producto parezca mejor de lo que es.",
     "f": "Publicidad engañosa e información falsa al consumidor: infracción a la Ley Federal de Protección al Consumidor.",
     "s": "Multas y medidas correctivas de PROFECO.", "p": "Publicidad veraz y reseñas verificadas."},
    {"id": "licvenc", "t": "Licencia vencida", "cat": "I",
     "x": "Usas un software con licencia vencida en 30 equipos de la empresa.",
     "f": "Incumplimiento del contrato de licencia: responsabilidad civil e infracción en materia de derechos de autor (LFDA); el titular puede reclamar, incluso ante el IMPI.",
     "s": "Multas administrativas e indemnización por daños.", "p": "Inventario de licencias, renovación a tiempo o alternativas de software libre."},
    {"id": "ewaste", "t": "Basura electrónica", "cat": "I",
     "x": "Tiras equipos electrónicos obsoletos a la basura común, sin plan de manejo.",
     "f": "Responsabilidad ambiental: la Ley General para la Prevención y Gestión Integral de los Residuos (LGPGIR) exige manejo adecuado de residuos; hacerlo mal es infracción administrativa y puede ser delito ambiental en casos graves.",
     "s": "Multas administrativas y obligación de reparar el daño ambiental.", "p": "Planes de manejo, centros de acopio y reciclaje de residuos electrónicos."},
    {"id": "tienda", "t": "Tienda sin datos", "cat": "I",
     "x": "Vendes en línea sin datos del proveedor, sin política de cambios y sin mostrar el precio total.",
     "f": "Incumples las obligaciones de información del comercio electrónico (LFPC, Art. 76 bis; Código de Comercio).",
     "s": "Multas y medidas de PROFECO.", "p": "Publicar datos del proveedor, precio total y política de devoluciones."},
    {"id": "phishing", "t": "Phishing bancario", "cat": "D",
     "x": "Clonas el sitio de un banco y envías correos para obtener contraseñas.",
     "f": "Fraude (Art. 386 CPF) y acceso o uso ilícito de información (Arts. 211 bis CPF). Es un delito patrimonial con TI como medio.",
     "s": "Prisión y multa según el Código Penal.", "p": "Autenticación multifactor, capacitación anti-phishing y pruebas de seguridad autorizadas por escrito."},
    {"id": "piratas", "t": "Copias piratas", "cat": "D",
     "x": "Vendes copias de software pirata con fines de lucro.",
     "f": "Delito contra la propiedad intelectual: producir o vender copias sin autorización con fin de especulación comercial (Art. 424 bis CPF; LFDA).",
     "s": "Prisión y multa.", "p": "Licencias legales y control del inventario de software."},
    {"id": "acceso", "t": "Acceso al servidor ajeno", "cat": "D",
     "x": "Entras sin permiso al servidor de tu antigua empresa y copias archivos.",
     "f": "Acceso ilícito a sistemas (Arts. 211 bis 1 y ss. CPF): sanciona conocer, copiar, modificar o destruir información sin autorización.",
     "s": "Prisión y multa.", "p": "Revocar accesos al salir, bitácoras (logs) y segmentación de permisos."},
    {"id": "intimo", "t": "Video íntimo", "cat": "D",
     "x": "Difundes un video íntimo, real o manipulado, de una compañera sin su consentimiento.",
     "f": "Violación a la intimidad sexual (Ley Olimpia): delito que sanciona difundir contenido íntimo sin consentimiento, incluso manipulado.",
     "s": "Prisión y multa, además de la reparación del daño.", "p": "Educación digital, denuncia y retiro inmediato del contenido."},
    {"id": "ransom", "t": "Ransomware a un hospital", "cat": "D",
     "x": "Cifras la base de datos de un hospital y exiges un rescate.",
     "f": "Daño o destrucción de información (Arts. 211 bis CPF) y extorsión: delitos con TI como objeto y como medio.",
     "s": "Prisión y multa.", "p": "Respaldos, segmentación de red, plan de respuesta a incidentes y cooperación internacional (Convenio de Budapest)."},
    {"id": "estafa", "t": "Tienda fantasma", "cat": "D",
     "x": "Montas una tienda en línea desde otro país, cobras pedidos a clientes en México y nunca envías nada.",
     "f": "Fraude o estafa (Art. 386 CPF): engañar para obtener un lucro indebido. Al cometerse desde otro país interviene la cooperación internacional (Convenio de Budapest) para investigar y perseguir el delito.",
     "s": "Prisión y multa; la pena depende del monto defraudado.", "p": "Comprar en sitios verificados, usar pagos protegidos, denunciar ante la policía cibernética y cooperar internacionalmente."},
    {"id": "deepfake", "t": "Voz clonada del director", "cat": "D",
     "x": "Clonas con IA la voz del director y llamas a finanzas para pedir una transferencia urgente.",
     "f": "Fraude con suplantación de identidad mediante IA (deepfake de voz): delito patrimonial con TI como medio. La UNESCO (2021) y el Reglamento de IA de la UE piden transparencia y etiquetar los contenidos sintéticos.",
     "s": "Prisión y multa.", "p": "Doble verificación de transferencias, palabras clave internas y capacitación sobre deepfakes."},
    {"id": "chatbotmenores", "t": "Chatbot que recaba datos de menores", "cat": "I",
     "x": "Tu chatbot educativo recaba nombre, escuela y fotos de niñas y niños sin permiso de sus tutores.",
     "f": "Infracción a la LFPDPPP: el tratamiento de datos de menores exige especial cuidado y el consentimiento de quien ejerce la patria potestad o tutela, además de respetar el interés superior de la niñez.",
     "s": "Multas y sanciones administrativas.", "p": "Consentimiento de tutores, minimización de datos y aviso de privacidad claro."},
]

# ---------------------------------------------------------------- D4: laboratorio
LAB_TABS = ["Licencias y marcas", "Tienda en línea", "IA responsable", "Investigación y redes"]
LAB = [
    {"id": "gpl", "tab": 0, "tipo": "radio", "t": "Copyleft: GPL",
     "q": "Tu app usa una biblioteca con licencia GPL. Al distribuir tu app, ¿qué decides?",
     "opts": [("Distribuirla cerrada y sin mencionarla", 0,
               "La GPL es copyleft: lo derivado debe conservar la misma libertad. Distribuirla cerrada y ocultar la biblioteca la incumple."),
              ("GPL, licencia comercial o alternativa MIT", 10,
               "Copyright vs Copyleft: puedes liberar tu app bajo GPL, comprar licencia comercial o cambiar a una biblioteca MIT/Apache, que solo exige atribución."),
              ("Quitar sus avisos de autor", 0,
               "Eliminar avisos de autoría viola los derechos morales de atribución (LFDA) y la licencia.")]},
    {"id": "atrib", "tab": 0, "tipo": "sn", "t": "Atribución MIT/Apache", "c": True,
     "q": "¿Incluirás la atribución y la licencia de las bibliotecas MIT/Apache que usas?",
     "ok": "Las licencias permisivas piden conservar el aviso de copyright y la licencia. Cumplirlas respeta los derechos morales del autor (LFDA).",
     "bad": "Omitir la atribución incumple la licencia y vulnera el derecho moral de reconocimiento del autor (LFDA)."},
    {"id": "marca", "tab": 0, "tipo": "sn", "t": "Marcas registradas", "c": False,
     "q": "¿Usarás en tu publicidad el logotipo de otra marca registrada sin permiso?",
     "ok": "La marca registrada da derecho exclusivo de uso (LFPPI); evitarlo previene infracciones ante el IMPI.",
     "bad": "Usar una marca ajena sin autorización puede ser infracción (LFPPI) y generar responsabilidad."},
    {"id": "precio", "tab": 1, "tipo": "sn", "t": "Precio total", "c": True,
     "q": "¿Mostrarás el precio total (con impuestos y cargos) antes de pagar?",
     "ok": "La información clara y veraz del precio es un derecho del consumidor (LFPC; Art. 76 bis en transacciones electrónicas).",
     "bad": "Ocultar parte del precio engaña al consumidor y es infracción sancionable por PROFECO."},
    {"id": "cargos", "tab": 1, "tipo": "sn", "t": "Cargos ocultos", "c": False,
     "q": "¿Agregarás cargos ocultos al final del proceso de pago?",
     "ok": "Sin cargos ocultos, el consumidor decide con información completa (LFPC).",
     "bad": "Los cargos ocultos son una práctica engañosa sancionable por PROFECO (LFPC)."},
    {"id": "proveedor", "tab": 1, "tipo": "sn", "t": "Datos del proveedor", "c": True,
     "q": "¿Publicarás nombre, domicilio y datos de contacto del proveedor?",
     "ok": "En comercio electrónico el proveedor debe dar su domicilio y medios de contacto (LFPC, Art. 76 bis).",
     "bad": "Sin datos del proveedor el consumidor no puede reclamar; incumples la LFPC (Art. 76 bis)."},
    {"id": "devol", "tab": 1, "tipo": "sn", "t": "Política de devoluciones", "c": True,
     "q": "¿Incluirás una política visible de cambios, devoluciones y cancelación?",
     "ok": "Informar las condiciones de cambio y cancelación es parte de la transparencia en comercio electrónico (LFPC).",
     "bad": "Sin política clara el consumidor queda desprotegido; PROFECO puede sancionarlo."},
    {"id": "premarcada", "tab": 1, "tipo": "sn", "t": "Casilla premarcada", "c": False,
     "q": "¿Usarás una casilla de suscripción premarcada?",
     "ok": "El consentimiento debe ser libre, específico e informado; una casilla vacía lo garantiza.",
     "bad": "Las casillas premarcadas inducen a error: no son un consentimiento libre ni informado (LFPDPPP, LFPC)."},
    {"id": "avisot", "tab": 1, "tipo": "sn", "t": "Aviso de privacidad", "c": True,
     "q": "¿Publicarás el aviso de privacidad antes de pedir datos al cliente?",
     "ok": "La LFPDPPP exige el aviso de privacidad antes de recabar datos.",
     "bad": "Recabar datos sin aviso incumple la LFPDPPP y puede derivar en multas."},
    {"id": "audsesgo", "tab": 2, "tipo": "sn", "t": "Auditoría de sesgos", "c": True,
     "q": "¿Auditarás tu modelo de crédito para detectar sesgos por grupos?",
     "ok": "Auditar el modelo previene la discriminación algorítmica (Art. 1° CPEUM; Recomendación UNESCO 2021).",
     "bad": "Un modelo sin auditar puede reproducir sesgos y discriminar sin que lo notes."},
    {"id": "colonia", "tab": 2, "tipo": "sn", "t": "Variable 'colonia'", "c": False,
     "q": "¿Usarás la colonia o el código postal como variable de decisión?",
     "ok": "Evitar variables 'proxy' reduce el riesgo de discriminación por origen socioeconómico.",
     "bad": "La colonia puede ser un proxy de discriminación socioeconómica; hay que evitarla o medir su impacto."},
    {"id": "explic", "tab": 2, "tipo": "sn", "t": "Explicación y revisión humana", "c": True,
     "q": "¿Darás explicación y revisión humana a quien sea rechazado?",
     "ok": "Transparencia y supervisión humana son principios de la UNESCO y se exigen en sistemas de alto riesgo del Reglamento de IA de la UE.",
     "bad": "Sin explicación ni revisión humana la persona no puede cuestionar la decisión automatizada."},
    {"id": "entrena", "tab": 2, "tipo": "sn", "t": "Datos sin consentimiento", "c": False,
     "q": "¿Entrenarás el modelo con datos personales sin consentimiento ni aviso?",
     "ok": "Tratar datos personales exige aviso y consentimiento (LFPDPPP); evitarlo protege la privacidad.",
     "bad": "Usar datos personales sin consentimiento ni aviso viola la LFPDPPP."},
    {"id": "consent", "tab": 3, "tipo": "sn", "t": "Consentimiento informado", "c": True,
     "q": "¿Pedirás consentimiento informado a los participantes de tu estudio de usuarios?",
     "ok": "La investigación ética exige que los participantes sepan para qué se usan sus datos y puedan retirarse.",
     "bad": "Sin consentimiento informado el estudio es éticamente inaceptable y puede violar la LFPDPPP."},
    {"id": "anonim", "tab": 3, "tipo": "sn", "t": "Anonimizar y minimizar", "c": True,
     "q": "¿Anonimizarás y minimizarás los datos que recolectes?",
     "ok": "Minimización y anonimización reducen el riesgo de reidentificación (LFPDPPP).",
     "bad": "Guardar datos de más y sin anonimizar aumenta el riesgo de fugas y reidentificación."},
    {"id": "privados", "tab": 3, "tipo": "sn", "t": "Mensajes privados", "c": False,
     "q": "¿Publicarás mensajes privados de un grupo con los nombres de usuario?",
     "ok": "Que algo sea accesible no lo hace publicable; protegerlo respeta la privacidad.",
     "bad": "Publicar mensajes privados con nombres expone datos y vulnera la privacidad (Art. 16 CPEUM)."},
    {"id": "musica", "tab": 3, "tipo": "sn", "t": "Música con licencia", "c": False,
     "q": "¿Usarás en tus redes una canción comercial sin licencia?",
     "ok": "Usar música con licencia respeta los derechos patrimoniales del autor (LFDA).",
     "bad": "Usar una obra musical sin autorización infringe derechos de autor (LFDA)."},
    {"id": "fotos", "tab": 3, "tipo": "sn", "t": "Fotos de empleados", "c": True,
     "q": "¿Pedirás autorización para publicar fotos de tus empleados?",
     "ok": "El retrato de una persona solo puede usarse con su consentimiento expreso (Art. 87 LFDA).",
     "bad": "Publicar su imagen sin consentimiento vulnera su derecho (Art. 87 LFDA)."},
    {"id": "regmarca", "tab": 0, "tipo": "sn", "t": "Registro de marca", "c": True,
     "q": "¿Registrarás tu marca y logotipo ante el IMPI antes de lanzar la app?",
     "ok": "La marca se protege registrándola ante el IMPI (LFPPI); el registro te da el derecho exclusivo de uso.",
     "bad": "Sin registro, tu marca queda expuesta a que otra persona la registre primero."},
    {"id": "licencia", "tab": 0, "tipo": "sn", "t": "Licencia de tu código", "c": True,
     "q": "¿Elegirás y publicarás una licencia clara para tu propio código (MIT, GPL o propietaria)?",
     "ok": "Declarar la licencia dice qué pueden hacer otras personas con tu obra y respeta el derecho de autor (LFDA).",
     "bad": "Sin licencia explícita nadie sabe qué usos están permitidos: la obra queda con todos los derechos reservados."},
    {"id": "avisoia", "tab": 2, "tipo": "sn", "t": "Transparencia de la IA", "c": True,
     "q": "¿Avisarás a las personas cuando estén interactuando con una IA y no con una persona?",
     "ok": "La transparencia sobre el uso de IA es un principio de la UNESCO y una obligación en ciertos sistemas del Reglamento de IA de la UE.",
     "bad": "Ocultar que se trata de una IA puede engañar a las personas y vulnerar su autonomía."},
    {"id": "redes", "tab": 3, "tipo": "sn", "t": "Normas de redes sociales", "c": True,
     "q": "¿Definirás por escrito reglas de uso de redes sociales para tu equipo (confidencialidad, respeto, marcas)?",
     "ok": "Las normas de redes sociales previenen filtraciones, acoso y daños reputacionales, y dan certeza al personal.",
     "bad": "Sin reglas claras es fácil filtrar información confidencial o publicar contenido que dañe a terceros."},
]

# álbum: (id, título, fundamento) por distrito
def album_items(u):
    if u == 0:
        return [(e["id"], e["t"], e["f"] + "\n\nEnfoque ético: " + e["e"] + "\nValor: " + VPE[e["id"]][0] + " · Principio: " + VPE[e["id"]][1] + " · Elemento: " + VPE[e["id"]][2]) for e in CHAT]
    if u == 1:
        return [(e["id"], e["t"], e["f"]) for e in HOT]
    if u == 2:
        return [(e["id"], e["t"], e["f"] + "\n\nSanción: " + e["s"] + "\nPrevención: " + e["p"]) for e in CARTAS]
    out = []
    for e in LAB:
        if e["tipo"] == "radio":
            out.append((e["id"], e["t"], e["q"] + "\n\n" + max(e["opts"], key=lambda z: z[1])[2]))
        else:
            out.append((e["id"], e["t"], e["q"] + "\n\n" + e["ok"]))
    return out


# ---------------------------------------------------------------- temario oficial -> actividades del juego
# (tema del programa, [ids de las actividades que lo cubren])
TEMARIO = [
    [("Conceptos básicos: moral, valores, principios y dilemas éticos", ["plagio", "legal"]),
     ("Ética en las TIC: importancia y desafíos", ["bots", "software"]),
     ("Ética para empleados y usuarios de TI", ["politica", "acoso"]),
     ("Ética en el desarrollo de software", ["software"]),
     ("Elementos éticos fundamentales: privacidad, seguridad, responsabilidad, propiedad intelectual y acceso equitativo", ["legal", "software", "acceso", "plagio"]),
     ("Dilemas éticos: ciberacoso, plagio, discriminación y desinformación", ["acoso", "plagio", "discrim", "bots"]),
     ("Toma de decisiones éticas", ["legal", "discrim", "software"]),
     ("Cumplimiento normativo: políticas y procedimientos", ["politica"])],
    [("El derecho de la información", ["info"]),
     ("Régimen jurídico de la información en México", ["pizarra", "autor"]),
     ("Marco constitucional (Arts. 6, 7, 8 y 16)", ["info", "peticion", "aviso"]),
     ("Libertad de expresión", ["foro"]),
     ("Derecho de petición", ["peticion"]),
     ("Privacidad de datos", ["camara"]),
     ("Protección de datos", ["aviso", "arco"]),
     ("Propiedad intelectual y derechos de autor en lo digital", ["autor", "pizarra"]),
     ("Revisión de código", ["codigo"])],
    [("Responsabilidad social y ambiental en las TIC", ["ewaste"]),
     ("Delitos informáticos: definición, tipos, penas y prevención", ["phishing", "acceso"]),
     ("Normatividad nacional e internacional", ["ransom", "estafa"]),
     ("Delitos contra el patrimonio: estafas, defraudaciones y daños", ["estafa", "phishing", "ransom"]),
     ("Delitos contra la propiedad intelectual", ["piratas"]),
     ("Las tecnologías como medios para cometer delitos", ["intimo", "deepfake"]),
     ("Normas y leyes nacionales e internacionales en IA", ["iasin", "deepfake"]),
     ("Cumplimiento normativo (compliance)", ["sinaviso", "licvenc", "tienda"])],
    [("Ética y responsabilidad en la investigación en línea", ["consent", "anonim", "privados"]),
     ("Ética en el uso de las redes sociales", ["redes", "musica", "fotos"]),
     ("Propiedad industrial, licenciamiento y derechos de autor (copyright y copyleft)", ["gpl", "atrib", "marca", "regmarca", "licencia"]),
     ("Comercio electrónico y protección al consumidor", ["precio", "cargos", "proveedor", "devol"]),
     ("IA y ética: sesgos, discriminación y privacidad", ["audsesgo", "colonia", "explic", "entrena", "avisoia"])],
]

BIBLIO = [
    "Menéndez Mato, J. C. y Gayo Santa Cecilia, M. E. (2014). Derecho e Informática. Ética y legislación. Bosch Editor.",
    "Davara Rodríguez, M. Á. (coord.) (2020). Manual de derecho informático. Thomson Reuters Aranzadi.",
    "López Sánchez, R. y Leal Espinoza, J. L. (2018). El derecho a la información y datos personales en México: una visión comparada con el sistema interamericano y europeo de derechos humanos. Dykinson.",
    "Rodríguez Ayuso, J. F. y Montero Pascual, J. J. (2023). La nueva regulación de los datos. Aranzadi.",
]


def desempeno(p):
    if p >= 90:
        return "Competente Estratégico"
    if p >= 80:
        return "Competente Autónomo"
    if p >= 70:
        return "Competente Básico"
    return "Sigue practicando"


# ======================================================================
#                              APLICACIÓN
# ======================================================================
class App:
    def __init__(self, root):
        self.root = root
        root.title("Gatópolis - Ética y Legislación en TIC")
        root.resizable(False, False)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{W}x{H}+{max(0, (sw - W) // 2)}+{max(0, (sh - H) // 2 - 20)}")
        self.c = tk.Canvas(root, width=W, height=H, highlightthickness=0, bg=WALL)
        self.c.pack()
        self.c.bind("<Button-1>", lambda e: self.c.focus_set(), add="+")
        root.protocol("WM_DELETE_WINDOW", self.cerrar)
        self._n = 0
        self._entry = None
        self._jobs = set()
        self._cerrando = False
        self._tick_id = None
        self._tip = None
        self.actors = []
        self.t0 = time.time()
        self.tick_ms = int(1000 / css(".animacion", "fps", 6))
        self.hover_ms = int(css(".animacion", "hover-ms", 50))
        self.run = None
        self.alb_u = 0
        self.prog = {"consent": None, "alias": "MICHI", "best": {}, "runbest": {}, "anim": True}
        self.cargar()
        self._last = time.perf_counter()
        self._tick()
        if self.prog["consent"] is None:
            self.privacidad(True)
        else:
            self.menu()

    def after(self, ms, fn):
        jid = None

        def run():
            self._jobs.discard(jid)
            if not self._cerrando:
                fn()
        jid = self.root.after(ms, run)
        self._jobs.add(jid)
        return jid

    def cancel(self, jid):
        self._jobs.discard(jid)
        try:
            self.root.after_cancel(jid)
        except tk.TclError:
            pass

    def _tick(self):
        if self._cerrando:
            return
        ahora = time.perf_counter()
        real = (ahora - self._last) * 1000
        self._last = ahora
        base = int(1000 / css(".animacion", "fps", 14))
        lag = real / max(1, self.tick_ms)
        if lag > 1.5:                       # la PC no alcanza: menos cuadros por segundo
            self.tick_ms = min(250, int(self.tick_ms * 1.35))
        elif lag < 1.2 and self.tick_ms > base:
            self.tick_ms = max(base, int(self.tick_ms * 0.92))
        if self.prog.get("anim", True):
            t = time.time() - self.t0
            for a in list(self.actors):
                try:
                    a.update(t)
                except tk.TclError:
                    pass
        self._tick_id = self.root.after(self.tick_ms, self._tick)

    def cerrar(self):
        """Cierra sin destruir widgets dentro de un callback (evita el error fatal de Tcl)."""
        if self._cerrando:
            return
        self._cerrando = True
        for j in list(self._jobs):
            try:
                self.root.after_cancel(j)
            except tk.TclError:
                pass
        self._jobs.clear()
        if self._tick_id:
            try:
                self.root.after_cancel(self._tick_id)
            except tk.TclError:
                pass
        self.actors = []
        try:
            self.root.destroy()
        except tk.TclError:
            pass
        self.root.quit()

    def guardar(self):
        if self.prog.get("consent"):
            try:
                with open(SAVE, "w", encoding="utf-8") as f:
                    json.dump(self.prog, f, ensure_ascii=False, indent=2)
            except OSError:
                pass

    def raton(self, cx, cy, s, kind, hurt=False, extra=(), anim=True):
        a = MouseActor(self.c, cx, cy, s, kind, hurt, extra)
        if anim:
            self.actors.append(a)
        return a

    def paw(self, x, y, s, color):
        c = self.c
        c.create_oval(x - 7 * s, y - 2 * s, x + 7 * s, y + 9 * s, fill=color, outline="")
        for dx, dy in ((-10, -8), (-3.5, -13), (3.5, -13), (10, -8)):
            c.create_oval(x + (dx - 3.2) * s, y + (dy - 3.5) * s, x + (dx + 3.2) * s,
                          y + (dy + 3.5) * s, fill=color, outline="")

    def rrect(self, x1, y1, x2, y2, r=14, **kw):
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1
        r = max(1.0, min(float(r), (x2 - x1) / 2.0, (y2 - y1) / 2.0))
        fill = kw.pop("fill", "")
        outline = kw.pop("outline", "")
        width = kw.pop("width", 1)
        tags = kw.get("tags", ())
        d = 2.0 * r
        if outline and width > 0:
            # Borde exterior dibujado con óvalos y rectángulos sólidos (sin create_arc)
            for a, b, c_, d_ in (
                (x1, y1, x1 + d, y1 + d),
                (x2 - d, y1, x2, y1 + d),
                (x1, y2 - d, x1 + d, y2),
                (x2 - d, y2 - d, x2, y2),
            ):
                self.c.create_oval(a, b, c_, d_, fill=outline, outline="", tags=tags)
            self.c.create_rectangle(x1 + r, y1, x2 - r, y2, fill=outline, outline="", tags=tags)
            self.c.create_rectangle(x1, y1 + r, x2, y2 - r, fill=outline, outline="", tags=tags)
            if fill:
                ix1, iy1, ix2, iy2 = x1 + width, y1 + width, x2 - width, y2 - width
                ir = max(1.0, r - width)
                id_ = 2.0 * ir
                for a, b, c_, d_ in (
                    (ix1, iy1, ix1 + id_, iy1 + id_),
                    (ix2 - id_, iy1, ix2, iy1 + id_),
                    (ix1, iy2 - id_, ix1 + id_, iy2),
                    (ix2 - id_, iy2 - id_, ix2, iy2),
                ):
                    self.c.create_oval(a, b, c_, d_, fill=fill, outline="", tags=tags)
                self.c.create_rectangle(ix1 + ir, iy1, ix2 - ir, iy2, fill=fill, outline="", tags=tags)
                self.c.create_rectangle(ix1, iy1 + ir, ix2, iy2 - ir, fill=fill, outline="", tags=tags)
        elif fill:
            for a, b, c_, d_ in (
                (x1, y1, x1 + d, y1 + d),
                (x2 - d, y1, x2, y1 + d),
                (x1, y2 - d, x1 + d, y2),
                (x2 - d, y2 - d, x2, y2),
            ):
                self.c.create_oval(a, b, c_, d_, fill=fill, outline="", tags=tags)
            self.c.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline="", tags=tags)
            self.c.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline="", tags=tags)
        return None

    def panel(self, x1, y1, x2, y2, color=BORDER, fill=CARD):
        r = css(".panel", "border-radius", 16)
        sd = css(".panel", "box-shadow", 5)
        self.rrect(x1 + sd - 1, y1 + sd, x2 + sd - 1, y2 + sd, r, fill=SHADOW, outline="")
        return self.rrect(x1, y1, x2, y2, r, fill=fill, outline=color, width=int(css(".panel", "border-width", 3)))

    def txt(self, x, y, s, size=12, color=INK, bold=True, anchor="center", width=None, tags=()):
        just = "center" if anchor == "center" else "left"
        return self.c.create_text(x, y, text=s, font=(FONT, size, "bold" if bold else "normal"),
                                  fill=color, anchor=anchor, width=width or 0, tags=tags, justify=just)

    def _bind(self, x1, y1, x2, y2, ftag, cmd, color, hover):
        c = self.c
        htag = f"bh{self._n}"
        self._n += 1
        # Capa invisible única encima de todo el botón: cero parpadeo de eventos y cero bucles after()
        hit = c.create_rectangle(x1, y1, x2, y2, fill="", outline="", tags=(htag,))

        def entrar(e):
            if self._cerrando:
                return
            try:
                c.config(cursor="hand2")
                c.itemconfig(ftag, fill=hover)
            except tk.TclError:
                pass

        def salir(e):
            if self._cerrando:
                return
            try:
                c.config(cursor="")
                c.itemconfig(ftag, fill=color)
            except tk.TclError:
                pass

        def click(e):
            if self._cerrando:
                return
            try:
                c.config(cursor="")
            except tk.TclError:
                pass
            self.root.after_idle(cmd)

        c.tag_bind(hit, "<Enter>", entrar)
        c.tag_bind(hit, "<Leave>", salir)
        c.tag_bind(hit, "<ButtonRelease-1>", click)

    def button(self, x1, y1, x2, y2, label, cmd, color, sub=None, fs=15):
        tag = f"b{self._n}"
        ftag = f"bf{self._n}"
        self._n += 1
        r = css(".boton", "border-radius", 16)
        sd = css(".boton", "box-shadow", 5)
        self.rrect(x1 + 3, y1 + sd, x2 + 3, y2 + sd, r, fill=shade(color, 0.22), outline="", tags=(tag,))
        self.rrect(x1, y1, x2, y2, r, fill=color, outline=shade(color, 0.35),
                   width=int(css(".boton", "border-width", 2)), tags=(tag, ftag))
        cy = (y1 + y2) / 2
        w = x2 - x1 - 16
        if sub:
            self.txt((x1 + x2) / 2, cy - 10, label, fs, tags=(tag,), width=w)
            self.txt((x1 + x2) / 2, cy + 14, sub, 9, INK2, False, tags=(tag,), width=w)
        else:
            self.txt((x1 + x2) / 2, cy, label, fs, tags=(tag,), width=w)
        self._bind(x1, y1, x2, y2, ftag, cmd, color, light(color, 0.45))

    def burbuja(self, x1, y1, x2, y2, texto, lado="izq"):
        self.rrect(x1 + 2, y1 + 3, x2 + 2, y2 + 3, 16, fill=SHADOW, outline="")
        self.rrect(x1, y1, x2, y2, 16, fill="white", outline=BORDER, width=2)
        if lado == "izq":
            self.c.create_polygon(x1 + 18, y2 - 2, x1 + 6, y2 + 16, x1 + 38, y2 - 2, fill="white", outline=BORDER, width=2)
            self.c.create_line(x1 + 20, y2, x1 + 36, y2, fill="white", width=3)
        else:
            self.c.create_polygon(x2 - 18, y2 - 2, x2 - 6, y2 + 16, x2 - 38, y2 - 2, fill="white", outline=BORDER, width=2)
            self.c.create_line(x2 - 20, y2, x2 - 36, y2, fill="white", width=3)
        self.txt((x1 + x2) / 2, (y1 + y2) / 2, texto, 10, INK, False, width=x2 - x1 - 20)

    def plataforma(self, cx, cy, rx, color):
        self.c.create_oval(cx - rx, cy - 16, cx + rx, cy + 16, fill=color, outline=shade(color, 0.3), width=2)
        self.c.create_oval(cx - rx + 14, cy - 9, cx + rx - 14, cy + 9, fill=light(color, 0.4), outline="")

    def info(self, titulo, cuerpo, size=11):
        self.draw_bg()
        self.panel(40, 16, 1060, 560)
        self.txt(550, 48, titulo, 22, INK)
        self.txt(70, 88, cuerpo, size, INK, False, anchor="nw", width=960)
        self.button(450, 576, 650, 624, "Volver", self.menu, PINK, fs=14)

    def alt_anim(self):
        self.prog["anim"] = not self.prog.get("anim", True)
        self.guardar()
        self.ajustes()

    # ---------- progreso
    def cargar(self):
        try:
            with open(SAVE, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict) and d.get("consent") is True:
                for k in ("consent", "alias", "best", "runbest", "anim"):
                    if k in d:
                        self.prog[k] = d[k]
        except (OSError, ValueError):
            pass

    def puntos(self):
        return sum(self.prog["best"].values())

    def pct_u(self, u):
        return self.prog["runbest"].get(str(u), 0)

    def estrellas_u(self, u):
        p = self.pct_u(u)
        return 3 if p >= 90 else 2 if p >= 80 else 1 if p >= 60 else 0

    def estrellas(self):
        return sum(self.estrellas_u(u) for u in range(4))

    def rango(self):
        return RANGOS[min(4, self.estrellas() // 3)]

    @staticmethod
    def estr_txt(k):
        return "★" * k + "☆" * (3 - k)

    def registrar(self, u, id_, pts):
        key = f"{u}:{id_}"
        self.prog["best"][key] = max(self.prog["best"].get(key, 0), pts)

    def terminar(self, u, pts, mx, errores, dead=False):
        pct = round(100 * pts / mx)
        if pct > self.pct_u(u):
            self.prog["runbest"][str(u)] = pct
        self.guardar()
        self.resultados(u, pts, mx, pct, errores, dead)

    # ---------- utilidades de dibujo
    def gato(self, cx, cy, s, mood="neutral", extra=(), salto=False, anim=True, peluca=False):
        a = CatActor(self.c, cx, cy, s, mood, extra, salto, peluca)
        if anim:
            self.actors.append(a)
        return a

    def limpiar(self):
        for j in list(self._jobs):
            self.cancel(j)
        self.actors = []
        if self._entry is not None:
            self._entry = None
        try:
            self.c.unbind("<Key>")
        except tk.TclError:
            pass
        try:
            self.c.config(cursor="")
        except tk.TclError:
            pass
        self.c.delete("all")

    def draw_bg(self):
        """Fondo ligero: pared a rayas y piso (unas 25 figuras en total)."""
        self.limpiar()
        c = self.c
        base = 420
        c.create_rectangle(0, 0, W, base, fill=WALL, outline="")
        for x in range(0, W, 88):
            c.create_rectangle(x, 0, x + 44, base, fill=WALL2, outline="")
        c.create_rectangle(0, base, W, H, fill=FLOOR, outline="")
        c.create_rectangle(0, base - 10, W, base + 6, fill=PLANK, outline="")
        for y in range(base + 40, H, 40):
            c.create_line(0, y, W, y, fill=PLANK)

    def pill(self, x1, y1, x2, y2, color, texto, size=12, anchor="center"):
        """Píldora ligera: una sola figura redondeada con borde y su texto."""
        self.rrect(x1, y1, x2, y2, (y2 - y1) / 2, fill=color, outline=shade(color, 0.35), width=2)
        if anchor == "center":
            self.txt((x1 + x2) / 2, (y1 + y2) / 2, texto, size, width=x2 - x1 - 12)
        else:
            self.txt(x1 + 16, (y1 + y2) / 2, texto, size, anchor="w", width=x2 - x1 - 24)

    def bar(self, x1, y, x2, v, label=None, color=None, h=14):
        """Barra ligera: dos rectángulos."""
        v = max(0, min(100, v))
        col = color or (MINT if v > 50 else BUTTER if v > 25 else CORAL)
        if label:
            self.txt(x1, y - 11, label, 9, INK2, anchor="w")
        self.c.create_rectangle(x1, y, x2, y + h, fill="#efe1c8", outline=BORDER, width=1)
        if v > 0:
            self.c.create_rectangle(x1 + 1, y + 1, x1 + 1 + max(3, (x2 - x1 - 2) * v / 100), y + h - 1,
                                    fill=col, outline="")

    def privacidad(self, primera):
        self.draw_bg()
        self.panel(30, 16, 1070, 492)
        self.txt(550, 44, "Aviso de privacidad y términos de uso", 20, INK)
        self.txt(60, 76, AVISO_G.format(a=AUTORES) + "\n\n" + TERMINOS_G, 10, INK, False,
                 anchor="nw", width=980)
        if primera:
            self._alias_buf = ""
            self.txt(340, 520, "Tu alias (haz clic y escribe):", 12, anchor="e")
            self.c.create_rectangle(350, 504, 600, 536, fill=CARD, outline=INK, width=2)
            campo = self.txt(362, 520, "MICHI", 13, INK2, False, anchor="w")

            def on_key(ev):
                if ev.keysym == "Return":
                    self.decidir(True)
                    return
                if ev.keysym == "BackSpace":
                    self._alias_buf = self._alias_buf[:-1]
                elif ev.char and ev.char.isprintable() and len(self._alias_buf) < 16:
                    self._alias_buf += ev.char
                try:
                    if self._alias_buf:
                        self.c.itemconfig(campo, text=self._alias_buf + "_", fill=INK)
                    else:
                        self.c.itemconfig(campo, text="_", fill=INK2)
                except tk.TclError:
                    pass

            self.c.bind("<Key>", on_key)
            self.zona(350, 504, 600, 536, lambda: self.c.focus_force())
            self.c.focus_force()
            self.button(60, 554, 540, 620, "Acepto y guardar mi progreso", lambda: self.decidir(True), MINT, fs=13)
            self.button(560, 554, 1040, 620, "Jugar sin guardar", lambda: self.decidir(False), LAV, fs=13)
        else:
            self.button(420, 554, 680, 620, "Volver", self.ajustes, PINK, fs=14)

    def decidir(self, acepta):
        try:
            self.c.unbind("<Key>")
        except tk.TclError:
            pass
        alias = getattr(self, "_alias_buf", "").strip()[:16] or "MICHI"
        self.prog["alias"] = alias
        self.prog["consent"] = bool(acepta)
        self.guardar()
        self.menu()

    def zona(self, x1, y1, x2, y2, cmd, enter=None, leave=None):
        c = self.c
        htag = f"bh{self._n}"
        self._n += 1
        c.create_rectangle(x1, y1, x2, y2, fill="", outline="", tags=(htag,))

        def entrar(e):
            if self._cerrando:
                return
            try:
                c.config(cursor="hand2")
                if enter:
                    enter()
            except tk.TclError:
                pass

        def salir(e):
            if self._cerrando:
                return
            try:
                c.config(cursor="")
                if leave:
                    leave()
            except tk.TclError:
                pass

        def click(e):
            if self._cerrando:
                return
            try:
                c.config(cursor="")
            except tk.TclError:
                pass
            self.root.after_idle(cmd)

        c.tag_bind(htag, "<Enter>", entrar)
        c.tag_bind(htag, "<Leave>", salir)
        c.tag_bind(htag, "<ButtonRelease-1>", click)

    def capa_ini(self):
        ids = self.c.find_all()
        self._m0 = ids[-1] if ids else 0

    def capa_fin(self, tag):
        for it in self.c.find_all():
            if it > self._m0:
                self.c.addtag_withtag(tag, it)

    def mini(self, x1, y1, x2, y2, texto, color, cmd, fs=11):
        ftag = f"bf{self._n}"
        self._n += 1
        self.c.create_rectangle(x1, y1, x2, y2, fill=color, outline=shade(color, 0.35), width=2, tags=(ftag,))
        self.txt((x1 + x2) / 2, (y1 + y2) / 2, texto, fs, width=x2 - x1 - 8)
        self._bind(x1, y1, x2, y2, ftag, cmd, color, light(color, 0.45))

    def opcion(self, x1, y1, x2, y2, letra, texto, color, cmd, fs=10):
        tag = f"b{self._n}"
        ftag = f"bf{self._n}"
        self._n += 1
        self.rrect(x1 + 3, y1 + 4, x2 + 3, y2 + 4, 12, fill=SHADOW, outline="", tags=(tag,))
        self.rrect(x1, y1, x2, y2, 12, fill=CARD, outline=BORDER, width=2, tags=(tag, ftag))
        cy = (y1 + y2) / 2
        self.c.create_oval(x1 + 12, cy - 15, x1 + 42, cy + 15, fill=color, outline=shade(color, 0.35), width=2, tags=(tag,))
        self.txt(x1 + 27, cy, letra, 13, tags=(tag,))
        self.txt(x1 + 54, cy, texto, fs, bold=False, anchor="w", width=x2 - x1 - 68, tags=(tag,))
        self._bind(x1, y1, x2, y2, ftag, cmd, CARD, light(color, 0.6))

    def barra(self, u, centro, derecha):
        d = DIST[u]
        self.pill(20, 16, 520, 58, d["col"], f"Distrito {d['u']} · {d['n']}", 12, anchor="w")
        self.pill(534, 16, 694, 58, BUTTER, centro, 13)
        self.pill(708, 16, 898, 58, PINK, derecha, 13)
        self.button(912, 16, 1080, 58, "Mapa", self.menu, LAV, fs=12)

    def michi_card(self, mood="neutral", frase="", barras=(), peluca=False, nombre="MICHI"):
        self.panel(20, 72, 250, 626, SKY)
        self.plataforma(135, 350, 80, PINK)
        self.gato(135, 232, 1.3, mood, peluca=peluca)
        self.txt(135, 386, nombre, 14)
        self.txt(135, 406, self.rango(), 9, INK2, False)
        if frase:
            self.burbuja(36, 424, 234, 470, frase, "izq")
        for k, (lab, v, col) in enumerate(barras):
            self.bar(38, 512 + 38 * k, 232, v, lab, col)

    # ======================= MAPA (menú principal) =======================
    def menu(self):
        self.limpiar()
        c = self.c
        for i, col in enumerate(["#d9ecf7", "#e3f0f4", "#ecf3ee", "#f3f1e6", "#f6ecd9"]):
            c.create_rectangle(0, i * 90, W, (i + 1) * 90, fill=col, outline="")
        c.create_oval(930, 70, 1010, 150, fill="#fbe7a8", outline="")
        for x, y, s in ((150, 112, 1.0), (590, 100, 1.3), (800, 160, 0.8)):
            for dx, dy, r in ((0, 0, 26), (28, -10, 32), (60, 0, 24), (30, 10, 26)):
                c.create_oval(x + (dx - r) * s, y + (dy - r * 0.6) * s, x + (dx + r) * s,
                              y + (dy + r * 0.6) * s, fill="white", outline="")
        c.create_oval(-120, 400, 520, 600, fill="#d4e6c6", outline="")
        c.create_oval(380, 420, 1220, 620, fill="#cfe3c0", outline="")
        c.create_rectangle(0, 470, W, H, fill="#e3d5bf", outline="")
        c.create_rectangle(0, 470, W, 484, fill="#cdb998", outline="")
        for x in range(0, W, 90):
            c.create_rectangle(x, 530, x + 44, 536, fill="#f7efe0", outline="")
        # barra superior
        self.pill(20, 16, 250, 58, PEACH, "Gatópolis", 16)
        self.pill(262, 16, 590, 58, SKY, f"{self.prog['alias']} · {self.rango()}", 11)
        self.pill(602, 16, 720, 58, BUTTER, f"★ {self.estrellas()}/12", 13)
        self.pill(732, 16, 850, 58, PINK, f"{self.puntos()} pts", 13)
        self.button(862, 16, 966, 58, "Álbum", self.album, MINT, fs=12)
        self.button(978, 16, 1080, 58, "Ajustes", self.ajustes, LAV, fs=12)
        for i in range(4):
            self.edificio(i)
        self.gato(540, 504, 0.6, "happy")
        self.burbuja(596, 494, 776, 534, "¡Elige un distrito!", "izq")
        for k, (lab, cmd, col) in enumerate((("Instrucciones", self.instrucciones, SKY), ("Temario", self.temario, LAV),
                                             ("Acerca de", self.acerca, BUTTER), ("Certificado", self.certificado, MINT),
                                             ("Salir", self.cerrar, PINK))):
            self.button(20 + 215 * k, 566, 220 + 215 * k, 622, lab, cmd, col, fs=12)

    def edificio(self, i):
        d = DIST[i]
        col = d["col"]
        dk = shade(col, 0.35)
        c = self.c
        x1 = 30 + 270 * i
        x2 = x1 + 230
        y1 = 470 - (300, 330, 310, 340)[i]
        et = f"ed{i}"
        c.create_polygon(x1 + 14, y1 + 8, x1 + 34, y1 - 34, x1 + 72, y1 + 8, fill=col, outline=dk, width=2, tags=(et,))
        c.create_polygon(x2 - 72, y1 + 8, x2 - 34, y1 - 34, x2 - 14, y1 + 8, fill=col, outline=dk, width=2, tags=(et,))
        self.rrect(x1, y1, x2, 470, 18, fill=col, outline=dk, width=3, tags=(et,))
        cx = (x1 + x2) / 2
        self.rrect(x1 + 14, y1 + 14, x2 - 14, y1 + 86, 10, fill=CARD, outline=dk, width=2)
        self.txt(cx, y1 + 30, f"Unidad {d['u']}", 9, INK2, False)
        self.txt(cx, y1 + 60, d["n"], 11, width=190)
        for r in range(2):
            for k in range(3):
                wx, wy = x1 + 22 + k * 66, y1 + 102 + r * 56
                c.create_rectangle(wx, wy, wx + 44, wy + 40, fill="#fffaf0", outline=dk, width=2)
        c.create_rectangle(x1 + 88, 430, x2 - 88, 470, fill=shade(col, 0.3), outline=dk, width=2)
        self.txt(cx, 384, self.estr_txt(self.estrellas_u(i)), 16, GOLD)
        self.txt(cx, 408, d["modo"], 9, INK2, False, width=200)
        self.zona(x1, y1 - 34, x2, 470, lambda i=i: self.intro(i),
                  enter=lambda: c.itemconfigure(et, fill=light(col, 0.4)),
                  leave=lambda: c.itemconfigure(et, fill=col))

    # ======================= PANTALLAS GENERALES =======================
    def instrucciones(self):
        self.info("Instrucciones · guía de Gatópolis", INSTRUCCIONES_G, 11)

    def acerca(self):
        self.draw_bg()
        self.panel(30, 16, 1070, 568)
        self.txt(550, 46, "Acerca de · créditos, licencias y fuentes", 21, INK)
        izq = (f"GATÓPOLIS v{VERSION}\nAutores: {AUTORES}\n"
               "Universidad Tecnológica Emiliano Zapata del Estado de Morelos (UTEZ)\n"
               "Asignatura: Ética y Legislación en Tecnologías de la Información (E-ELTI-3). "
               "Programa DGUTyP, vigente desde septiembre de 2024.\n"
               "Docente: Mtra. Iris Nayeli Corona Aceves\n\n" + TERMINOS_G)
        der = ("REFERENCIAS LEGALES Y ÉTICAS\n" + "\n".join("• " + r for r in REFERENCIAS) +
               "\n\nBIBLIOGRAFÍA DEL PROGRAMA\n" + "\n".join("• " + b for b in BIBLIO))
        self.txt(56, 80, izq, 9, INK, False, anchor="nw", width=470)
        it = self.txt(560, 80, der, 9, INK, False, anchor="nw", width=480)
        self._acerca_fondo = self.c.bbox(it)[3]
        self.button(450, 578, 650, 626, "Volver", self.menu, PINK, fs=14)

    def estado_tema(self, u, refs):
        mejores = [self.prog["best"].get(f"{u}:{r}", None) for r in refs]
        if all(m == 10 for m in mejores):
            return "✓", "#2e7d4f"
        if any(m is not None for m in mejores):
            return "~", "#9a6b00"
        return "○", INK2

    def temario(self):
        self.draw_bg()
        self.pill(20, 16, 560, 58, BUTTER, "Temario E-ELTI-3 · tu cobertura", 14)
        self.txt(580, 37, "✓ dominado   ~ a medias   ○ pendiente", 10, INK2, False, anchor="w")
        self.button(912, 16, 1080, 58, "Mapa", self.menu, LAV, fs=12)
        for u in range(4):
            d = DIST[u]
            x1 = 20 + 266 * u
            x2 = x1 + 254
            self.panel(x1, 70, x2, 628, shade(d["col"], 0.2))
            self.pill(x1 + 10, 80, x2 - 10, 112, d["col"], f"Unidad {d['u']} · {d['n']}", 9)
            self.txt(x1 + 12, 122, d["tema"], 9, INK2, False, anchor="nw", width=232)
            y = 158
            hechos = 0
            for tema, refs in TEMARIO[u]:
                sym, col = self.estado_tema(u, refs)
                if sym == "✓":
                    hechos += 1
                it = self.txt(x1 + 12, y, f"{sym} {tema}", 9, col, False, anchor="nw", width=232)
                y = self.c.bbox(it)[3] + 7
            tot = len(TEMARIO[u])
            self.bar(x1 + 12, 600, x2 - 12, 100 * hechos / tot, f"Temas dominados: {hechos}/{tot}", d["col"], h=12)

    def intro(self, u):
        self.draw_bg()
        d = DIST[u]
        self.panel(50, 24, 1050, 536, shade(d["col"], 0.2))
        self.pill(76, 44, 780, 86, d["col"], f"Distrito {d['u']} · {d['n']} · modo: {d['modo']}", 12, anchor="w")
        self.txt(82, 112, INTRO[u], 12, INK, False, anchor="nw", width=690)
        self.plataforma(940, 372, 90, d["col"])
        self.raton(940, 270, 1.35, d["enem"])
        self.txt(940, 428, "El jefe del distrito", 11)
        self.button(60, 558, 300, 622, "Mapa", self.menu, PINK, fs=14)
        self.button(380, 558, 720, 622, "¡Entrar!", lambda: self.entrar(u), MINT, fs=18)

    def entrar(self, u):
        (self.chat_iniciar, self.insp_iniciar, self.trib_iniciar, self.lab_iniciar)[u]()

    # ======================= D1 · HISTORIA EN CHAT =======================
    def chat_iniciar(self):
        self.run = {"u": 0, "i": 0, "pts": 0, "max": 10 * len(CHAT), "y": 126, "m": 0, "opts": None,
                    "stats": {"ÉTICA": 50, "LEGAL": 50, "CONFIANZA": 50}, "errores": [], "dead": False}
        self.chat()

    def set_tip(self, txt):
        try:
            self.c.itemconfigure(self._tip, text=txt)
        except (tk.TclError, TypeError):
            pass

    def brujula(self):
        self.panel(850, 72, 1080, 626, PEACH)
        self.txt(965, 98, "Brújula ética", 15)
        pasos = ["Identifica el dilema", "¿Quiénes salen afectados?", "Revisa normas, códigos (ACM/IEEE) y la ley",
                 "Decide y asume las consecuencias"]
        for k, p in enumerate(pasos):
            y = 126 + k * 70
            self.c.create_oval(868, y, 898, y + 30, fill=PEACH, outline=shade(PEACH, 0.35), width=2)
            self.txt(883, y + 15, str(k + 1), 12)
            self.txt(906, y + 15, p, 10, INK, False, anchor="w", width=162)
        self.rrect(862, 420, 1068, 614, 10, fill=light(PEACH, 0.5), outline="")
        self.txt(965, 442, "Moral · Ética · Derecho", 11)
        self.txt(874, 462, "Moral: valores personales o de un grupo.\nÉtica: reflexión crítica sobre esas normas.\n"
                 "Derecho: normas obligatorias con sanción.\nAlgo puede ser legal y no ético.", 9, INK, False,
                 anchor="nw", width=186)

    def chat(self, resp=None):
        r = self.run
        esc = CHAT[r["i"]]
        d = DIST[0]
        self.draw_bg()
        self.barra(0, f"Escena {r['i'] + 1}/{len(CHAT)}", f"{r['pts']} pts")
        mood = None
        if resp:
            p = resp["opt"][1]
            mood = "happy" if p == 10 else "neutral" if p >= 5 else "sad"
        frase = "Mmm… hay que pensar bien" if not resp else {"happy": "¡Miau! Buena decisión",
                "neutral": "Se puede mejorar", "sad": "Uy… eso salió mal"}[mood]
        self.michi_card(mood or "neutral", frase, [(f"{k}  {v}", v, None) for k, v in r["stats"].items()])
        self.panel(264, 72, 836, 626, shade(d["col"], 0.2))
        self.rrect(274, 80, 826, 118, 10, fill=light(d["col"], 0.35), outline="")
        self.txt(292, 99, esc["canal"], 12, anchor="w")
        self._tip = self.txt(818, 99, "en línea", 9, INK2, False, anchor="e")
        self.txt(752, 99, "Elemento ético: " + VPE[esc["id"]][2], 9, INK2, False, anchor="e", width=230)
        self.brujula()
        r["y"] = 126
        if resp is None:
            r["m"] = 0
            r["opts"] = random.sample(esc["o"], len(esc["o"]))
            q0 = esc["msgs"][0][0]
            self.set_tip("en línea" if q0 == "Sistema" else f"{q0} está escribiendo…")
            self.after(RETARDO, self.chat_siguiente)
        else:
            for q, t in esc["msgs"]:
                self.chat_burbuja(q, t)
            self.chat_burbuja("Michi", resp["opt"][0], yo=True)
            self.after(int(RETARDO * 1.4), lambda: self.chat_feedback(resp))

    def chat_burbuja(self, quien, texto, yo=False):
        r = self.run
        c = self.c
        y = r["y"]
        if quien == "Sistema":
            it = self.txt(550, y + 12, texto, 9, INK2, False, width=420)
            r["y"] = c.bbox(it)[3] + 12
            return
        col = MINT if yo else PERSONAS.get(quien, SKY)
        it = self.txt(0, y + 24, texto, 10, INK, False, anchor="nw", width=380)
        bb = c.bbox(it)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        x0 = 820 - (tw + 24) if yo else 330
        c.move(it, x0 + 12 - bb[0], 0)
        tg = f"bb{self._n}"
        self._n += 1
        self.rrect(x0, y + 16, x0 + tw + 24, y + 24 + th + 10, 12, fill=light(col, 0.45),
                   outline=shade(col, 0.25), width=1, tags=(tg,))
        c.tag_lower(tg, it)
        self.txt(x0 + 8, y + 8, "Michi" if yo else quien, 8, INK2, anchor="w")
        if not yo:
            c.create_oval(288, y + 18, 318, y + 48, fill=col, outline=shade(col, 0.3), width=2)
            self.txt(303, y + 33, quien[0], 11)
        r["y"] = y + 24 + th + 10 + 12

    def chat_siguiente(self):
        r = self.run
        esc = CHAT[r["i"]]
        q, t = esc["msgs"][r["m"]]
        self.chat_burbuja(q, t)
        r["m"] += 1
        if r["m"] < len(esc["msgs"]):
            nq = esc["msgs"][r["m"]][0]
            self.set_tip("en línea" if nq == "Sistema" else f"{nq} está escribiendo…")
            self.after(RETARDO, self.chat_siguiente)
        else:
            self.set_tip("en línea")
            self.after(int(RETARDO * 0.6), self.chat_opciones)

    def chat_opciones(self):
        r = self.run
        col = DIST[0]["col"]
        y = 466
        for k, o in enumerate(r["opts"]):
            self.opcion(278, y, 822, y + 48, "ABC"[k], o[0], col, lambda k=k: self.chat_responder(k), fs=10)
            y += 54

    def chat_responder(self, k):
        r = self.run
        esc = CHAT[r["i"]]
        opt = r["opts"][k]
        r["pts"] += opt[1]
        for n, dlt in zip(r["stats"], opt[2:5]):
            r["stats"][n] = max(0, min(100, r["stats"][n] + dlt))
        if min(r["stats"].values()) <= 0:
            r["dead"] = True
        if opt[1] < 10:
            r["errores"].append(esc["t"])
        self.registrar(0, esc["id"], opt[1])
        self.guardar()
        self.chat({"opt": opt})

    def chat_feedback(self, resp):
        r = self.run
        esc = CHAT[r["i"]]
        opt = resp["opt"]
        pts = opt[1]
        color = MINT if pts == 10 else BUTTER if pts >= 5 else CORAL
        head = ("¡Excelente decisión!" if pts == 10 else
                "Buen intento, puedes mejorar" if pts >= 5 else "¡Cuidado con esa decisión!")
        self.panel(272, 124, 828, 560, shade(color, 0.3), fill=light(color, 0.6))
        self.txt(292, 148, f"{head}  +{pts} pts", 14, anchor="w")
        self.txt(292, 172, f"Ética {opt[2]:+d}  ·  Legal {opt[3]:+d}  ·  Confianza {opt[4]:+d}", 10, INK2, anchor="w")
        y = 192
        partes = [("Consecuencia: ", opt[5])]
        if pts < 10:
            partes.append(("Mejor decisión: ", max(esc["o"], key=lambda z: z[1])[0]))
        partes.append(("Fundamento: ", esc["f"]))
        partes.append(("Enfoque ético: ", esc["e"]))
        v, pr, el = VPE[esc["id"]]
        partes.append(("Valor en juego: ", f"{v}. Principio: {pr}. Elemento ético fundamental: {el}."))
        for et, cu in partes:
            it = self.txt(292, y, et + cu, 10, INK, False, anchor="nw", width=520)
            y = self.c.bbox(it)[3] + 8
        ultimo = r["dead"] or r["i"] + 1 >= len(CHAT)
        self.button(528, 572, 828, 618, "Ver resultado ▶" if ultimo else "Continuar ▶", self.chat_next, MINT, fs=14)

    def chat_next(self):
        r = self.run
        r["i"] += 1
        if r["dead"] or r["i"] >= len(CHAT):
            self.terminar(0, r["pts"], r["max"], r["errores"], r["dead"])
        else:
            self.chat()

    # ======================= D2 · INSPECCIÓN =======================
    def insp_iniciar(self):
        self.run = {"u": 1, "res": {}, "sel": {}, "opts": {}, "pistas": 2, "max": 10 * len(HOT), "errores": []}
        self.inspeccion()

    def inspeccion(self):
        r = self.run
        c = self.c
        d = DIST[1]
        self.draw_bg()
        self.barra(1, f"Hallazgos {len(r['res'])}/{len(HOT)}", f"{sum(r['res'].values())} pts")
        self.panel(20, 72, 1080, 560, shade(d["col"], 0.2), fill="#f4e7d3")
        c.create_rectangle(28, 434, 1072, 552, fill="#e2c9a3", outline="")
        c.create_rectangle(28, 426, 1072, 436, fill="#cdb089", outline="")
        for y in (464, 494, 524):
            c.create_line(28, y, 1072, y, fill="#d3b88c")
        # escritorio
        c.create_rectangle(240, 384, 650, 410, fill="#b98e5f", outline="#8a6a43", width=2)
        c.create_rectangle(262, 410, 282, 452, fill="#9c7650", outline="")
        c.create_rectangle(608, 410, 628, 452, fill="#9c7650", outline="")
        self.plataforma(730, 452, 90, PINK)
        self.gato(730, 372, 0.85, "neutral")
        c.create_oval(664, 350, 696, 382, outline=GOLD, width=4, fill="")
        c.create_line(690, 376, 708, 396, fill=GOLD, width=5)
        for k, h in enumerate(HOT):
            self.objeto(k, h)
        self.txt(30, 596, "Haz clic en los objetos sospechosos de la oficina. Pasa el cursor para resaltarlos.",
                 11, INK, False, anchor="w", width=600)
        self.button(650, 570, 840, 622, f"Pista ({r['pistas']})", self.pista, BUTTER, fs=13)
        self.button(860, 570, 1080, 622, "Terminar inspección", self.insp_fin, MINT, fs=12)

    def objeto(self, k, h):
        c = self.c
        i = h["id"]
        x1, y1, x2, y2 = h["box"]
        if i == "aviso":
            c.create_rectangle(270, 278, 450, 372, fill="#3a3a4e", outline="#22222e", width=3)
            c.create_rectangle(278, 286, 442, 364, fill="#fffaf0", outline="")
            self.txt(360, 298, "REGISTRO DE PACIENTES", 8, INK)
            for j, t in enumerate(("Nombre: ________", "CURP: ________", "Diagnóstico: ____")):
                self.txt(290, 314 + j * 12, t, 8, INK2, False, anchor="w")
            c.create_rectangle(318, 351, 402, 362, fill=MINT, outline=INK2)
            self.txt(360, 356, "ENVIAR", 7, INK)
            c.create_rectangle(350, 372, 370, 384, fill="#22222e", outline="")
        elif i == "peticion":
            c.create_rectangle(862, 108, 1000, 162, fill="white", outline=INK2)
            c.create_rectangle(872, 122, 1012, 172, fill="#fffaf0", outline=INK2)
            c.create_line(872, 122, 942, 154, 1012, 122, fill=INK2)
            self.txt(942, 146, "PETICIÓN", 9, INK)
            c.create_rectangle(860, 168, 1040, 200, fill="#d8c3a0", outline="#a88b5f", width=3)
            self.txt(950, 184, "BUZÓN", 9, INK)
        elif i == "foro":
            c.create_rectangle(610, 100, 790, 230, fill="#d9b887", outline="#8a6a43", width=5)
            c.create_rectangle(624, 114, 704, 170, fill=BUTTER, outline=INK2)
            self.txt(664, 142, "REGLAS\nDEL FORO", 8, INK)
            c.create_rectangle(716, 120, 780, 176, fill=PINK, outline=INK2)
            self.txt(748, 148, "Críticas\nal jefe", 8, INK)
            c.create_rectangle(628, 184, 782, 222, fill="white", outline=INK2)
            self.txt(705, 203, "BORRAR TODA CRÍTICA", 8, INK)
        elif i == "codigo":
            c.create_rectangle(484, 310, 598, 368, fill="#2f2f45", outline="#1c1c2c", width=3)
            for j, t in enumerate(('db_pass="admin123"', "SELECT * ... + correo", "log.write(curp)")):
                c.create_text(490, 322 + j * 14, text=t, font=("Consolas", 7), fill="#9fe3b0", anchor="w")
            c.create_rectangle(476, 368, 606, 384, fill="#9aa0b4", outline="#6c7186", width=2)
        elif i == "pizarra":
            c.create_rectangle(260, 100, 560, 240, fill="white", outline="#b9a07a", width=5)
            self.txt(410, 118, "ALGORITMO DE RECOMENDACIÓN", 9, INK)
            for bx, t in ((284, "datos"), (396, "modelo"), (488, "app")):
                c.create_rectangle(bx, 144, bx + 62, 178, fill=light(LAV, 0.3), outline=INK2)
                self.txt(bx + 31, 161, t, 9, INK)
            c.create_line(346, 161, 396, 161, fill=INK2, arrow="last")
            c.create_line(458, 161, 488, 161, fill=INK2, arrow="last")
            self.txt(410, 212, "¿Patente? ¿Autor? ¿Secreto?", 10, INK2, False)
        elif i == "camara":
            c.create_rectangle(56, 104, 204, 226, fill="#f0e6d6", outline="#b9a07a", width=4)
            c.create_line(118, 176, 118, 196, fill="#4a4a5e", width=5)
            c.create_rectangle(76, 138, 152, 178, fill="#4a4a5e", outline="#2a2a3a", width=3)
            c.create_oval(150, 144, 180, 172, fill="#2f2f45", outline="#1c1c2c", width=3)
            c.create_oval(158, 151, 172, 165, fill="#7fb6e8", outline="")
            c.create_oval(84, 146, 94, 156, fill=CORAL, outline="")
            self.txt(130, 118, "ENTRADA", 9, INK)
            self.txt(130, 210, "reconocimiento facial", 8, INK2, False)
        elif i == "arco":
            c.create_rectangle(884, 368, 1036, 422, fill="#3a3a4e", outline="#22222e", width=3)
            c.create_rectangle(892, 376, 1028, 414, fill="#fffaf0", outline="")
            c.create_rectangle(900, 382, 1020, 408, fill=light(PINK, 0.4), outline=INK2)
            self.txt(960, 395, "Borren mis datos", 8, INK)
        elif i == "info":
            c.create_rectangle(50, 250, 200, 450, fill="#c9c4d8", outline="#8b86a0", width=3)
            for j, yy in enumerate((262, 320, 378)):
                c.create_rectangle(58, yy, 192, yy + 50, fill="#d9d4e8", outline="#8b86a0", width=2)
                c.create_rectangle(105, yy + 36, 145, yy + 42, fill="#8b86a0", outline="")
            self.txt(125, 280, "CONTRATOS", 9, INK)
            self.txt(125, 338, "VIDEOVIGILANCIA", 8, INK)
        elif i == "autor":
            c.create_rectangle(860, 224, 1040, 352, fill="#b9895a", outline="#8a6a43", width=3)
            c.create_rectangle(870, 234, 1030, 342, fill="#bfe3f0", outline="")
            c.create_oval(980, 244, 1010, 274, fill="#fbe7a8", outline="")
            c.create_polygon(870, 342, 930, 290, 990, 342, fill="#9fcf9d", outline="")
            c.create_oval(922, 300, 950, 328, fill="#f4b883", outline="")
            c.create_polygon(924, 304, 930, 292, 936, 304, fill="#f4b883", outline="")
            c.create_polygon(936, 304, 942, 292, 948, 304, fill="#f4b883", outline="")
            self.txt(1018, 334, "©?", 8, INK2)
        c.create_rectangle(x1 - 4, y1 - 4, x2 + 4, y2 + 4, outline=GOLD, width=4, state="hidden", tags=(f"hl{k}",))
        if k in self.run["res"]:
            p = self.run["res"][k]
            cx, cy = x2 - 4, y1 + 6
            c.create_oval(cx - 14, cy - 14, cx + 14, cy + 14, fill=MINT if p == 10 else BUTTER if p >= 5 else CORAL,
                          outline=INK2, width=2)
            self.txt(cx, cy, "✓" if p == 10 else "!" if p >= 5 else "✗", 12)
        self.zona(x1, y1, x2, y2, lambda k=k: self.hs_abrir(k),
                  enter=lambda: c.itemconfigure(f"hl{k}", state="disabled"),
                  leave=lambda: c.itemconfigure(f"hl{k}", state="hidden"))

    def pista(self):
        r = self.run
        pend = [k for k in range(len(HOT)) if k not in r["res"]]
        if r["pistas"] <= 0 or not pend:
            return
        r["pistas"] -= 1
        k = pend[0]
        self.inspeccion()
        self.c.itemconfigure(f"hl{k}", state="disabled")

        def ocultar():
            try:
                self.c.itemconfigure(f"hl{k}", state="hidden")
            except tk.TclError:
                pass
        self.after(2200, ocultar)

    def hs_abrir(self, k):
        r = self.run
        h = HOT[k]
        c = self.c
        c.delete("modal")
        if k not in r["opts"]:
            r["opts"][k] = random.sample(h["o"], len(h["o"]))
        d = DIST[1]
        self.capa_ini()
        self.panel(110, 86, 990, 556, shade(d["col"], 0.2))
        self.pill(130, 102, 970, 140, d["col"], h["t"], 13, anchor="w")
        it = self.txt(134, 152, h["x"], 12, INK, False, anchor="nw", width=830)
        y = c.bbox(it)[3] + 10
        if "code" in h:
            n = h["code"].count("\n") + 1
            c.create_rectangle(134, y, 966, y + 14 + n * 18, fill="#2f2f45", outline="#1c1c2c", width=2)
            c.create_text(146, y + 8, text=h["code"], font=("Consolas", 10), fill="#9fe3b0", anchor="nw")
            y += 14 + n * 18 + 10
        if k in r["sel"]:
            opt = r["sel"][k]
            pts = opt[1]
            color = MINT if pts == 10 else BUTTER if pts >= 5 else CORAL
            head = ("¡Excelente decisión!" if pts == 10 else
                    "Buen intento, puedes mejorar" if pts >= 5 else "¡Cuidado con esa decisión!")
            self.panel(130, y, 970, 500, shade(color, 0.3), fill=light(color, 0.6))
            self.txt(150, y + 22, f"{head}  +{pts} pts", 13, anchor="w")
            yy = y + 44
            partes = [("Consecuencia: ", opt[2])]
            if pts < 10:
                partes.append(("Mejor decisión: ", max(h["o"], key=lambda z: z[1])[0]))
            partes.append(("Fundamento: ", h["f"]))
            for et, cu in partes:
                t2 = self.txt(150, yy, et + cu, 11, INK, False, anchor="nw", width=800)
                yy = c.bbox(t2)[3] + 8
            self.button(700, 508, 970, 548, "Continuar ▶", self.hs_cerrar, MINT, fs=13)
        else:
            self.txt(134, y, "¿Qué norma o derecho está en juego y qué decides?", 11, INK2, anchor="nw")
            y += 28
            for j, o in enumerate(r["opts"][k]):
                self.opcion(130, y, 970, y + 58, "ABC"[j], o[0], d["col"], lambda j=j: self.hs_resp(k, j), fs=11)
                y += 66
        self.capa_fin("modal")

    def hs_resp(self, k, j):
        r = self.run
        opt = r["opts"][k][j]
        r["sel"][k] = opt
        if k not in r["res"]:
            r["res"][k] = opt[1]
            self.registrar(1, HOT[k]["id"], opt[1])
            if opt[1] < 10:
                r["errores"].append(HOT[k]["t"])
            self.guardar()
        self.hs_abrir(k)

    def hs_cerrar(self):
        if len(self.run["res"]) >= len(HOT):
            self.insp_fin()
        else:
            self.inspeccion()

    def insp_fin(self):
        r = self.run
        for k, h in enumerate(HOT):
            if k not in r["res"]:
                r["errores"].append(h["t"])
        self.terminar(1, sum(r["res"].values()), r["max"], r["errores"])

    # ======================= D3 · TRIBUNAL =======================
    def trib_iniciar(self):
        sel = []
        for cat, n in (("E", 3), ("I", 3), ("D", 3)):
            sel += random.sample([x for x in CARTAS if x["cat"] == cat], n)
        sel.append(random.choice([x for x in CARTAS if x not in sel]))
        random.shuffle(sel)
        self.run = {"u": 2, "cards": sel, "i": 0, "pts": 0, "max": 10 * len(sel), "racha": 0, "aciertos": 0,
                    "errores": [], "res": [], "kinds": [random.choice(["troll", "auditor", "hacker", "algo"]) for _ in sel]}
        self.tribunal()

    def tribunal(self, fb=None):
        r = self.run
        c = self.c
        d = DIST[2]
        carta = r["cards"][r["i"]]
        ci = [b[0] for b in BINS].index(carta["cat"])
        self.draw_bg()
        self.barra(2, f"Expediente {r['i'] + 1}/{len(r['cards'])}", f"{r['pts']} pts")
        mood = "neutral" if fb is None else ("happy" if fb["ok"] else "sad")
        frase = "¡Orden en la corte!" if fb is None else ("¡Caso cerrado!" if fb["ok"] else "Revisemos el expediente…")
        vistos = r["i"] + (1 if fb else 0)
        self.michi_card(mood, frase, [(f"Racha: {r['racha']}", min(100, r["racha"] * 25), MINT),
                                      (f"Aciertos: {r['aciertos']}/{vistos}", 100 * r["aciertos"] / max(1, vistos), None)],
                        peluca=True, nombre="JUEZA MICHI")
        # expediente
        self.panel(264, 72, 836, 250, d["col"])
        self.pill(280, 84, 820, 116, d["col"], f"Expediente #{r['i'] + 101}: {carta['t']}", 12, anchor="w")
        self.txt(284, 130, carta["x"], 13, INK, False, anchor="nw", width=430)
        self.raton(776, 190, 0.62, r["kinds"][r["i"]], hurt=bool(fb and fb["ok"]))
        self.txt(790, 242, "El acusado", 9, INK2, False)
        # veredictos
        for j, (k, nom, sub, col) in enumerate(BINS):
            x1 = 264 + 194 * j
            if fb is None:
                self.button(x1, 262, x1 + 184, 352, nom, lambda j=j: self.veredicto(j), col, sub, fs=14)
            else:
                if j == ci:
                    fill, mark = MINT, "✓ "
                elif j == fb["j"]:
                    fill, mark = CORAL, "✗ "
                else:
                    fill, mark = "#eadfcc", ""
                self.rrect(x1, 262, x1 + 184, 352, 14, fill=fill, outline=shade(fill, 0.35), width=3)
                self.txt(x1 + 92, 296, mark + nom, 14)
                self.txt(x1 + 92, 326, sub, 9, INK2, False, width=168)
        if fb is not None:
            color = MINT if fb["ok"] else CORAL
            self.panel(264, 364, 836, 570, shade(color, 0.3), fill=light(color, 0.6))
            self.txt(284, 386, ("¡Correcto! " if fb["ok"] else "Veredicto incorrecto. ") + f"Es: {BINS[ci][1]}", 13, anchor="w")
            y = 406
            for et, cu in (("Fundamento: ", carta["f"]), ("Sanción: ", carta["s"]), ("Prevención: ", carta["p"])):
                it = self.txt(284, y, et + cu, 10, INK, False, anchor="nw", width=536)
                y = c.bbox(it)[3] + 6
            ultimo = r["i"] + 1 >= len(r["cards"])
            self.button(544, 580, 836, 624, "Ver resultado ▶" if ultimo else "Siguiente expediente ▶",
                        self.trib_next, MINT, fs=13)
        else:
            self.txt(550, 400, "Clasifica el expediente: ¿falta ética, infracción o delito?", 13, INK2)
            self.txt(550, 430, "Pista: pregúntate quién puede sancionar la conducta y con qué ley.", 11, INK2, False)
        # guía de la jueza
        self.panel(850, 72, 1080, 626, MINT)
        self.txt(965, 96, "Guía de la jueza", 14)
        guia = {"E": "Daña valores y normas profesionales, pero no tiene sanción legal directa. Ej.: un meme humillante.",
                "I": "Incumple una ley administrativa o civil; la sanciona una autoridad (PROFECO, IMPI, datos).",
                "D": "Está tipificado en el Código Penal o en leyes como la Ley Olimpia: prisión y multa."}
        for j, (k, nom, sub, col) in enumerate(BINS):
            y = 114 + j * 108
            self.rrect(862, y, 1068, y + 98, 10, fill=light(col, 0.5), outline=shade(col, 0.35), width=2)
            self.txt(965, y + 16, nom, 11)
            self.txt(872, y + 32, guia[k], 9, INK, False, anchor="nw", width=186)
        self.txt(965, 456, "Marcos: Convenio de Budapest (2001) · UNESCO IA (2021) · Reglamento UE de IA (2024)",
                 8, INK2, False, width=190)
        for q in range(len(r["cards"])):
            cx, cy = 880 + (q % 5) * 40, 520 + (q // 5) * 34
            st = r["res"][q] if q < len(r["res"]) else None
            fill = "#e6dccb" if st is None else MINT if st else CORAL
            c.create_oval(cx - 13, cy - 13, cx + 13, cy + 13, fill=fill, outline=shade(fill, 0.3), width=2)
            self.txt(cx, cy, "✓" if st else "✗" if st is not None else str(q + 1), 9)

    def veredicto(self, j):
        r = self.run
        carta = r["cards"][r["i"]]
        ok = BINS[j][0] == carta["cat"]
        pts = 10 if ok else 0
        r["pts"] += pts
        r["res"].append(1 if ok else 0)
        if ok:
            r["racha"] += 1
            r["aciertos"] += 1
        else:
            r["racha"] = 0
            r["errores"].append(carta["t"])
        self.registrar(2, carta["id"], pts)
        self.guardar()
        self.tribunal({"j": j, "ok": ok})

    def trib_next(self):
        r = self.run
        r["i"] += 1
        if r["i"] >= len(r["cards"]):
            self.terminar(2, r["pts"], r["max"], r["errores"])
        else:
            self.tribunal()

    # ======================= D4 · LABORATORIO =======================
    def lab_iniciar(self):
        self.run = {"u": 3, "tab": 0, "res": {}, "ans": {}, "fb": None, "max": 10 * len(LAB), "errores": []}
        self.lab()

    def lab_tab(self, t):
        self.run["tab"] = t
        self.lab()

    def lab(self):
        r = self.run
        c = self.c
        d = DIST[3]
        self.draw_bg()
        self.barra(3, f"Revisión {len(r['res'])}/{len(LAB)}", f"{sum(r['res'].values())} pts")
        fb = r["fb"]
        mood = "neutral" if fb is None else ("happy" if fb[2] else "sad")
        frase = "Revisemos cada punto" if fb is None else ("¡Bien hecho!" if fb[2] else "Mmm… revisa esto")
        cumpl = round(100 * sum(r["res"].values()) / (10 * len(LAB)))
        self.michi_card(mood, frase, [(f"Cumplimiento {cumpl}%", cumpl, None)], nombre="MICHI QA")
        for t, nom in enumerate(LAB_TABS):
            x1 = 264 + 144 * t
            na = sum(1 for e in LAB if e["tab"] == t and e["id"] in r["res"])
            tot = sum(1 for e in LAB if e["tab"] == t)
            self.button(x1, 72, x1 + 140, 114, f"{nom} ({na}/{tot})", lambda t=t: self.lab_tab(t),
                        PEACH if t == r["tab"] else CARD, fs=9)
        self.panel(264, 122, 836, 468, shade(d["col"], 0.2))
        y = 134
        for e in [e for e in LAB if e["tab"] == r["tab"]]:
            y = self.lab_fila(e, y)
        # retroalimentación
        self.panel(264, 478, 836, 570, shade(d["col"], 0.2))
        if fb is None:
            self.txt(550, 524, "Responde cada punto del checklist. Recibirás el fundamento al instante.", 11, INK2, False)
        else:
            self.txt(284, 494, ("✓ Correcto" if fb[2] else "✗ Revisa este punto") + " · " + fb[0], 10, anchor="w", width=540)
            self.txt(284, 516, fb[1], 10, INK, False, anchor="nw", width=540)
        faltan = len(LAB) - len(r["res"])
        if faltan == 0:
            self.button(544, 580, 836, 624, "¡Lanzar app! ▶", self.lab_lanzar, MINT, fs=14)
        else:
            self.rrect(544, 580, 836, 624, 14, fill="#eadfcc", outline=BORDER, width=2)
            self.txt(690, 602, f"Faltan {faltan} decisiones", 12, INK2)
        # sellos
        self.panel(850, 72, 1080, 626, PEACH)
        self.txt(965, 98, "Sellos de cumplimiento", 12)
        for q, e in enumerate(LAB):
            cx, cy = 886 + (q % 4) * 52, 146 + (q // 4) * 52
            st = r["res"].get(e["id"])
            fill = "#e6dccb" if st is None else MINT if st == 10 else CORAL
            c.create_oval(cx - 19, cy - 19, cx + 19, cy + 19, fill=fill, outline=shade(fill, 0.3), width=2)
            self.txt(cx, cy, "✓" if st == 10 else "✗" if st is not None else str(q + 1), 11)
        self.txt(965, 466, "Gris: pendiente\nVerde: primera respuesta correcta\nRojo: primera respuesta incorrecta",
                 9, INK2, False, width=200)
        self.txt(965, 548, "Puedes cambiar una respuesta para ver su fundamento, pero los puntos cuentan la primera.",
                 9, INK2, False, width=200)

    def lab_fila(self, e, y):
        r = self.run
        c = self.c
        st = r["ans"].get(e["id"])
        if st is None:
            bg = CARD
            ok = None
        else:
            ok = (e["opts"][st][1] == 10) if e["tipo"] == "radio" else (st == e["c"])
            bg = light(MINT, 0.4) if ok else light(CORAL, 0.4)
        if e["tipo"] == "radio":
            c.create_rectangle(274, y, 826, y + 100, fill=bg, outline=BORDER)
            self.txt(284, y + 8, e["q"], 10, INK, True, anchor="nw", width=530)
            for j, (corto, pts, fbt) in enumerate(e["opts"]):
                x1 = 284 + 180 * j
                col = (MINT if ok else CORAL) if st == j else CARD
                self.mini(x1, y + 46, x1 + 174, y + 92, corto, col, lambda j=j, e=e: self.lab_resp(e, j), fs=9)
            return y + 106
        c.create_rectangle(274, y, 826, y + 48, fill=bg, outline=BORDER)
        self.txt(284, y + 24, e["q"], 10, INK, False, anchor="w", width=350)
        for val, nom, x1 in ((True, "Sí", 650), (False, "No", 738)):
            col = (MINT if ok else CORAL) if st is val else CARD
            self.mini(x1, y + 6, x1 + 78, y + 42, nom, col, lambda v=val, e=e: self.lab_resp(e, v), fs=12)
        return y + 54

    def lab_resp(self, e, val):
        r = self.run
        r["ans"][e["id"]] = val
        if e["tipo"] == "radio":
            ok = e["opts"][val][1] == 10
            txt = e["opts"][val][2]
        else:
            ok = (val == e["c"])
            txt = e["ok"] if ok else e["bad"]
        if e["id"] not in r["res"]:
            pts = 10 if ok else 0
            r["res"][e["id"]] = pts
            self.registrar(3, e["id"], pts)
            if not ok:
                r["errores"].append(e["t"])
            self.guardar()
        r["fb"] = (e["t"], txt, ok)
        self.lab()

    def lab_lanzar(self):
        r = self.run
        self.terminar(3, sum(r["res"].values()), r["max"], r["errores"])

    # ======================= RESULTADOS, ÁLBUM, CERTIFICADO =======================
    def resultados(self, u, pts, mx, pct, errores, dead=False):
        d = DIST[u]
        win = pct >= 60 and not dead
        self.draw_bg()
        if win:
            rnd = random.Random(3)
            for _ in range(40):
                x, y = rnd.randint(10, W - 10), rnd.randint(8, 400)
                sz = rnd.randint(6, 12)
                self.c.create_oval(x, y, x + sz, y + sz, fill=rnd.choice([PINK, BUTTER, MINT, SKY, LAV, PEACH]), outline="")
        self.panel(250, 16, 850, 100, MINT if win else CORAL)
        titulo = ("¡Distrito completado!" if win else "¡Sigue practicando!")
        self.txt(550, 58, titulo, 28)
        self.panel(20, 114, 260, 540, SKY)
        self.plataforma(140, 440, 82, PINK)
        self.gato(140, 300, 1.5, "happy" if win else "sad", salto=win)
        self.txt(140, 486, self.prog["alias"].upper(), 13)
        self.txt(140, 508, "¡Lo logramos!" if win else "Ánimo, ¡otra vez!", 10, INK2, False)
        self.panel(840, 114, 1080, 540, CORAL)
        self.plataforma(960, 440, 82, light(CORAL, 0.2))
        self.raton(960, 300, 1.5, d["enem"], hurt=win)
        self.txt(960, 486, "El jefe del distrito", 12)
        self.txt(960, 508, "Derrotado" if win else "Sigue en pie", 10, INK2, False)
        self.panel(276, 114, 824, 540, shade(d["col"], 0.2))
        if dead:
            msg = "Uno de tus indicadores llegó a 0 y perdiste la confianza del equipo."
        elif win:
            msg = ("Superaste los dilemas éticos de la Casa de la Moral.", "La oficina quedó en regla.",
                   "¡Caso cerrado, Su Señoría!", "¡Lanzamiento responsable!")[u]
        else:
            msg = "Repasa los fundamentos y vuelve a intentarlo."
        self.txt(550, 148, msg, 11, INK, False, width=500)
        self.txt(550, 196, f"Puntaje: {pts}/{mx}  ({pct}%)", 20)
        self.txt(550, 232, desempeno(pct), 12, INK2)
        self.txt(550, 286, self.estr_txt(self.estrellas_u(u)), 40, GOLD)
        self.txt(550, 328, "Estrellas del distrito (según tu mejor partida)", 9, INK2, False)
        if errores:
            self.txt(300, 360, "Para repasar: " + "; ".join(errores), 10, INK, False, anchor="nw", width=500)
        self.txt(550, 518, "Tus huellitas están en el Álbum", 9, INK2, False)
        botones = []
        if win and u < 3:
            botones.append(("Siguiente distrito", lambda: self.intro(u + 1), MINT))
        botones.append(("Reintentar", lambda: self.entrar(u), PEACH))
        botones.append(("Mapa", self.menu, PINK))
        n = len(botones)
        ancho = 240
        x0 = 550 - (n * ancho + (n - 1) * 20) / 2
        for k, (lab, cmd, colr) in enumerate(botones):
            x1 = x0 + k * (ancho + 20)
            self.button(x1, 560, x1 + ancho, 620, lab, cmd, colr, fs=14)

    def album(self, u=None):
        if u is not None:
            self.alb_u = u
        u = self.alb_u
        d = DIST[u]
        items = album_items(u)
        got = sum(1 for it in items if self.prog["best"].get(f"{u}:{it[0]}", 0) == 10)
        self.draw_bg()
        self.pill(20, 16, 270, 58, BUTTER, f"Álbum · {got}/{len(items)}", 14)
        for k in range(4):
            self.button(286 + 156 * k, 16, 286 + 156 * k + 146, 58, f"Distrito {DIST[k]['u']}",
                        lambda k=k: self.album(k), DIST[k]["col"] if k == u else CARD, fs=11)
        self.button(912, 16, 1080, 58, "Mapa", self.menu, LAV, fs=12)
        self.pill(20, 70, 1080, 100, d["col"], f"{d['n']} · {d['modo']}", 11)
        self.panel(25, 396, 1075, 628, shade(d["col"], 0.2))
        det = self.txt(45, 412, "Toca una huellita para ver su fundamento. Se desbloquea al elegir la mejor "
                       "decisión (10 pts).", 11, INK, False, anchor="nw", width=1010)
        for k, (id_, titulo, fund) in enumerate(items):
            col_, row = k % 4, k // 4
            x1 = 25 + col_ * 265
            y1 = 110 + row * 46
            ok = self.prog["best"].get(f"{u}:{id_}", 0) == 10
            if ok:
                lab = titulo if len(titulo) <= 34 else titulo[:32] + "…"
                txt = f"{titulo}\n\n{fund}"
                color = d["col"]
            else:
                lab = "???"
                txt = "Huellita bloqueada. Elige la mejor decisión (10 pts) en este punto para desbloquearla."
                color = LOCK
            self.mini(x1, y1, x1 + 255, y1 + 40, lab, color, lambda t=txt: self.c.itemconfigure(det, text=t), fs=10)

    def certificado(self):
        self.draw_bg()
        self.panel(40, 20, 1060, 610, GOLD)
        self.txt(550, 54, "Certificado del Consejo Felino", 24)
        self.txt(550, 88, f"{self.prog['alias']} · {self.rango()}", 13, INK2)
        pcts = [self.pct_u(u) for u in range(4)]
        for k in range(4):
            y = 128 + k * 74
            d = DIST[k]
            self.txt(80, y, f"Distrito {d['u']} · {d['n']}", 13, anchor="w")
            self.txt(80, y + 20, d["tema"], 9, INK2, False, anchor="w")
            self.bar(80, y + 36, 640, pcts[k], None, d["col"], h=16)
            self.txt(660, y + 44, f"{pcts[k]}%", 13, anchor="w")
            self.txt(740, y + 40, self.estr_txt(self.estrellas_u(k)), 20, GOLD, anchor="w")
        prom = round(sum(pcts) / 4)
        self.txt(80, 440, f"Promedio general: {prom}%", 18, anchor="w")
        self.txt(80, 474, f"Nivel de desempeño: {desempeno(prom)}", 14, INK2, anchor="w")
        faltan = [DIST[k]["n"] for k in range(4) if pcts[k] == 0]
        msg = ("Aún no juegas: " + ", ".join(faltan) + ".") if faltan else (
            "¡Sintetizaste las 4 unidades! Sigue mejorando tu puntaje en cada distrito.")
        self.txt(80, 508, msg, 11, INK, False, anchor="w", width=600)
        self.txt(80, 548, "Escala: 90-100 Estratégico · 80-89 Autónomo · 70-79 Básico · <70 No acreditado",
                 9, INK2, False, anchor="w")
        self.gato(930, 470, 0.9, "happy")
        self.button(450, 560, 650, 604, "Volver", self.menu, PINK, fs=14)

    def ajustes(self):
        self.draw_bg()
        self.panel(300, 20, 800, 612, LAV)
        self.txt(550, 56, "Ajustes", 24, INK)
        g = "activado" if self.prog["consent"] else "desactivado (modo sin guardar)"
        self.txt(550, 92, f"Jugador: {self.prog['alias']}  ·  Guardado local: {g}", 10, INK2, False, width=460)
        an = self.prog.get("anim", True)
        self.button(340, 124, 760, 184, f"Animaciones: {'sí' if an else 'no (más rápido)'}", self.alt_anim, PEACH, fs=14)
        self.button(340, 204, 760, 264, "Cambiar alias", self.cambiar_alias, MINT, fs=14)
        self.button(340, 284, 760, 344, "Aviso de privacidad y términos", lambda: self.privacidad(False),
                    BUTTER, fs=13)
        self.button(340, 364, 760, 424, "Borrar mi progreso (ARCO)", self.borrar, CORAL, fs=14)
        self.button(340, 530, 760, 590, "Volver", self.menu, PINK, fs=14)

    # ---------- ventanas propias del juego (en lugar de los cuadros grises del sistema)
    def bloqueo(self):
        """Capa invisible que impide hacer clic en lo que queda debajo de una ventana."""
        self.c.create_rectangle(0, 0, W, H, fill="", outline="")

    def cambiar_alias(self):
        self._alias_buf = ""
        self.capa_ini()
        self.bloqueo()
        self.panel(310, 180, 790, 430, shade(LAV, 0.25), fill=light(LAV, 0.55))
        self.txt(550, 216, "Nuevo alias", 20)
        self.txt(550, 246, f"Ahora eres «{self.prog['alias']}». Escribe con el teclado (máx. 16 letras).", 10, INK2, False)
        self.c.create_rectangle(350, 270, 750, 312, fill=CARD, outline=shade(LAV, 0.4), width=3)
        campo = self.txt(364, 291, "_", 14, INK, False, anchor="w")
        self.txt(550, 334, "Enter = guardar · Esc = cancelar", 9, INK2, False)
        self.button(340, 358, 540, 410, "Guardar", self.alias_guardar, MINT, fs=14)
        self.button(560, 358, 760, 410, "Cancelar", self.alias_cancelar, PINK, fs=14)
        self.capa_fin("modal")

        def on_key(ev):
            if ev.keysym == "Return":
                self.alias_guardar()
                return
            if ev.keysym == "Escape":
                self.alias_cancelar()
                return
            if ev.keysym == "BackSpace":
                self._alias_buf = self._alias_buf[:-1]
            elif ev.char and ev.char.isprintable() and len(self._alias_buf) < 16:
                self._alias_buf += ev.char
            try:
                self.c.itemconfig(campo, text=self._alias_buf + "_")
            except tk.TclError:
                pass

        self.c.bind("<Key>", on_key)
        self.c.focus_force()

    def alias_guardar(self):
        a = getattr(self, "_alias_buf", "").strip()
        if a:
            self.prog["alias"] = a[:16]
            self.guardar()
        self.ajustes()

    def alias_cancelar(self):
        self.ajustes()

    def borrar(self):
        self.capa_ini()
        self.bloqueo()
        self.panel(310, 170, 790, 440, shade(CORAL, 0.25), fill=light(CORAL, 0.55))
        self.txt(550, 208, "Borrar mi progreso", 20)
        self.txt(550, 280, "Se borrarán tus puntos, estrellas y huellitas, y el archivo local de "
                 "progreso.\n\nEsta acción no se puede deshacer.", 11, INK, False, width=420)
        self.button(340, 366, 540, 418, "Sí, borrar", self.borrar_ok, CORAL, fs=14)
        self.button(560, 366, 760, 418, "Cancelar", self.ajustes, MINT, fs=14)
        self.capa_fin("modal")

    def borrar_ok(self):
        try:
            os.remove(SAVE)
        except OSError:
            pass
        self.prog = {"consent": None, "alias": "MICHI", "best": {}, "runbest": {}, "anim": True}
        self.privacidad(True)


def main():
    print(f"Iniciando Gatópolis... (Python {sys.version.split()[0]})")
    try:
        root = tk.Tk()
        App(root)
        root.mainloop()
    except Exception:
        import traceback
        err = traceback.format_exc()
        print("\n*** OCURRIÓ UN ERROR ***\n" + err)
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gatopolis_error.txt"),
                      "w", encoding="utf-8") as f:
                f.write(err)
            print("El error se guardó en gatopolis_error.txt")
        except OSError:
            pass
        try:
            input("\nPresiona Enter para cerrar...")
        except EOFError:
            pass
        sys.exit(1)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
