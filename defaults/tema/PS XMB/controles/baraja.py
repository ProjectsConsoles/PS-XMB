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
  const VERSION = 16;
  if (window.__psxBaraja === VERSION) return "ya estaba";
  if (window.__psxBarajaTimer) clearInterval(window.__psxBarajaTimer);
  if (window.__psxBarajaObs) window.__psxBarajaObs.disconnect();
  if (window.__psxBarajaA) window.removeEventListener("vgp_onbuttondown", window.__psxBarajaA, true);
  window.__psxBaraja = VERSION;
  let grid = null, pendiente = false;
  const LADO = 7;
  const logoSteam = 'url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%2024%2024%22%3E%3Ccircle%20cx%3D%2212%22%20cy%3D%2212%22%20r%3D%2211.5%22%20fill%3D%22%23fff%22/%3E%3Cpath%20d%3D%22M7.6%2015.6%2015.6%208.9%22%20stroke%3D%22%23171a21%22%20stroke-width%3D%222.6%22%20stroke-linecap%3D%22round%22/%3E%3Ccircle%20cx%3D%2215.6%22%20cy%3D%228.9%22%20r%3D%224.1%22%20fill%3D%22%23171a21%22/%3E%3Ccircle%20cx%3D%2215.6%22%20cy%3D%228.9%22%20r%3D%222.4%22%20fill%3D%22%23fff%22/%3E%3Ccircle%20cx%3D%227.6%22%20cy%3D%2215.6%22%20r%3D%222.9%22%20fill%3D%22%23171a21%22/%3E%3Ccircle%20cx%3D%227.6%22%20cy%3D%2215.6%22%20r%3D%221.5%22%20fill%3D%22%23fff%22/%3E%3C/svg%3E")';
  const acomodar = () => {
    pendiente = false;
    if (!grid || !grid.isConnected) return;
    const cartas = grid.querySelectorAll(":scope > div > div > div");
    let f = -1;
    cartas.forEach((c, i) => { if (f < 0 && c.querySelector(".gpfocus")) f = i; });
    const conFoco = f >= 0;
    // al volver a la Biblioteca la cuadricula es nueva y sin foco: se centra en el ultimo
    if (!conFoco) f = Math.min(window.__psxBarajaUltimo ?? Number(grid.dataset.psxFoco || 0), cartas.length - 1);
    else window.__psxBarajaUltimo = f;
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
      if (d === 0) c.dataset.psxSel = ""; else delete c.dataset.psxSel;
    });
    // entrada (la elegida llega girando desde la izquierda y las demas desde los lados) y
    // despues las animaciones, cuando Steam ya puso el foco
    if (conFoco && !("psxListo" in grid.dataset) && !grid.__psxEsperando) {
      grid.__psxEsperando = true;
      const esta = grid;
      setTimeout(() => requestAnimationFrame(() => {
        if (!esta.isConnected) return;
        esta.dataset.psxEntrando = "";
        setTimeout(() => { delete esta.dataset.psxEntrando; esta.dataset.psxListo = ""; }, 900);
      }), 150);
    }
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
      delete grid.dataset.psxListo;
      acomodar();
      // si el foco no llega (recien arrancado Steam, o se quedo en las pestanas) se pone en
      // el ultimo juego elegido y se muestra igual
      const esta = grid;
      setTimeout(() => {
        if (!esta.isConnected) return;
        const cartas = [...esta.querySelectorAll(":scope > div > div > div")];
        if (cartas.length && !cartas.some(c => c.querySelector(".gpfocus"))) {
          const i = Math.min(window.__psxBarajaUltimo ?? 0, cartas.length - 1);
          const caja = cartas[i].firstElementChild;
          if (caja && caja.focus) caja.focus();
        }
        if (!esta.__psxEsperando) { esta.__psxEsperando = true; esta.dataset.psxListo = ""; }
      }, 700);
    }
  };
  // A sobre una tarjeta: se arma una copia en 3D de la caja fuera de la Biblioteca (Steam
  // borra la Biblioteca al abrir el juego), que gira sin parar mientras se va del mismo
  // tamano hasta salir por la izquierda, girando cada vez mas rapido. El boton se le pasa
  // a Steam casi al final, para que la caja ya no este cuando aparezca el juego. Las demas
  // tarjetas se apartan. A medio vuelo se le pasa el mismo boton a Steam.
  // la copia usa las mismas variables --psx-caja-* que extras/caja-3d.css, asi sale con
  // la misma marca (Steam, PS2...). Se arma al tamano base de la tarjeta (134x201) y se
  // escala, para que las medidas en px de la franja y del lomo valgan igual.
  document.getElementById("psx-vuelo-css")?.remove();
  const css = document.createElement("style");
  css.id = "psx-vuelo-css";
  css.textContent = `
    .psx-vuelo { position: fixed; z-index: 99999; pointer-events: none; perspective: 1400px;
      animation: psx-vuelo-ir 0.75s cubic-bezier(.5, 0, .9, .6) forwards; }
    .psx-vuelo .psx-escala { position: absolute; left: 0; top: 0; width: 134px; height: 201px;
      transform-origin: 0 0; transform-style: preserve-3d; }
    .psx-vuelo .psx-caja { position: absolute; inset: 0; transform-style: preserve-3d;
      animation: psx-vuelo-girar 0.75s cubic-bezier(.55, 0, 1, .7) forwards; }
    .psx-vuelo .psx-cara { position: absolute; top: 0; height: 100%; backface-visibility: hidden;
      border-radius: 4px; overflow: hidden; background: var(--psx-caja-plastico, #0b0e13); }
    .psx-vuelo .psx-img { position: absolute; left: 0; right: 0; bottom: 0; top: var(--psx-caja-alto, 7%);
      background: center / cover no-repeat; }
    .psx-vuelo .psx-sin-caja .psx-img { top: 0; }
    .psx-vuelo .psx-franja { position: absolute; inset: 0;
      padding-left: var(--psx-caja-sangria, 13px);
      font: var(--psx-caja-fuente, 800 10px/14px "Motiva Sans", Arial, sans-serif);
      letter-spacing: var(--psx-caja-espacio, 2px); color: var(--psx-caja-color, #fff);
      text-align: var(--psx-caja-alinea, center); text-shadow: var(--psx-caja-sombra, 0 0 6px rgba(102, 192, 244, .8));
      background:
        var(--psx-caja-logo, ${logoSteam}) var(--psx-caja-logo-lugar, calc(50% - 29px) 2px / 10px 10px) no-repeat,
        var(--psx-caja-logo2, none) var(--psx-caja-logo2-lugar, right 4px top 2px / auto 10px) no-repeat,
        linear-gradient(115deg, rgba(255, 255, 255, .22) 0%, rgba(255, 255, 255, .04) 28%, transparent 45%),
        linear-gradient(180deg, var(--psx-caja-franja1, #2a475e) 0%, var(--psx-caja-franja2, #171a21) var(--psx-caja-alto, 7%),
          transparent var(--psx-caja-alto, 7%)); }
    .psx-vuelo .psx-franja::before { content: var(--psx-caja-texto, "STEAM"); }
    .psx-vuelo .psx-lomo { border-radius: 2px; color: var(--psx-caja-lomo-color, #c7d5e0);
      font: 800 11px/32px Arial, sans-serif; letter-spacing: 3px; writing-mode: vertical-rl; text-align: center;
      background: var(--psx-caja-lomo-fondo, linear-gradient(90deg, #0d1219, #3c4b5e 35%, #56677c 50%, #2a3646 70%, #0d1219)); }
    .psx-vuelo .psx-lomo::before { content: var(--psx-caja-lomo, "STEAM"); }
    .psx-vuelo .psx-canto { background: var(--psx-caja-canto, linear-gradient(90deg, #11161e, #3a4759 45%, #4d5d71 55%, #11161e)); }
    @keyframes psx-vuelo-girar { from { transform: rotateY(0deg); } to { transform: rotateY(-1260deg); } }
    @keyframes psx-vuelo-ir {
      from { transform: none; }
      to { transform: translateX(var(--psx-salida)); }
    }`;
  document.head.appendChild(css);
  const vuelo = (carta) => {
    const r = carta.getBoundingClientRect();
    const img = carta.querySelector("img");
    const conCaja = getComputedStyle(carta, "::after").content !== "none";
    const W = 134, H = 201, t = conCaja ? 32 : 6, k = r.width / W;
    const v = document.createElement("div");
    v.className = "psx-vuelo";
    Object.assign(v.style, {left: r.left + "px", top: r.top + "px", width: r.width + "px", height: r.height + "px"});
    // lo que le falta para salir completa por el borde izquierdo
    v.style.setProperty("--psx-salida", -(r.left + r.width + 80) + "px");
    const escala = document.createElement("div");
    escala.className = "psx-escala" + (conCaja ? "" : " psx-sin-caja");
    escala.style.transform = `scale(${k})`;
    const caja = document.createElement("div");
    caja.className = "psx-caja";
    const cara = (ancho, transform, clase) => {
      const c = document.createElement("div");
      c.className = "psx-cara " + (clase || "");
      Object.assign(c.style, {width: ancho + "px", left: (W - ancho) / 2 + "px", transform});
      caja.appendChild(c);
      return c;
    };
    const portada = (c, oscura) => {
      const i = document.createElement("div");
      i.className = "psx-img";
      if (img) i.style.backgroundImage = `url("${img.src}")`;
      if (oscura) i.style.filter = "brightness(0.45)";
      c.appendChild(i);
    };
    const frente = cara(W, `translateZ(${t / 2}px)`);
    portada(frente);
    if (conCaja) {
      const f = document.createElement("div");
      f.className = "psx-franja";
      frente.appendChild(f);
    }
    portada(cara(W, `rotateY(180deg) translateZ(${t / 2}px)`), true);
    cara(t, `rotateY(-90deg) translateZ(${W / 2}px)`, conCaja ? "psx-lomo" : "psx-canto");
    cara(t, `rotateY(90deg) translateZ(${W / 2}px)`, "psx-canto");
    escala.appendChild(caja);
    v.appendChild(escala);
    document.body.appendChild(v);
    setTimeout(() => v.remove(), 800);
  };
  window.__psxVuelo = vuelo;
  window.__psxBarajaA = (e) => {
    const d = e.detail;
    if (!grid || !d || d.__psx || d.button !== 1) return;
    // mientras la Biblioteca entra o se acomoda, A va directo a Steam (sin animacion)
    if (!("psxListo" in grid.dataset) || "psxEntrando" in grid.dataset) return;
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
      // si mientras tanto se salio de la Biblioteca no se abre nada
      if (destino.isConnected) {
        const o = {detail: {...d, __psx: true}, bubbles: true, cancelable: true};
        destino.dispatchEvent(new CustomEvent("vgp_onbuttondown", o));
        setTimeout(() => destino.dispatchEvent(new CustomEvent("vgp_onbuttonup", o)), 50);
      }
      setTimeout(() => { delete carta.dataset.psxElegida; delete fila.dataset.psxAbriendo; }, 600);
    }, 600);
  };
  // mientras la caja vuela, B y las flechas no hacen nada (un B de mas mandaba el foco a
  // las pestanas y la Biblioteca se quedaba sin juego seleccionado)
  if (window.__psxBarajaBloqueo) window.removeEventListener("vgp_onbuttondown", window.__psxBarajaBloqueo, true);
  window.__psxBarajaBloqueo = (e) => {
    const d = e.detail;
    if (!grid || !d || d.__psx || !("psxAbriendo" in grid.dataset)) return;
    if ([2, 9, 10, 11, 12].includes(d.button)) { e.stopImmediatePropagation(); e.preventDefault(); }
  };
  window.addEventListener("vgp_onbuttondown", window.__psxBarajaBloqueo, true);
  window.addEventListener("vgp_onbuttondown", window.__psxBarajaA, true);
  window.__psxBarajaObs = new MutationObserver(pedir);
  window.__psxBarajaTimer = setInterval(buscar, 150);
  buscar();
  return "puesto";
})()
"""

INICIO = r"""
(() => {
  const VERSION = 8;
  if (window.__psxInicio === VERSION) return "ya estaba";
  if (window.__psxInicioTimer) clearInterval(window.__psxInicioTimer);
  if (window.__psxInicioObs) window.__psxInicioObs.disconnect();
  if (window.__psxInicioA) window.removeEventListener("vgp_onbuttondown", window.__psxInicioA, true);
  window.__psxInicio = VERSION;
  // marca de que el script corre: el CSS solo esconde la fila sin acomodar si esta presente
  document.documentElement.dataset.psxJs = "";
  let fila = null, pendiente = false;
  const paso = () => parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--psx-paso")) || 80;
  const tarjetas = () => [...fila.children];
  const acomodar = () => {
    pendiente = false;
    if (!fila || !fila.isConnected) return;
    const items = tarjetas();
    let f = items.findIndex(x => x.querySelector(".gpfocus"));
    const conFoco = f >= 0;
    // al regresar de un juego la fila es nueva y todavia sin foco: se centra en el ultimo
    // juego elegido (si no, aparece en otro lado y luego se desliza hasta el)
    if (!conFoco) f = Math.min(window.__psxInicioUltimo ?? Number(fila.dataset.psxFoco || 0), items.length - 1);
    else window.__psxInicioUltimo = f;
    fila.dataset.psxFoco = f;
    portadas();
    const centro = fila.parentElement.clientWidth / 2, p = paso();
    items.forEach((x, i) => {
      const d = i - f, ad = Math.abs(d), s = Math.sign(d);
      // destino de su centro en la baraja menos donde la pone Steam (left)
      const destino = centro - x.offsetWidth / 2 + s * (70 + Math.min(ad, 7) * p);
      x.style.setProperty("--tx", (destino - x.offsetLeft) + "px");
      x.style.setProperty("--s", s);
      x.style.setProperty("--ad", ad);
      x.style.setProperty("--c", d === 0 ? 1 : 0);
      if (d === 0) x.dataset.psxSel = ""; else delete x.dataset.psxSel;
    });
    // las animaciones se encienden cuando Steam ya puso el foco y la fila quedo en su lugar
    if (conFoco && !("psxListo" in fila.dataset) && !fila.__psxEsperando) {
      fila.__psxEsperando = true;
      const esta = fila;
      setTimeout(() => requestAnimationFrame(() => {
        if (!esta.isConnected) return;
        // entrada: la caja elegida llega girando desde la izquierda y las demas desde los lados
        esta.dataset.psxEntrando = "";
        esta.dataset.psxListo = "";
        setTimeout(() => delete esta.dataset.psxEntrando, 850);
      }), 250);
    }
  };
  // La primera tarjeta (ultimo jugado) trae la imagen horizontal del juego; en la baraja va
  // vertical como las demas, asi que se le pone la portada vertical (si no, se recorta)
  const vertical = (src) => {
    let m = src.match(/^(.*\/customimages\/\d+)\.(png|jpe?g|webp)(\?.*)?$/);
    if (m) return m[1] + "p." + m[2] + (m[3] || "");
    m = src.match(/^(.*\/assets\/\d+\/)(header|capsule_[^/.]+|library_hero[^/.]*)\.jpg(\?.*)?$/);
    if (m) return m[1] + "library_600x900.jpg" + (m[3] || "");
    return null;
  };
  const portadas = () => {
    fila.querySelectorAll("img").forEach(img => {
      const v = vertical(img.getAttribute("src") || "");
      if (v) img.setAttribute("src", v);
    });
  };
  const pedir = () => { if (!pendiente) { pendiente = true; requestAnimationFrame(acomodar); } };
  const buscar = () => {
    const activa = getComputedStyle(document.documentElement).getPropertyValue("--psx-inicio-baraja").trim() === "si";
    const g = activa ? document.querySelector(".ReactVirtualized__Grid__innerScrollContainer") : null;
    if (g === fila) return;
    if (fila) { delete fila.dataset.psxInicio; delete fila.dataset.psxListo; }
    window.__psxInicioObs.disconnect();
    fila = g;
    if (!fila) return;
    fila.dataset.psxInicio = "";
    window.__psxInicioObs.observe(fila, {subtree: true, childList: true, attributes: true, attributeFilter: ["class", "src"]});
    acomodar();
    // si el foco no llega (por ejemplo recien arrancado Steam) se muestra igual, sin entrada
    const esta = fila;
    setTimeout(() => { if (esta.isConnected && !esta.__psxEsperando) { esta.__psxEsperando = true; esta.dataset.psxListo = ""; } }, 700);
  };
  // A sobre una tarjeta del Inicio: la misma caja que vuela de la Biblioteca
  window.__psxInicioA = (e) => {
    const d = e.detail;
    if (!fila || !d || d.__psx || d.button !== 1 || !window.__psxVuelo) return;
    const item = tarjetas().find(x => x.querySelector(".gpfocus"));
    const carta = item && item.querySelector(":scope > div > div > div:first-child > div:first-child");
    if (!carta || item.hasAttribute("data-psx-elegida")) return;
    e.stopImmediatePropagation();
    e.preventDefault();
    const destino = e.target, f = fila;
    window.__psxVuelo(carta);
    item.dataset.psxElegida = "";
    f.dataset.psxAbriendo = "";
    setTimeout(() => {
      const o = {detail: {...d, __psx: true}, bubbles: true, cancelable: true};
      destino.dispatchEvent(new CustomEvent("vgp_onbuttondown", o));
      setTimeout(() => destino.dispatchEvent(new CustomEvent("vgp_onbuttonup", o)), 50);
      setTimeout(() => { delete item.dataset.psxElegida; delete f.dataset.psxAbriendo; }, 600);
    }, 600);
  };
  if (window.__psxInicioBloqueo) window.removeEventListener("vgp_onbuttondown", window.__psxInicioBloqueo, true);
  window.__psxInicioBloqueo = (e) => {
    const d = e.detail;
    if (!fila || !d || d.__psx || !("psxAbriendo" in fila.dataset)) return;
    if ([2, 9, 10, 11, 12].includes(d.button)) { e.stopImmediatePropagation(); e.preventDefault(); }
  };
  window.addEventListener("vgp_onbuttondown", window.__psxInicioBloqueo, true);
  window.addEventListener("vgp_onbuttondown", window.__psxInicioA, true);
  window.__psxInicioObs = new MutationObserver(pedir);
  window.__psxInicioTimer = setInterval(buscar, 150);
  buscar();
  return "puesto";
})()
"""

QUITAR = """(() => { if (window.__psxBarajaTimer) clearInterval(window.__psxBarajaTimer);
  if (window.__psxBarajaObs) window.__psxBarajaObs.disconnect();
  if (window.__psxBarajaA) window.removeEventListener("vgp_onbuttondown", window.__psxBarajaA, true);
  window.__psxBaraja = 0;
  if (window.__psxInicioTimer) clearInterval(window.__psxInicioTimer);
  if (window.__psxInicioObs) window.__psxInicioObs.disconnect();
  if (window.__psxInicioA) window.removeEventListener("vgp_onbuttondown", window.__psxInicioA, true);
  if (window.__psxInicioBloqueo) window.removeEventListener("vgp_onbuttondown", window.__psxInicioBloqueo, true);
  if (window.__psxBarajaBloqueo) window.removeEventListener("vgp_onbuttondown", window.__psxBarajaBloqueo, true);
  window.__psxInicio = 0; delete document.documentElement.dataset.psxJs; return "quitado"; })()"""


def poner(separacion=80):
    """separacion: distancia entre cajas en px (el control del plugin)"""
    paso = f'document.documentElement.style.setProperty("--psx-paso", "{int(separacion)}px");\n'
    r = evaluar_en_steam(paso + BARAJA + ";\n" + INICIO, es_interfaz)
    return r.get("result", {}).get("result", {}).get("value")


def quitar():
    evaluar_en_steam(QUITAR, es_interfaz)


if __name__ == "__main__":
    print(quitar() if "--quitar" in sys.argv else poner())
