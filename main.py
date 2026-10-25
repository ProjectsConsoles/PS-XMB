"""Plugin de Decky para el tema PS XMB.

Hace en segundo plano lo que antes hacian tres servicios de systemd (y los apaga al
arrancar para que no se dupliquen):
- sonidos y musica de Audio Loader segun la consola, y color en automatico al
  cambiar de consola (sonidos/sonidos_por_modo.py);
- traductor de arriba/abajo para la columna de PS3 (controles/xmb_vertical.py);
- portadas de SteamGridDB para juegos nuevos (portadas/portadas_cuadradas.py).
Tambien trae el tema adentro (carpeta tema/) y lo instala o actualiza en la carpeta
de temas de CSS Loader al arrancar, sin tocar la configuracion del usuario.
Los scripts viven en la carpeta del tema y se usan tal cual.
"""
import asyncio
import json
import os
import shutil
import subprocess
import sys
import time

HOME = os.environ.get("DECKY_USER_HOME", "/home/deck")
# los scripts del tema usan ~ para sus archivos
os.environ["HOME"] = HOME
TEMA = os.path.join(HOME, "homebrew", "themes", "PS XMB")
for sub in ("sonidos", "controles", "portadas"):
    sys.path.insert(0, os.path.join(TEMA, sub))

import decky  # noqa: E402

AJUSTES = os.path.join(HOME, ".config", "psxmb_plugin.json")
DEFECTO = {"sonidos": True, "controles": True, "portadas": True}
SERVICIOS = ["psxmb-sonidos.path", "psxmb-sonidos.service", "psxmb-portadas.path",
             "psxmb-portadas.timer", "psxmb-portadas.service", "psxmb-controles.service"]

# el traductor que pone xmb_vertical.py se apaga quitando su escucha
QUITAR_CONTROLES = """(() => { if (window.__psxXmbEscucha) window.removeEventListener(
  "vgp_onbuttondown", window.__psxXmbEscucha, true); window.__psxXmb = 0; return "quitado"; })()"""


def leer_json(ruta, defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defecto


def modulos():
    """Se importan tarde: si el tema no esta instalado el plugin sigue cargando."""
    import portadas_cuadradas as portadas
    import sonidos_por_modo as sonidos
    import xmb_vertical as controles
    return portadas, sonidos, controles


# estado del plugin. Decky (formato clasico) llama los metodos de Plugin pasando la
# clase como self, asi que el trabajo va en funciones del modulo y no en metodos
ESTADO = {"ajustes": dict(DEFECTO), "ultimo": ""}


def aviso(texto):
    ESTADO["ultimo"] = time.strftime("%H:%M ") + texto
    decky.logger.info(texto)


def guardar():
    os.makedirs(os.path.dirname(AJUSTES), exist_ok=True)
    with open(AJUSTES, "w") as f:
        json.dump(ESTADO["ajustes"], f)


async def correr(funcion):
    return await asyncio.get_event_loop().run_in_executor(None, funcion)


def quitar_controles():
    _, sonidos, controles = modulos()
    sonidos.evaluar_en_steam(QUITAR_CONTROLES, controles.es_interfaz)


def portadas_ahora():
    portadas = modulos()[0]
    sys.argv = ["portadas"]
    try:
        portadas.main()
    except SystemExit:
        pass
    css = os.path.join(portadas.COMPANERO, "portadas.css")
    return open(css).read().count("content:") if os.path.exists(css) else 0


def sonidos_ahora():
    sonidos = modulos()[1]
    if ESTADO["ajustes"]["sonidos"]:
        try:
            sonidos.main()
        except SystemExit:
            pass
    else:
        # aunque los sonidos esten apagados, el color sigue la consola
        cfg = leer_json(sonidos.CONFIG_TEMA, {})
        estado = leer_json(sonidos.ESTADO, {})
        sonidos.color_por_consola(cfg, estado)
        with open(sonidos.ESTADO, "w") as f:
            json.dump(estado, f)


def firma_juegos():
    portadas = modulos()[0]
    return sum(os.path.getmtime(r) for r in portadas.bibliotecas() + portadas.archivos_accesos())


def apagar_servicios():
    entorno = dict(os.environ, XDG_RUNTIME_DIR=f"/run/user/{os.getuid()}")
    subprocess.run(["systemctl", "--user", "disable", "--now", *SERVICIOS],
                   env=entorno, capture_output=True)


def paquetes_de_sonido():
    """Lista de los paquetes que pide sonidos/sonidos.json: nombre, para que es
    (p. ej. "Sonidos PS2", "Musica PS3") y si esta instalado."""
    mapa = leer_json(os.path.join(TEMA, "sonidos", "sonidos.json"), {})
    lista = []
    for clave, nombre in mapa.items():
        if not nombre or nombre in ("Default", "None"):
            continue
        tipo, consola = clave.split("_", 1)
        uso = ("Musica " if tipo == "musica" else "Sonidos ") + consola.upper().replace("_", " ")
        lista.append({"nombre": nombre, "uso": uso,
                      "ok": os.path.isdir(os.path.join(HOME, "homebrew", "sounds", nombre))})
    # primero los sonidos y luego la musica, cada grupo por consola
    return sorted(lista, key=lambda p: (p["uso"].startswith("Musica"), p["uso"]))


# el tema viene en defaults/tema del repositorio; Decky lo copia junto a main.py
TEMA_INCLUIDO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tema", "PS XMB")


def version(ruta):
    """'v1.9' -> (1, 9) para comparar; sin tema -> (0,)"""
    v = leer_json(os.path.join(ruta, "theme.json"), {}).get("version", "v0")
    try:
        return tuple(int(x) for x in v.lstrip("v").split("."))
    except ValueError:
        return (0,)


def instalar_tema():
    """Copia el tema que trae el plugin si no esta o si el instalado es mas viejo.
    Se conservan los archivos del usuario: su configuracion y lo que no venga en el
    plugin."""
    if not os.path.isdir(TEMA_INCLUIDO) or version(TEMA) >= version(TEMA_INCLUIDO):
        return False
    shutil.copytree(TEMA_INCLUIDO, TEMA, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("config_USER.json", "__pycache__"))
    # la escritura de theme.json al final hace que CSS Loader recargue con todo listo
    os.utime(os.path.join(TEMA, "theme.json"))
    aviso(f"tema instalado/actualizado a v{'.'.join(map(str, version(TEMA)))}")
    return True


def hay_clave():
    return os.path.exists(os.path.join(HOME, ".config", "psxmb_sgdb_key"))


async def actualizar_portadas():
    aviso("bajando portadas...")
    n = await correr(portadas_ahora)
    aviso(f"portadas listas ({n})")
    return ESTADO["ultimo"]


class Plugin:
    # ---------- llamadas desde el panel ----------

    async def get_estado(self):
        tema = leer_json(os.path.join(TEMA, "theme.json"), {})
        cfg = leer_json(os.path.join(TEMA, "config_USER.json"), {})
        parches = tema.get("patches", {})
        return {
            "instalado": bool(tema),
            "consolas": list(parches.get("Consola", {}).get("values", {})),
            "colores": list(parches.get("Color de fondo", {}).get("values", {})),
            "consola": cfg.get("Consola", parches.get("Consola", {}).get("default", "")),
            "color": cfg.get("Color de fondo", parches.get("Color de fondo", {}).get("default", "")),
            "ajustes": ESTADO["ajustes"],
            "clave": hay_clave(),
            "ultimo": ESTADO["ultimo"],
            "paquetes": paquetes_de_sonido(),
            # todas las demas opciones del tema, para el apartado "Mas opciones"
            "opciones": [
                {"nombre": n, "tipo": d.get("type", "dropdown"), "valores": list(d.get("values", {})),
                 "valor": cfg.get(n, d.get("default", ""))}
                for n, d in parches.items() if n not in ("Consola", "Color de fondo")
            ],
        }

    async def set_ajuste(self, clave, valor):
        ESTADO["ajustes"][clave] = bool(valor)
        guardar()
        if clave == "controles" and not valor:
            await correr(quitar_controles)
        aviso(f"{clave}: {'si' if valor else 'no'}")
        return ESTADO["ajustes"]

    async def guardar_clave(self, clave):
        clave = (clave or "").strip()
        if len(clave) < 20:
            return "La clave parece incompleta"
        ruta = os.path.join(HOME, ".config", "psxmb_sgdb_key")
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w") as f:
            f.write(clave)
        os.chmod(ruta, 0o600)
        asyncio.get_event_loop().create_task(actualizar_portadas())
        return "Clave guardada; bajando portadas"

    async def actualizar_portadas(self):
        return await actualizar_portadas()

    # ---------- trabajo en segundo plano ----------

    async def _main(self):
        ESTADO["ajustes"] = {**DEFECTO, **leer_json(AJUSTES, {})}
        await correr(apagar_servicios)
        try:
            await correr(instalar_tema)
        except Exception as e:
            decky.logger.error(f"instalar tema: {e}")
        aviso("PS XMB listo")
        config = os.path.join(TEMA, "config_USER.json")
        ultima_cfg = ultima_juegos = None
        ultimo_reintento = time.time()
        while True:
            try:
                if os.path.isdir(TEMA):
                    if ESTADO["ajustes"]["controles"]:
                        await correr(lambda: modulos()[2].poner())
                    if os.path.getmtime(config) != ultima_cfg:
                        # CSS Loader guarda varias veces seguidas: se espera a que termine
                        await asyncio.sleep(1)
                        ultima_cfg = os.path.getmtime(config)
                        await correr(sonidos_ahora)
                    if ESTADO["ajustes"]["portadas"] and hay_clave():
                        firma = await correr(firma_juegos)
                        diario = time.time() - ultimo_reintento > 24 * 3600
                        if firma != ultima_juegos or diario:
                            if ultima_juegos is not None:
                                # espera a que Steam termine de escribir el juego nuevo
                                await asyncio.sleep(20)
                            ultima_juegos, ultimo_reintento = firma, time.time()
                            await correr(portadas_ahora)
            except Exception as e:
                decky.logger.error(f"ciclo: {e}")
            await asyncio.sleep(3)

    async def _unload(self):
        try:
            await correr(quitar_controles)
        except Exception:
            pass
