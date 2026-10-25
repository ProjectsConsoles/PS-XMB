#!/usr/bin/env python3
"""Controles de la columna vertical del modo PS3 de PS XMB.

En PS3 la fila de juegos se ve como columna (se gira con CSS), pero Steam la sigue
manejando con izquierda/derecha. Este script mete en la interfaz de Steam un pequeno
traductor de botones: mientras la fila tenga la marca --psx-vertical (solo en PS3),
arriba/abajo se convierten en izquierda/derecha, e izquierda/derecha no hacen nada
(sacarian la seleccion de la columna). En las demas consolas no hace nada.

Steam borra el traductor cada vez que se reinicia su interfaz, asi que el servicio
revisa cada pocos segundos y lo vuelve a poner si hace falta. Se instala una vez:

    python3 ~/homebrew/themes/PS\\ XMB/controles/xmb_vertical.py --instalar-auto
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sonidos"))
from sonidos_por_modo import evaluar_en_steam  # noqa: E402

# botones de Steam: 9 arriba, 10 abajo, 11 izquierda, 12 derecha
TRADUCTOR = r"""
(() => {
  const VERSION = 2;
  if (window.__psxXmb === VERSION) return "ya estaba";
  // si hay una version anterior puesta, se quita su escucha antes de poner la nueva
  if (window.__psxXmbEscucha) window.removeEventListener("vgp_onbuttondown", window.__psxXmbEscucha, true);
  window.__psxXmb = VERSION;
  // arriba/abajo recorren la columna; izquierda/derecha (null) se ignoran
  const CAMBIO = {9: 11, 10: 12, 11: null, 12: null};
  window.__psxXmbEscucha = (e) => {
    const d = e.detail;
    if (!d || d.__psx || !(d.button in CAMBIO)) return;
    const fila = e.target.closest && e.target.closest(".ReactVirtualized__Grid");
    if (!fila || getComputedStyle(fila).getPropertyValue("--psx-vertical").trim() !== "si") return;
    // se detiene el boton original y se manda el traducido a la misma tarjeta
    e.stopImmediatePropagation();
    e.preventDefault();
    if (CAMBIO[d.button] === null) return;
    e.target.dispatchEvent(new CustomEvent("vgp_onbuttondown", {
      detail: {...d, button: CAMBIO[d.button], __psx: true}, bubbles: true, cancelable: true}));
  };
  // en window (fase de captura) para decidir antes que cualquier otra escucha
  window.addEventListener("vgp_onbuttondown", window.__psxXmbEscucha, true);
  return "puesto";
})()
"""


def es_interfaz(t):
    """la ventana principal del Modo Juego (su titulo cambia con el idioma)"""
    return "browserType=4" in t.get("url", "")


def poner():
    r = evaluar_en_steam(TRADUCTOR, es_interfaz)
    return r.get("result", {}).get("result", {}).get("value")


def instalar_auto():
    unidades = os.path.expanduser("~/.config/systemd/user")
    os.makedirs(unidades, exist_ok=True)
    script = os.path.abspath(__file__)
    open(os.path.join(unidades, "psxmb-controles.service"), "w").write(
        "[Unit]\nDescription=PS XMB: controles de la columna vertical (PS3)\n\n"
        f'[Service]\nExecStart=/usr/bin/python3 "{script}" --vigilar\nRestart=always\nRestartSec=10\n\n'
        "[Install]\nWantedBy=default.target\n")
    os.system("systemctl --user daemon-reload && systemctl --user enable --now psxmb-controles.service")
    print("Listo: en PS3 la columna se maneja con arriba y abajo.")


def main():
    if "--instalar-auto" in sys.argv:
        return instalar_auto()
    if "--vigilar" in sys.argv:
        while True:
            try:
                if poner() == "puesto":
                    print("traductor puesto en la interfaz de Steam", flush=True)
            except Exception:
                pass  # Steam todavia no arranca o se esta reiniciando
            time.sleep(5)
    print(poner())


if __name__ == "__main__":
    main()
