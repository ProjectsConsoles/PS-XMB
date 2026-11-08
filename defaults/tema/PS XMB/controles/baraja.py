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
  const VERSION = 18;
  if (window.__psxBaraja === VERSION) return "ya estaba";
  if (window.__psxBarajaTimer) clearInterval(window.__psxBarajaTimer);
  if (window.__psxBarajaObs) window.__psxBarajaObs.disconnect();
  if (window.__psxBarajaA) window.removeEventListener("vgp_onbuttondown", window.__psxBarajaA, true);
  window.__psxBaraja = VERSION;
  let grid = null, pendiente = false;
  const LADO = 7;
  const logoSteam = 'url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%22-.5%20-.5%2066%2066%22%3E%3Cpath%20d%3D%22M31.96%200a32%2032%200%201%200%20.001%200z%22%20fill%3D%22%23fff%22/%3E%3Cpath%20d%3D%22M30.31%2023.985l.003.158-7.83%2011.375c-1.268-.058-2.54.165-3.748.662a8.14%208.14%200%200%200-1.498.8L.042%2029.893s-.398%206.546%201.26%2011.424l12.156%205.016c.6%202.728%202.48%205.12%205.242%206.27a8.88%208.88%200%200%200%2011.603-4.782%208.89%208.89%200%200%200%20.684-3.656L42.18%2036.16l.275.005c6.705%200%2012.155-5.466%2012.155-12.18s-5.44-12.16-12.155-12.174c-6.702%200-12.155%205.46-12.155%2012.174zm-1.88%2023.05c-1.454%203.5-5.466%205.147-8.953%203.694a6.84%206.84%200%200%201-3.524-3.362l3.957%201.64a5.04%205.04%200%200%200%206.591-2.719%205.05%205.05%200%200%200-2.715-6.601l-4.1-1.695c1.578-.6%203.372-.62%205.05.077%201.7.703%203%202.027%203.696%203.72s.692%203.56-.01%205.246M42.466%2032.1a8.12%208.12%200%200%201-8.098-8.113%208.12%208.12%200%200%201%208.098-8.111%208.12%208.12%200%200%201%208.1%208.111%208.12%208.12%200%200%201-8.1%208.113m-6.068-8.126a6.09%206.09%200%200%201%206.08-6.095c3.355%200%206.084%202.73%206.084%206.095a6.09%206.09%200%200%201-6.084%206.093%206.09%206.09%200%200%201-6.081-6.093z%22%20fill%3D%22%23171a21%22/%3E%3C/svg%3E")';
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
    // solo se escribe lo que cambio (cada escritura hace que Steam recalcule esa tarjeta)
    const poner = (x, n, v) => { v = String(v); if (x.style.getPropertyValue(n) !== v) x.style.setProperty(n, v); };
    poner(grid, "--centro", Math.round(grid.clientWidth / 2) + "px");
    cartas.forEach((c, i) => {
      const d = i - f, ad = Math.abs(d);
      poner(c, "--i", i);
      poner(c, "--d", Math.max(-LADO, Math.min(LADO, d)));
      poner(c, "--s", Math.sign(d));
      poner(c, "--ad", ad);
      poner(c, "--c", d === 0 ? 1 : 0);
      if (!("psxPuesto" in c.dataset)) c.dataset.psxPuesto = "";
      if (d === 0) { if (!("psxSel" in c.dataset)) c.dataset.psxSel = ""; }
      else if ("psxSel" in c.dataset) delete c.dataset.psxSel;
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
  // la marca data-psx-cuadricula la usan extras/caja-3d.css y extras/biblioteca-baraja.css
  // (va aunque la baraja este apagada). La opcion se revisa cada 2 s o cuando aparece otra
  // cuadricula: leer el estilo calculado obliga a Steam a recalcular estilos
  let revisado = 0, activaUlt = false;
  const buscar = () => {
    const g = document.querySelector('div[style*="grid-auto-rows"]');
    if (g && !("psxCuadricula" in g.dataset)) g.dataset.psxCuadricula = "";
    const ahora = Date.now();
    if (g && (g !== grid || ahora - revisado >= 2000)) {
      revisado = ahora;
      activaUlt = getComputedStyle(g).getPropertyValue("--psx-baraja").trim() === "si";
    }
    const activa = g && activaUlt;
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
  const VERSION = 15;
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
  // que juego es cada tarjeta (el numero de app viene en la imagen de la portada): al
  // regresar de un juego la fila se reordena (el que jugaste pasa al principio), asi que
  // se recuerda el juego y no su posicion
  const juego = (x) => {
    const img = x.querySelector("img");
    const m = img && (img.getAttribute("src") || "").match(/(?:customimages|assets)\/(\d+)/);
    return m ? m[1] : null;
  };
  const acomodar = () => {
    pendiente = false;
    if (!fila || !fila.isConnected) return;
    const items = tarjetas();
    let f = items.findIndex(x => x.querySelector(".gpfocus"));
    // al regresar de un juego Steam pone el foco primero en la tarjeta destacada y luego en
    // la del juego: mientras se asienta se ignora y se queda en el ultimo juego elegido
    if (fila.__psxAsentando && window.__psxInicioUltimo != null) f = -1;
    const conFoco = f >= 0;
    // al regresar de un juego la fila es nueva y todavia sin foco: se centra en el ultimo
    // juego elegido, buscandolo por su numero de app (si no, aparece otro y luego se desliza)
    if (!conFoco) {
      const porJuego = window.__psxInicioJuego ? items.findIndex(x => juego(x) === window.__psxInicioJuego) : -1;
      f = porJuego >= 0 ? porJuego : Math.min(window.__psxInicioUltimo ?? Number(fila.dataset.psxFoco || 0), items.length - 1);
    } else {
      window.__psxInicioUltimo = f;
      window.__psxInicioJuego = juego(items[f]);
    }
    fila.dataset.psxFoco = f;
    portadas();
    // primero se leen todas las medidas y despues se escribe: leer el tamano de una tarjeta
    // despues de moverle otra obliga a Steam a recalcular la pagina, una vez por tarjeta
    const centro = fila.parentElement.clientWidth / 2, p = paso();
    const medidas = items.map(x => [x.offsetWidth, x.offsetLeft]);
    const cd = claseDestacada();
    const poner = (x, n, v) => { v = String(v); if (x.style.getPropertyValue(n) !== v) x.style.setProperty(n, v); };
    items.forEach((x, i) => {
      const d = i - f, ad = Math.abs(d), s = Math.sign(d);
      // destino de su centro en la baraja menos donde la pone Steam (left)
      const destino = centro - medidas[i][0] / 2 + s * (70 + Math.min(ad, 7) * p);
      poner(x, "--tx", (destino - medidas[i][1]) + "px");
      if (!("psxPuesto" in x.dataset)) x.dataset.psxPuesto = "";
      const destacada = !!cd && !!x.querySelector(cd);
      if (destacada !== ("psxDestacada" in x.dataset)) {
        if (destacada) x.dataset.psxDestacada = ""; else delete x.dataset.psxDestacada;
      }
      poner(x, "--s", s);
      poner(x, "--ad", ad);
      poner(x, "--c", d === 0 ? 1 : 0);
      if (d === 0) { if (!("psxSel" in x.dataset)) x.dataset.psxSel = ""; }
      else if ("psxSel" in x.dataset) delete x.dataset.psxSel;
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
  // la clase real de la tarjeta destacada (Steam usa nombres con hash; CSS Loader pone en
  // extras/inicio-baraja.css la regla ".psx-marca-destacada, <clase>")
  let destacadaCache = null;
  const claseDestacada = () => {
    if (destacadaCache) return destacadaCache;
    for (const hoja of document.styleSheets) {
      let reglas;
      try { reglas = hoja.cssRules; } catch (e) { continue; }
      for (const r of reglas) {
        const m = r.selectorText && r.selectorText.match(/\.psx-marca-destacada, \.([\w-]+)/);
        if (m) return (destacadaCache = "." + m[1]);
      }
    }
    return null;
  };
  const pedir = () => { if (!pendiente) { pendiente = true; requestAnimationFrame(acomodar); } };
  // leer el estilo calculado obliga a Steam a recalcular estilos (con el fondo animado, casi
  // siempre): la opcion se revisa cada 2 s o cuando aparece otra fila, no cada 150 ms
  let revisado = 0, activa = false;
  const buscar = () => {
    const candidata = document.querySelector(".ReactVirtualized__Grid__innerScrollContainer");
    const ahora = Date.now();
    if (candidata === fila && ahora - revisado < 2000) return;
    if (candidata !== fila || ahora - revisado >= 2000) {
      revisado = ahora;
      activa = getComputedStyle(document.documentElement).getPropertyValue("--psx-inicio-baraja").trim() === "si";
    }
    const g = activa ? candidata : null;
    if (g === fila) return;
    if (fila) {
      delete fila.dataset.psxInicio; delete fila.dataset.psxListo;
      if (fila.parentElement) delete fila.parentElement.dataset.psxInicioPadre;
    }
    window.__psxInicioObs.disconnect();
    fila = g;
    if (!fila) return;
    fila.dataset.psxInicio = "";
    if (fila.parentElement) fila.parentElement.dataset.psxInicioPadre = "";
    // los primeros 0.7 s: el foco salta y el fondo de Steam muestra el arte del primer juego
    const nueva = fila;
    nueva.__psxAsentando = true;
    document.documentElement.dataset.psxAsentando = "";
    setTimeout(() => {
      nueva.__psxAsentando = false;
      delete document.documentElement.dataset.psxAsentando;
      if (nueva.isConnected) pedir();
    }, 700);
    window.__psxInicioObs.observe(fila, {subtree: true, childList: true, attributes: true, attributeFilter: ["class", "src"]});
    acomodar();
    // si el foco no llega (por ejemplo recien arrancado Steam) se muestra igual, sin entrada
    // (despues de que se asienta el foco, para no quitarle la entrada al regresar)
    const esta = fila;
    setTimeout(() => { if (esta.isConnected && !esta.__psxEsperando) { esta.__psxEsperando = true; esta.dataset.psxListo = ""; } }, 1000);
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

PROTECTOR = r"""
(() => {
  const VERSION = 1;
  if (window.__psxProt === VERSION) return "ya estaba";
  if (window.__psxProtTimer) clearInterval(window.__psxProtTimer);
  (window.__psxProtEscuchas || []).forEach(([t, f]) => window.removeEventListener(t, f, true));
  window.__psxProt = VERSION;
  const html = document.documentElement;
  window.__psxProtUlt = Date.now();
  // cualquier boton, tecla o toque: si el protector estaba puesto solo lo quita (ese primer
  // boton no hace nada mas); si no, reinicia la cuenta
  const despertar = (e) => {
    window.__psxProtUlt = Date.now();
    if ("psxProtector" in html.dataset) {
      delete html.dataset.psxProtector;
      if (e.type === "vgp_onbuttondown") { e.stopImmediatePropagation(); e.preventDefault(); }
    }
  };
  window.__psxProtEscuchas = ["vgp_onbuttondown", "keydown", "pointerdown", "touchstart", "wheel"].map(t => [t, despertar]);
  window.__psxProtEscuchas.forEach(([t, f]) => window.addEventListener(t, f, true));
  window.__psxProtTimer = setInterval(() => {
    // solo cuenta con la pantalla principal al frente y en el Inicio (con el menu de los
    // 3 puntos abierto o un juego, las teclas van a otra ventana)
    const enInicio = document.hasFocus() && document.visibilityState === "visible"
      && !!document.querySelector(".ReactVirtualized__Grid__innerScrollContainer");
    if (!window.__psxProtOn || !enInicio) {
      window.__psxProtUlt = Date.now();
      if ("psxProtector" in html.dataset && !window.__psxProtOn) delete html.dataset.psxProtector;
      return;
    }
    if (Date.now() - window.__psxProtUlt > 60000) html.dataset.psxProtector = "";
  }, 1000);
  return "puesto";
})()
"""

LOGO = r"""
(() => {
  const VERSION = 4;
  if (window.__psxLogo === VERSION) return "ya estaba";
  if (window.__psxLogoTimer) clearInterval(window.__psxLogoTimer);
  window.__psxLogo = VERSION;
  const SVG = "<svg xmlns=\"http://www.w3.org/2000/svg\" id=\"psx-steam-logo-svg\" viewBox=\"-.5 -.5 66 66\"><style>#psx-steam-logo-svg .psxl-t{fill:none;stroke:#fff;stroke-opacity:.2;stroke-width:.6;stroke-linecap:butt;stroke-linejoin:round;stroke-dasharray:103 103;stroke-dashoffset:103}#psx-steam-logo-svg .psxl-relleno{fill:#fff;fill-opacity:0;animation:psxl-relleno 12s ease infinite}#psx-steam-logo-svg .psxl-trazos{animation:psxl-trazos 12s ease infinite}#psx-steam-logo-svg .psxl-c{animation:psxl-c 12s linear infinite}#psx-steam-logo-svg .psxl-p{animation:psxl-p 12s linear infinite}#psx-steam-logo-svg .psxl-lleno{opacity:0;animation:psxl-lleno 12s ease infinite}#psx-steam-logo-svg .psxl-todo{animation:psxl-todo 12s ease infinite}@keyframes psxl-c{0%{stroke-dashoffset:103}18%,100%{stroke-dashoffset:0}}@keyframes psxl-p{0%,16%{stroke-dashoffset:103}38%,100%{stroke-dashoffset:0}}@keyframes psxl-relleno{0%,28%{fill-opacity:0}44%,100%{fill-opacity:.14}}@keyframes psxl-lleno{0%,46%{opacity:0}54%,100%{opacity:1}}@keyframes psxl-trazos{0%,46%{opacity:1}51%,100%{opacity:0}}@keyframes psxl-todo{0%{opacity:0}2%,84%{opacity:1}96%,100%{opacity:0}}</style><g class=\"psxl-todo\"><g class=\"psxl-lleno\"><path d=\"M31.96 0a32 32 0 1 0 .001 0z\" fill=\"#fff\" fill-opacity=\".06\"/><path d=\"M30.31 23.985l.003.158-7.83 11.375c-1.268-.058-2.54.165-3.748.662a8.14 8.14 0 0 0-1.498.8L.042 29.893s-.398 6.546 1.26 11.424l12.156 5.016c.6 2.728 2.48 5.12 5.242 6.27a8.88 8.88 0 0 0 11.603-4.782 8.89 8.89 0 0 0 .684-3.656L42.18 36.16l.275.005c6.705 0 12.155-5.466 12.155-12.18s-5.44-12.16-12.155-12.174c-6.702 0-12.155 5.46-12.155 12.174zm-1.88 23.05c-1.454 3.5-5.466 5.147-8.953 3.694a6.84 6.84 0 0 1-3.524-3.362l3.957 1.64a5.04 5.04 0 0 0 6.591-2.719 5.05 5.05 0 0 0-2.715-6.601l-4.1-1.695c1.578-.6 3.372-.62 5.05.077 1.7.703 3 2.027 3.696 3.72s.692 3.56-.01 5.246M42.466 32.1a8.12 8.12 0 0 1-8.098-8.113 8.12 8.12 0 0 1 8.098-8.111 8.12 8.12 0 0 1 8.1 8.111 8.12 8.12 0 0 1-8.1 8.113m-6.068-8.126a6.09 6.09 0 0 1 6.08-6.095c3.355 0 6.084 2.73 6.084 6.095a6.09 6.09 0 0 1-6.084 6.093 6.09 6.09 0 0 1-6.081-6.093z\" fill=\"#000\" fill-opacity=\".24\"/></g><defs><mask id=\"sinpiston\"><rect x=\"-1\" y=\"-1\" width=\"67\" height=\"67\" fill=\"#fff\"/><path d=\"M30.31 23.985l.003.158-7.83 11.375c-1.268-.058-2.54.165-3.748.662a8.14 8.14 0 0 0-1.498.8L.042 29.893s-.398 6.546 1.26 11.424l12.156 5.016c.6 2.728 2.48 5.12 5.242 6.27a8.88 8.88 0 0 0 11.603-4.782 8.89 8.89 0 0 0 .684-3.656L42.18 36.16l.275.005c6.705 0 12.155-5.466 12.155-12.18s-5.44-12.16-12.155-12.174c-6.702 0-12.155 5.46-12.155 12.174zm-1.88 23.05c-1.454 3.5-5.466 5.147-8.953 3.694a6.84 6.84 0 0 1-3.524-3.362l3.957 1.64a5.04 5.04 0 0 0 6.591-2.719 5.05 5.05 0 0 0-2.715-6.601l-4.1-1.695c1.578-.6 3.372-.62 5.05.077 1.7.703 3 2.027 3.696 3.72s.692 3.56-.01 5.246M42.466 32.1a8.12 8.12 0 0 1-8.098-8.113 8.12 8.12 0 0 1 8.098-8.111 8.12 8.12 0 0 1 8.1 8.111 8.12 8.12 0 0 1-8.1 8.113m-6.068-8.126a6.09 6.09 0 0 1 6.08-6.095c3.355 0 6.084 2.73 6.084 6.095a6.09 6.09 0 0 1-6.084 6.093 6.09 6.09 0 0 1-6.081-6.093z\" fill=\"#000\"/></mask></defs><g class=\"psxl-trazos\"><path class=\"psxl-t psxl-c\" mask=\"url(#sinpiston)\" d=\"M31.96 0a32 32 0 1 0 .001 0z\" pathLength=\"100\"/><path class=\"psxl-relleno\" d=\"M30.31 23.985l.003.158-7.83 11.375c-1.268-.058-2.54.165-3.748.662a8.14 8.14 0 0 0-1.498.8L.042 29.893s-.398 6.546 1.26 11.424l12.156 5.016c.6 2.728 2.48 5.12 5.242 6.27a8.88 8.88 0 0 0 11.603-4.782 8.89 8.89 0 0 0 .684-3.656L42.18 36.16l.275.005c6.705 0 12.155-5.466 12.155-12.18s-5.44-12.16-12.155-12.174c-6.702 0-12.155 5.46-12.155 12.174zm-1.88 23.05c-1.454 3.5-5.466 5.147-8.953 3.694a6.84 6.84 0 0 1-3.524-3.362l3.957 1.64a5.04 5.04 0 0 0 6.591-2.719 5.05 5.05 0 0 0-2.715-6.601l-4.1-1.695c1.578-.6 3.372-.62 5.05.077 1.7.703 3 2.027 3.696 3.72s.692 3.56-.01 5.246M42.466 32.1a8.12 8.12 0 0 1-8.098-8.113 8.12 8.12 0 0 1 8.098-8.111 8.12 8.12 0 0 1 8.1 8.111 8.12 8.12 0 0 1-8.1 8.113m-6.068-8.126a6.09 6.09 0 0 1 6.08-6.095c3.355 0 6.084 2.73 6.084 6.095a6.09 6.09 0 0 1-6.084 6.093 6.09 6.09 0 0 1-6.081-6.093z\"/><path class=\"psxl-t psxl-p\" d=\"M30.31 23.985l.003.158-7.83 11.375c-1.268-.058-2.54.165-3.748.662a8.14 8.14 0 0 0-1.498.8L.042 29.893s-.398 6.546 1.26 11.424l12.156 5.016c.6 2.728 2.48 5.12 5.242 6.27a8.88 8.88 0 0 0 11.603-4.782 8.89 8.89 0 0 0 .684-3.656L42.18 36.16l.275.005c6.705 0 12.155-5.466 12.155-12.18s-5.44-12.16-12.155-12.174c-6.702 0-12.155 5.46-12.155 12.174zm-1.88 23.05c-1.454 3.5-5.466 5.147-8.953 3.694a6.84 6.84 0 0 1-3.524-3.362l3.957 1.64a5.04 5.04 0 0 0 6.591-2.719 5.05 5.05 0 0 0-2.715-6.601l-4.1-1.695c1.578-.6 3.372-.62 5.05.077 1.7.703 3 2.027 3.696 3.72s.692 3.56-.01 5.246M42.466 32.1a8.12 8.12 0 0 1-8.098-8.113 8.12 8.12 0 0 1 8.098-8.111 8.12 8.12 0 0 1 8.1 8.111 8.12 8.12 0 0 1-8.1 8.113m-6.068-8.126a6.09 6.09 0 0 1 6.08-6.095c3.355 0 6.084 2.73 6.084 6.095a6.09 6.09 0 0 1-6.084 6.093 6.09 6.09 0 0 1-6.081-6.093z\" pathLength=\"100\"/></g></g></svg>";
  // el logo de Steam animado del fondo (fondos/steam.css pone --psx-steam-logo): como
  // elemento de la pagina para poder pausarlo mientras Steam redibuja el Inicio
  window.__psxLogoTimer = setInterval(() => {
    const activo = getComputedStyle(document.documentElement).getPropertyValue("--psx-steam-logo").trim() === "si";
    let el = document.getElementById("psx-steam-logo");
    if (el && el.dataset.v !== String(VERSION)) { el.remove(); el = null; }
    if (activo && !el) {
      el = document.createElement("div");
      el.id = "psx-steam-logo";
      el.dataset.v = String(VERSION);
      el.innerHTML = SVG;
      document.body.appendChild(el);
    } else if (!activo && el) {
      el.remove();
    }
  }, 1000);
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
  window.__psxInicio = 0; delete document.documentElement.dataset.psxJs;
  if (window.__psxProtTimer) clearInterval(window.__psxProtTimer);
  (window.__psxProtEscuchas || []).forEach(([t, f]) => window.removeEventListener(t, f, true));
  window.__psxProt = 0; delete document.documentElement.dataset.psxProtector;
  if (window.__psxLogoTimer) clearInterval(window.__psxLogoTimer);
  window.__psxLogo = 0; document.getElementById("psx-steam-logo")?.remove(); return "quitado"; })()"""


def poner(separacion=80, protector=True):
    """separacion: distancia entre cajas en px (el control del plugin); protector: si se
    pone el protector de pantalla del Inicio despues de 1 minuto"""
    paso = (f'document.documentElement.style.setProperty("--psx-paso", "{int(separacion)}px");\n'
            f'window.__psxProtOn = {"true" if protector else "false"};\n')
    r = evaluar_en_steam(paso + BARAJA + ";\n" + PROTECTOR + ";\n" + LOGO + ";\n" + INICIO, es_interfaz)
    return r.get("result", {}).get("result", {}).get("value")


def quitar():
    evaluar_en_steam(QUITAR, es_interfaz)


if __name__ == "__main__":
    print(quitar() if "--quitar" in sys.argv else poner())
