# Genera PS XMB/fondos/simbolos-ps5.css: simbolos de PlayStation en contorno y
# particulas de luz que suben despacio, como la pantalla de arranque de la PS5.
# Cada capa es un mosaico que se repite; sube exactamente un mosaico por ciclo.
import math, random, sys

def simbolo(tipo, x, y, t, op, giro):
    g = f"transform='rotate({giro:.0f} {x:.0f} {y:.0f})' stroke-opacity='{op}'"
    if tipo == 0:  # triangulo
        h = t * 0.87
        return f"<path d='M{x:.0f} {y - h*0.6:.0f} L{x + t/2:.0f} {y + h*0.4:.0f} L{x - t/2:.0f} {y + h*0.4:.0f} Z' {g}/>"
    if tipo == 1:  # circulo
        return f"<circle cx='{x:.0f}' cy='{y:.0f}' r='{t/2:.0f}' {g}/>"
    if tipo == 2:  # tache
        d = t / 2
        return f"<path d='M{x-d:.0f} {y-d:.0f} L{x+d:.0f} {y+d:.0f} M{x+d:.0f} {y-d:.0f} L{x-d:.0f} {y+d:.0f}' {g}/>"
    return f"<rect x='{x - t/2:.0f}' y='{y - t/2:.0f}' width='{t:.0f}' height='{t:.0f}' {g}/>"  # cuadro

def capa(semilla, W, H, n, tam, op, puntos, grosor):
    r = random.Random(semilla)
    partes = []
    for i in range(n):
        partes.append(simbolo(i % 4, r.uniform(40, W - 40), r.uniform(40, H - 40),
                              r.uniform(*tam), round(r.uniform(*op), 2), r.uniform(-25, 25)))
    for _ in range(puntos):
        partes.append(f"<circle cx='{r.uniform(0, W):.0f}' cy='{r.uniform(0, H):.0f}' r='{r.uniform(1, 2.5):.1f}' "
                      f"fill='white' stroke='none' fill-opacity='{r.uniform(0.3, 0.8):.2f}'/>")
    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' fill='none' stroke='white' "
            f"stroke-width='{grosor}' stroke-linejoin='round' stroke-linecap='round'>" + "".join(partes) + "</svg>")

lejos = capa(5, 700, 500, 12, (14, 30), (0.25, 0.5), 30, 1.5)
cerca = capa(9, 1100, 800, 6, (50, 90), (0.12, 0.25), 8, 2.5)

css = f"""/* Fondo estilo PS5: simbolos de PlayStation en contorno y particulas de luz que
   suben despacio, como la pantalla de arranque de la consola. Dos capas a distinta
   velocidad. Generado por simbolos_ps5.py; el color sale de --ps3-ola. */

body::before,
body::after {{
  content: "";
  position: fixed;
  left: 0;
  top: 0;
  width: 100%;
  height: 300%;
  pointer-events: none;
  z-index: 0;
  mix-blend-mode: screen;
  background-color: color-mix(in srgb, var(--ps3-ola, #ffffff) 70%, var(--ps3-claro));
  -webkit-mask-repeat: repeat;
  will-change: transform;
}}

/* capa lejana: simbolos chicos y puntos, lenta */
body::before {{
  -webkit-mask-size: 700px 500px;
  -webkit-mask-image: url("data:image/svg+xml;utf8,{lejos}");
  animation: ps5-lejos 70s linear infinite;
}}

/* capa cercana: simbolos grandes y tenues, un poco mas rapida */
body::after {{
  -webkit-mask-size: 1100px 800px;
  -webkit-mask-image: url("data:image/svg+xml;utf8,{cerca}");
  animation: ps5-cerca 45s linear infinite;
}}

/* cada capa sube exactamente un mosaico para que el ciclo no brinque */
@keyframes ps5-lejos {{
  from {{ transform: translateY(0); }}
  to {{ transform: translateY(-500px); }}
}}

@keyframes ps5-cerca {{
  from {{ transform: translateY(0); }}
  to {{ transform: translateY(-800px); }}
}}
"""
open(sys.argv[1], "w").write(css)
