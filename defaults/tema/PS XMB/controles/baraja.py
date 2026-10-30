#!/usr/bin/env python3
"""Biblioteca en baraja (estilo Aurora) de PS XMB.

El CSS (extras/biblioteca-baraja.css) deja las tarjetas de la Biblioteca en una fila real,
10px una de otra, para que Steam siga sabiendo cual esta a la izquierda y a la derecha, y
las acomoda con transform: la seleccionada al centro y las demas a los lados. Para eso
cada tarjeta necesita saber su distancia a la seleccionada, y eso no se puede con CSS:
este script se la pone (--i, --d, --s, --ad, --c) cada vez que cambia la seleccion.

Tambien atrapa el boton A sobre una tarjeta: la portada gira y se va a la izquierda, y
despues le pasa el mismo boton a Steam para que abra el juego.

Solo trabaja mientras la cuadricula tenga la marca --psx-baraja (la pone el CSS cuando
la opcion "Biblioteca en baraja" esta activa); si no, no toca nada. El plugin lo vuelve
a poner cuando Steam reinicia su interfaz.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sonidos"))
from sonidos_por_modo import evaluar_en_steam  # noqa: E402
from xmb_vertical import es_interfaz  # noqa: E402

# botones de Steam: 1 A, 11 izquierda, 12 derecha
BARAJA = r"""
(() => {
  const VERSION = 9;
  if (window.__psxBaraja === VERSION) return "ya estaba";
  if (window.__psxBarajaTimer) clearInterval(window.__psxBarajaTimer);
  if (window.__psxBarajaObs) window.__psxBarajaObs.disconnect();
  if (window.__psxBarajaA) window.removeEventListener("vgp_onbuttondown", window.__psxBarajaA, true);
  window.__psxBaraja = VERSION;
  let grid = null, pendiente = false;
  const LADO = 7;
  const acomodar = () => {
    pendiente = false;
    if (!grid || !grid.isConnected) return;
    const cartas = grid.querySelectorAll(":scope > div > div > div");
    let f = -1;
    cartas.forEach((c, i) => { if (f < 0 && c.querySelector(".gpfocus")) f = i; });
    if (f < 0) f = Number(grid.dataset.psxFoco || 0);
    grid.dataset.psxFoco = f;
    // Steam desplaza la pestana de lado para "mostrar" la tarjeta con foco; la fila no se
    // mueve de lado (el CSS ya le quita el ancho de mas), asi que se regresa a 0
    const pestana = grid.closest("._TabContentsScroll");
    if (pestana && pestana.scrollLeft) pestana.scrollLeft = 0;
    grid.style.setProperty("--centro", Math.round(grid.clientWidth / 2) + "px");
    cartas.forEach((c, i) => {
      const d = i - f, ad = Math.abs(d);
      c.style.setProperty("--i", i);
      c.style.setProperty("--d", Math.max(-LADO, Math.min(LADO, d)));
      c.style.setProperty("--s", Math.sign(d));
      c.style.setProperty("--ad", ad);
      c.style.setProperty("--c", d === 0 ? 1 : 0);
    });
  };
  const pedir = () => { if (!pendiente) { pendiente = true; requestAnimationFrame(acomodar); } };
  const buscar = () => {
    const g = document.querySelector('div[style*="grid-auto-rows"]');
    const activa = g && getComputedStyle(g).getPropertyValue("--psx-baraja").trim() === "si";
    if (!activa) { if (grid) { window.__psxBarajaObs.disconnect(); grid = null; } return; }
    if (g !== grid) {
      grid = g;
      window.__psxBarajaObs.disconnect();
      window.__psxBarajaObs.observe(grid, {subtree: true, childList: true, attributes: true, attributeFilter: ["class"]});
      // la primera vez se colocan sin animacion; despues ya se deslizan
      delete grid.dataset.psxListo;
      acomodar();
      requestAnimationFrame(() => requestAnimationFrame(() => { if (grid) grid.dataset.psxListo = ""; }));
    }
  };
  // A sobre una tarjeta: se arma una copia en 3D de la caja fuera de la Biblioteca (Steam
  // borra la Biblioteca al abrir el juego), que gira sin parar mientras se va del mismo
  // tamano hasta salir por la izquierda, girando cada vez mas rapido. El boton se le pasa
  // a Steam casi al final, para que la caja ya no este cuando aparezca el juego. Las demas
  // tarjetas se apartan. A medio vuelo se le pasa el mismo boton a Steam.
  if (!document.getElementById("psx-vuelo-css")) {
    const css = document.createElement("style");
    css.id = "psx-vuelo-css";
    css.textContent = `
      .psx-vuelo { position: fixed; z-index: 99999; pointer-events: none; perspective: 1400px;
        animation: psx-vuelo-ir 0.75s cubic-bezier(.5, 0, .9, .6) forwards; }
      .psx-vuelo .psx-caja { position: absolute; inset: 0; transform-style: preserve-3d;
        animation: psx-vuelo-girar 0.75s cubic-bezier(.55, 0, 1, .7) forwards; }
      .psx-vuelo .psx-cara { position: absolute; top: 0; height: 100%; backface-visibility: hidden;
        border-radius: 6px; overflow: hidden; background: #0b0e13 center / cover no-repeat; }
      .psx-vuelo .psx-franja { position: absolute; left: 0; right: 0; top: 0; height: 7%;
        background: linear-gradient(180deg, #2a475e, #171a21); border-bottom: 2px solid #66c0f4;
        color: #fff; font: 800 19px/1 Arial, sans-serif; letter-spacing: 4px;
        display: flex; align-items: center; justify-content: center; }
      .psx-vuelo .psx-lomo { border-radius: 3px;
        background: linear-gradient(90deg, #0d1219, #3c4b5e 35%, #56677c 50%, #2a3646 70%, #0d1219); }
      @keyframes psx-vuelo-girar { from { transform: rotateY(0deg); } to { transform: rotateY(-1260deg); } }
      @keyframes psx-vuelo-ir {
        from { transform: none; }
        to { transform: translateX(var(--psx-salida)); }
      }`;
    document.head.appendChild(css);
  }
  const vuelo = (carta) => {
    const r = carta.getBoundingClientRect();
    const img = carta.querySelector("img");
    const conCaja = getComputedStyle(carta, "::after").content.includes("STEAM");
    const w = r.width, h = r.height, t = Math.round(w * (conCaja ? 0.27 : 0.05));
    const v = document.createElement("div");
    v.className = "psx-vuelo";
    Object.assign(v.style, {left: r.left + "px", top: r.top + "px", width: w + "px", height: h + "px"});
    // lo que le falta para salir completa por el borde izquierdo
    v.style.setProperty("--psx-salida", -(r.left + w + 80) + "px");
    const caja = document.createElement("div");
    caja.className = "psx-caja";
    const cara = (ancho, transform, clase) => {
      const c = document.createElement("div");
      c.className = "psx-cara " + (clase || "");
      Object.assign(c.style, {width: ancho + "px", left: (w - ancho) / 2 + "px", transform});
      caja.appendChild(c);
      return c;
    };
    const portada = img ? `url("${img.src}")` : "none";
    const frente = cara(w, `translateZ(${t / 2}px)`);
    frente.style.backgroundImage = portada;
    if (conCaja) {
      frente.style.backgroundSize = "cover";
      frente.style.backgroundPosition = "center bottom";
      const f = document.createElement("div");
      f.className = "psx-franja";
      f.textContent = "STEAM";
      frente.appendChild(f);
    }
    const atras = cara(w, `rotateY(180deg) translateZ(${t / 2}px)`);
    atras.style.backgroundImage = portada;
    atras.style.filter = "brightness(0.45)";
    cara(t, `rotateY(-90deg) translateZ(${w / 2}px)`, "psx-lomo");
    cara(t, `rotateY(90deg) translateZ(${w / 2}px)`, "psx-lomo");
    v.appendChild(caja);
    document.body.appendChild(v);
    setTimeout(() => v.remove(), 800);
  };
  window.__psxBarajaA = (e) => {
    const d = e.detail;
    if (!grid || !d || d.__psx || d.button !== 1) return;
    const carta = [...grid.querySelectorAll(":scope > div > div > div")].find(c => c.querySelector(".gpfocus"));
    if (!carta || carta.hasAttribute("data-psx-elegida")) return;
    e.stopImmediatePropagation();
    e.preventDefault();
    const destino = e.target, fila = grid;
    vuelo(carta);
    // marcas como atributos data-*: React reescribe las clases de las tarjetas cada vez
    // que Steam las redibuja y una clase puesta a mano se borraria
    carta.dataset.psxElegida = "";
    fila.dataset.psxAbriendo = "";
    setTimeout(() => {
      const o = {detail: {...d, __psx: true}, bubbles: true, cancelable: true};
      destino.dispatchEvent(new CustomEvent("vgp_onbuttondown", o));
      setTimeout(() => destino.dispatchEvent(new CustomEvent("vgp_onbuttonup", o)), 50);
      setTimeout(() => { delete carta.dataset.psxElegida; delete fila.dataset.psxAbriendo; }, 600);
    }, 600);
  };
  window.addEventListener("vgp_onbuttondown", window.__psxBarajaA, true);
  window.__psxBarajaObs = new MutationObserver(pedir);
  window.__psxBarajaTimer = setInterval(buscar, 150);
  buscar();
  return "puesto";
})()
"""

QUITAR = """(() => { if (window.__psxBarajaTimer) clearInterval(window.__psxBarajaTimer);
  if (window.__psxBarajaObs) window.__psxBarajaObs.disconnect();
  if (window.__psxBarajaA) window.removeEventListener("vgp_onbuttondown", window.__psxBarajaA, true);
  window.__psxBaraja = 0; return "quitado"; })()"""


def poner(separacion=80):
    """separacion: distancia entre cajas en px (el control del plugin)"""
    paso = f'document.documentElement.style.setProperty("--psx-paso", "{int(separacion)}px");\n'
    r = evaluar_en_steam(paso + BARAJA, es_interfaz)
    return r.get("result", {}).get("result", {}).get("value")


def quitar():
    evaluar_en_steam(QUITAR, es_interfaz)


if __name__ == "__main__":
    print(quitar() if "--quitar" in sys.argv else poner())
