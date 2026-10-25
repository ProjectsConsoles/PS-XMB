#!/usr/bin/env python3
"""PS XMB en Windows (ROG Ally, PC): hace lo que en la Deck hacen Decky y los servicios.

Un solo proceso que arranca al iniciar sesion y se queda en segundo plano:
- Controles: pone el traductor de arriba/abajo de la columna de PS3 en el Big Picture.
- Sonidos: en Windows no hay Audio Loader, asi que copia los sonidos del paquete de
  cada consola sobre los de Steam (steamui/sounds) y guarda los originales para
  regresarlos con "Steam Deck". Si una actualizacion de Steam los pisa, los repone.
  Los paquetes se bajan solos de la tienda de DeckThemes la primera vez.
- Color: al cambiar de consola regresa el color de fondo a "Automatico".
- Portadas: si hay clave de SteamGridDB guardada, baja las de los juegos nuevos.

Se instala una vez (crea el arranque automatico y lo prende):

    <python> "%USERPROFILE%\\homebrew\\themes\\PS XMB\\windows\\psxmb_windows.py" --instalar

Con una clave de SteamGridDB al final tambien la guarda y baja las portadas:

    ... psxmb_windows.py --instalar TU_CLAVE
"""
import io
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile

TEMA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# el Python portatil no agrega solo las carpetas del script a la ruta de modulos
for sub in ("sonidos", "controles", "portadas"):
    sys.path.insert(0, os.path.join(TEMA, sub))

import portadas_cuadradas as portadas  # noqa: E402
import sonidos_por_modo as sonidos  # noqa: E402
import xmb_vertical as controles  # noqa: E402

PAQUETES = os.path.join(os.path.expanduser("~"), "homebrew", "sounds")
ORIGINALES = os.path.join(PAQUETES, "_steam_original")
SONIDOS_STEAM = os.path.join(portadas.STEAM, "steamui", "sounds")
ESTADO = os.path.join(os.path.expanduser("~"), ".config", "psxmb_windows.json")
REGISTRO = os.path.join(os.path.expanduser("~"), ".config", "psxmb_windows.log")


def log(*partes):
    linea = time.strftime("%Y-%m-%d %H:%M:%S ") + " ".join(str(p) for p in partes)
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def leer_json(ruta, defecto):
    try:
        return json.load(open(ruta, encoding="utf-8"))
    except (OSError, ValueError):
        return defecto


# ---------- sonidos ----------

def bajar_paquete(nombre):
    """Baja un paquete de sonidos de la tienda de DeckThemes por su nombre."""
    q = urllib.parse.quote(nombre)
    datos = json.load(urllib.request.urlopen(
        f"https://api.deckthemes.com/themes?filters=Audio&search={q}&perPage=20", timeout=20))
    tema = next((t for t in datos.get("items", []) if t["name"] == nombre), None)
    if not tema:
        log("paquete no encontrado en la tienda:", nombre)
        return False
    blob = urllib.request.urlopen(
        f"https://api.deckthemes.com/blobs/{tema['download']['id']}", timeout=60).read()
    destino = os.path.join(PAQUETES, nombre)
    os.makedirs(destino, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            # los zips traen una carpeta con el nombre del paquete; se aplana
            archivo = os.path.basename(info.filename)
            if archivo and archivo != "desktop.ini":
                with open(os.path.join(destino, archivo), "wb") as f:
                    f.write(z.read(info))
    log("paquete bajado:", nombre)
    return True


def respaldar_originales():
    """Guarda una vez los sonidos originales de Steam para poder regresarlos."""
    if os.path.isdir(ORIGINALES) and os.listdir(ORIGINALES):
        return
    os.makedirs(ORIGINALES, exist_ok=True)
    for f in os.listdir(SONIDOS_STEAM):
        shutil.copy2(os.path.join(SONIDOS_STEAM, f), os.path.join(ORIGINALES, f))
    log("originales de Steam respaldados:", len(os.listdir(ORIGINALES)))


def archivos_del_paquete(nombre):
    """{archivo de Steam: ruta a usar} para un paquete ("Default" = originales)."""
    usar = {f: os.path.join(ORIGINALES, f) for f in os.listdir(ORIGINALES)}
    if nombre in ("Default", "None", "", None):
        return usar
    carpeta = os.path.join(PAQUETES, nombre)
    if not os.path.isdir(carpeta) and not bajar_paquete(nombre):
        return usar
    manifiesto = leer_json(os.path.join(carpeta, "pack.json"), {})
    ignorar = set(manifiesto.get("ignore", []))
    for f in usar:
        propio = os.path.join(carpeta, f)
        if f not in ignorar and os.path.exists(propio):
            usar[f] = propio
    return usar


def sonidos_al_dia(nombre):
    """True si los archivos de Steam ya son los del paquete (comparando tamanos)."""
    try:
        for f, origen in archivos_del_paquete(nombre).items():
            if os.path.getsize(os.path.join(SONIDOS_STEAM, f)) != os.path.getsize(origen):
                return False
        return True
    except OSError:
        return False


def poner_sonidos(nombre):
    for f, origen in archivos_del_paquete(nombre).items():
        shutil.copy2(origen, os.path.join(SONIDOS_STEAM, f))
    log("sonidos puestos:", nombre)


# ---------- ciclo ----------

def paquete_de_la_consola(estado):
    cfg = leer_json(sonidos.CONFIG_TEMA, {})
    mapa = leer_json(sonidos.MAPA, {})
    est_sonidos = leer_json(sonidos.ESTADO, {})
    if sonidos.color_por_consola(cfg, est_sonidos):
        log("color de fondo en automatico por cambio de consola")
    json.dump(est_sonidos, open(sonidos.ESTADO, "w"))
    # en Windows no hay musica de menu: solo cuenta el paquete de sonidos
    actual = {"selected_pack": estado.get("paquete", "Default"), "selected_music": "None"}
    sonidos.instalado = lambda p: p in ("Default", "None") or bool(p)
    paquete, _ = sonidos.elegir(cfg, mapa, actual, {})
    return paquete


def firma_juegos():
    """Cambia cuando se instala/quita un juego o se agrega un acceso no-Steam."""
    total = 0.0
    for c in portadas.bibliotecas():
        total += os.path.getmtime(c)
    for a in portadas.archivos_accesos():
        total += os.path.getmtime(a)
    return total


def vigilar():
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    estado = leer_json(ESTADO, {})
    ultima_cfg = ultima_juegos = None
    ultima_revision = 0
    log("PS XMB para Windows iniciado")
    while True:
        try:
            controles.poner()
        except Exception:
            pass  # Steam cerrado o sin el puerto de depuracion todavia
        try:
            mt = os.path.getmtime(sonidos.CONFIG_TEMA)
            ahora = time.time()
            if mt != ultima_cfg or ahora - ultima_revision > 60:
                ultima_cfg, ultima_revision = mt, ahora
                respaldar_originales()
                paquete = paquete_de_la_consola(estado)
                if paquete != estado.get("paquete") or not sonidos_al_dia(paquete):
                    poner_sonidos(paquete)
                    estado["paquete"] = paquete
                    json.dump(estado, open(ESTADO, "w"))
        except Exception as e:
            log("error en sonidos:", e)
        try:
            firma = firma_juegos()
            if firma != ultima_juegos and os.path.exists(portadas.CLAVE):
                ultima_juegos = firma
                sys.argv = [sys.argv[0]]
                portadas.main()
        except Exception as e:
            log("error en portadas:", e)
        time.sleep(3)


def instalar():
    """Arranque automatico: acceso directo en la carpeta Inicio del usuario, con
    pythonw (sin ventana). Tambien deja uno en el escritorio para prenderlo a mano."""
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    script = os.path.abspath(__file__)
    inicio = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
    for carpeta in (inicio, os.path.join(os.path.expanduser("~"), "Desktop")):
        lnk = os.path.join(carpeta, "PS XMB.lnk")
        ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
              f"$s.TargetPath='{pythonw}';$s.Arguments='\"{script}\"';"
              f"$s.WorkingDirectory='{os.path.dirname(script)}';$s.Save()")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    # Steam necesita este archivo para dejar entrar a CSS Loader y a este script
    bandera = os.path.join(portadas.STEAM, ".cef-enable-remote-debugging")
    if not os.path.exists(bandera):
        open(bandera, "w").close()
        print("Activado el modo depurador de Steam: cierra y vuelve a abrir Steam.")
    os.makedirs(os.path.join(os.path.expanduser("~"), "homebrew", "sounds"), exist_ok=True)
    clave = [a for a in sys.argv[1:] if not a.startswith("--")]
    if clave:
        sys.argv = [sys.argv[0], clave[0]]
        portadas.main()
    if "--sin-arrancar" in sys.argv:
        print("Listo: arranca solo al iniciar sesion (o con el acceso directo PS XMB).")
        return
    subprocess.Popen([pythonw, script], cwd=os.path.dirname(script))
    print("Listo: PS XMB queda corriendo y arranca solo al iniciar sesion.")


if __name__ == "__main__":
    if "--instalar" in sys.argv:
        instalar()
    else:
        vigilar()
