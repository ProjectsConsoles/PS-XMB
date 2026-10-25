# Genera PS XMB/fondos/orbes-ps2.css: los 7 orbes del menu de la PS2, sacados de
# una grabacion de la consola. Van sobre un mismo aro que gira rapido y se voltea
# en 3D; en un ciclo de 20 s pasan de aro parejo a arco, a una sola bola, y de
# vuelta a arco y aro. Cada orbe es una capa de fondo y una sola animacion mueve
# las 7 capas; la segunda capa repite el vuelo atrasado como estela.
import math, sys

N = 7
CAJA = 280          # px del recuadro donde vuelan
R = 80              # radio del aro
T = 20              # segundos por ciclo completo
VUELTAS = 8         # vueltas del aro por ciclo (2.5 s cada una, como la consola)
PASOS = 240         # cuadros clave por ciclo (12 por segundo)
TAM = 40            # tamano del halo de un orbe al frente

def suave(a, b, t):
    """0 antes de a, 1 despues de b, curva suave entre medio"""
    x = min(1, max(0, (t - a) / (b - a)))
    return x * x * (3 - 2 * x)

def separacion(seg):
    """fraccion del aro entre orbe y orbe en el segundo seg del ciclo:
    1/7 = aro parejo, ~1/16 = arco, 0 = una sola bola"""
    aro, arco = 1 / N, 1 / 16
    s = aro
    s += (arco - aro) * suave(5, 9, seg)        # se cierra en arco
    s += (0 - arco) * suave(11, 12.5, seg)       # termina en bola
    s += (arco - 0) * suave(15, 16.5, seg)       # se abre en arco
    s += (aro - arco) * suave(17, 20, seg)       # vuelve al aro
    return s

def cuadro(t):
    seg = t * T
    s = separacion(seg)
    base = 2 * math.pi * VUELTAS * t
    # el aro se voltea: su inclinacion sube y baja y a la vez gira de lado
    incl = math.radians(50 + 35 * math.sin(2 * math.pi * 2 * t))
    lado = 2 * math.pi * t
    pos, tam = [], []
    for i in range(N):
        th = base - 2 * math.pi * s * (i - (N - 1) / 2)
        x, y, z = R * math.cos(th), R * math.sin(th), 0.0
        y, z = y * math.cos(incl), y * math.sin(incl)
        x, y = x * math.cos(lado) - y * math.sin(lado), x * math.sin(lado) + y * math.cos(lado)
        esc = 360 / (360 - z)
        sz = TAM * esc * (0.8 + 0.2 * (z + R) / (2 * R))
        pos.append(f"{CAJA / 2 + x * esc - sz / 2:.1f}px {CAJA / 2 + y * esc - sz / 2:.1f}px")
        tam.append(f"{sz:.1f}px {sz:.1f}px")
    return ", ".join(pos), ", ".join(tam)

orbe = ("radial-gradient(circle, #ffffff 0, #ffffff 9%, var(--psx-orbe) 20%, "
        "color-mix(in srgb, var(--psx-orbe) 35%, transparent) 38%, transparent 68%)")
capas = ", ".join([orbe] * N)
claves = "\n".join(
    f"  {100 * i / PASOS:.3f}% {{ background-position: {p}; background-size: {s}; }}"
    for i in range(PASOS + 1) for p, s in [cuadro(i / PASOS)])

css = f"""/* Fondo estilo PS2: los 7 orbes del menu de la PS2. Van sobre un aro que gira y se
   voltea en 3D y en cada ciclo pasan de aro parejo a arco, a una bola, y de vuelta.
   Generado por orbes_ps2.py a partir de una grabacion de la consola; el color sale
   de --ps3-ola. */

:root {{
  --psx-orbe: color-mix(in srgb, var(--ps3-ola, #ffffff) 25%, #3fb4ff);
}}

body::before,
body::after {{
  content: "";
  position: fixed;
  /* en la parte de abajo, que el Inicio deja libre debajo de la fila */
  left: 50%;
  top: 68%;
  width: {CAJA}px;
  height: {CAJA}px;
  margin: -{CAJA // 2}px 0 0 -{CAJA // 2}px;
  pointer-events: none;
  /* detras de toda la interfaz: la imagen de fondo de un juego la tapa */
  z-index: -1;
  background-image: {capas};
  background-repeat: no-repeat;
  animation: ps2-orbes {T}s linear infinite;
}}

/* estela: el mismo vuelo un poquito atrasado (0.06 s), tenue. Un retraso negativo
   adelanta la animacion, por eso se usa casi un ciclo completo para quedar detras. */
body::after {{
  opacity: 0.3;
  filter: blur(1px);
  animation-delay: -{T - 0.06:.2f}s;
}}

@keyframes ps2-orbes {{
{claves}
}}
"""
open(sys.argv[1], "w").write(css)
