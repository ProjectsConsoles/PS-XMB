# Genera PS XMB/fondos/../extras/grid-ps2.css: acomoda la fila de juegos de Steam en
# una tabla, como el navegador de la memory card de la PS2.
#
# Steam pone cada tarjeta con un "left" fijo en su estilo (la primera en 0 y las
# demas desde 442.047px cada 146px). Con el estilo de tarjetas cuadradas la fila
# queda a 146px por tarjeta, asi que la tarjeta i esta en x = 146*i. Cada una se
# mueve con "translate" (aparte de "transform", que usa la animacion) a su columna
# y renglon. La navegacion arriba/abajo y el bloqueo del desplazamiento los pone
# controles/xmb_vertical.py al ver la marca --psx-grid.
import sys

COLUMNAS = 7
PASO = 146        # distancia entre tarjetas en la fila de Steam
COLUMNA = 178     # distancia entre columnas en la tabla (deja aire entre tarjetas)
ALTO = 235        # alto de cada renglon (tarjeta + reflejo + aire)
MAXIMO = 80       # tarjetas que cubre (Steam muestra unas 20)


def left(i):
    """el left que Steam escribe para la tarjeta i, con su formato de 6 cifras"""
    return "0px" if i == 0 else f"{442.047 + PASO * (i - 1):.6g}px"


reglas = []
for i in range(MAXIMO):
    dx = (i % COLUMNAS) * COLUMNA - PASO * i
    dy = (i // COLUMNAS) * ALTO
    reglas.append(f'.ReactVirtualized__Grid__innerScrollContainer > div[style*="left: {left(i)};"] '
                  f'{{ translate: {dx}px {dy}px; }}')

css = f"""/* Tabla de {COLUMNAS} columnas para la consola PS2, como el navegador de la memory
   card. Generado por herramientas/grid_ps2.py. */

/* marca para controles/xmb_vertical.py: arriba/abajo saltan un renglon */
.basicgamecarousel_BasicGameCarousel {{
  --psx-grid: {COLUMNAS};
  /* centrada y con alto para los renglones (Steam recorta lo que se sale) */
  transform: translateX(86px) scale(0.72) !important;
  height: 1000px !important;
}}

/* en la tabla las demas tarjetas no se recorren al seleccionar una... */
.ReactVirtualized__Grid__innerScrollContainer > .gpfocuswithin ~ div {{
  transform: none;
}}

.ReactVirtualized__Grid__innerScrollContainer > .gpfocuswithin ~ div:has(.basicgamecarousel_Featured) {{
  transform: translateX(296px);
}}

/* ...y la seleccionada crece desde su centro, sin tapar a las vecinas */
.ReactVirtualized__Grid__innerScrollContainer > .gpfocuswithin {{
  transform: scale(1.2);
  transform-origin: 67px 67px;
}}

.ReactVirtualized__Grid__innerScrollContainer > .gpfocuswithin:has(.basicgamecarousel_Featured) {{
  transform: translateX(296px) scale(1.2);
}}

""" + "\n".join(reglas) + "\n"
open(sys.argv[1], "w").write(css)
