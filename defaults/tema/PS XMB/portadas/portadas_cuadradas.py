#!/usr/bin/env python3
"""Portadas cuadradas de SteamGridDB para el tema PS XMB.

Se corre una vez en la Steam Deck (Konsole en modo escritorio, o por SSH):

    python3 ~/homebrew/themes/PS\\ XMB/portadas/portadas_cuadradas.py TU_CLAVE

La clave sale gratis en https://www.steamgriddb.com/profile/preferences/api

Ese comando guarda la clave, baja para cada juego de Steam instalado y cada acceso
no-Steam una portada cuadrada (512x512 o 1024x1024, para PS2 / PS4 / PS5) y una
horizontal (460x215 o 920x430, para los iconos del XMB de PS3), y deja la Deck
vigilando: cuando instalas o agregas un juego, baja las suyas solas.

Las imagenes y su CSS van en un tema aparte, "PS XMB Portadas", que este script
crea; asi las actualizaciones de PS XMB desde la tienda no las borran. Activalo una
vez en CSS Loader. Cada tipo de portada solo se aplica con las tarjetas que le
tocan; con "Steam Deck" se ven las portadas normales. No toca las imagenes de Steam.

Otros usos:
    python3 portadas_cuadradas.py              # correr a mano con la clave guardada
    python3 portadas_cuadradas.py --instalar-auto
"""
import json
import os
import re
import struct
import sys
import time
import urllib.parse
import urllib.request

def carpeta_steam():
    """En Windows Steam guarda su carpeta en el registro; en la Deck es fija."""
    if os.name == "nt":
        import winreg
        for raiz, llave in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")):
            try:
                with winreg.OpenKey(raiz, llave) as k:
                    for nombre in ("SteamPath", "InstallPath"):
                        try:
                            return os.path.normpath(winreg.QueryValueEx(k, nombre)[0])
                        except OSError:
                            pass
            except OSError:
                pass
        return r"C:\Program Files (x86)\Steam"
    return os.path.expanduser("~/.local/share/Steam")


STEAM = carpeta_steam()
TEMAS = os.path.expanduser("~/homebrew/themes")
NOMBRE = "PS XMB Portadas"
COMPANERO = os.path.join(TEMAS, NOMBRE)
CSS = os.path.join(COMPANERO, "portadas.css")
URL_BASE = "/themes_custom/" + urllib.parse.quote(NOMBRE) + "/"
# tipos de portada: carpeta, tamanos en SteamGridDB y la marca que las tarjetas del
# tema ponen en la fila para pedir ese tipo
TIPOS = [
    {"nombre": "cuadrada", "carpeta": "img", "tamanos": "512x512,1024x1024",
     "marca": "--psx-cuadradas"},
    {"nombre": "horizontal", "carpeta": "img_ancho", "tamanos": "460x215,920x430",
     "marca": "--psx-ancho"},
]
API = "https://www.steamgriddb.com/api/v2"
CLAVE = os.path.expanduser("~/.config/psxmb_sgdb_key")
# juegos sin portada de un tipo (sin_portada.json en su carpeta), para no preguntar
# por ellos en cada corrida
REINTENTAR = 7 * 24 * 3600  # se vuelven a buscar cada 7 dias
# nombre -> id de SteamGridDB para los que la busqueda por nombre encuentra mal
AJUSTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ajustes_portadas.json")


def clave_api():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        os.makedirs(os.path.dirname(CLAVE), exist_ok=True)
        with open(CLAVE, "w") as f:
            f.write(args[0].strip())
        os.chmod(CLAVE, 0o600)
        return args[0].strip()
    if os.path.exists(CLAVE):
        return open(CLAVE).read().strip()
    sys.exit("Falta la clave de SteamGridDB (ver la ayuda al inicio del script)")


def pedir(url, clave):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + clave,
                                               "User-Agent": "psxmb-portadas"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def bibliotecas():
    """Carpetas steamapps de todas las bibliotecas (interna y microSD)."""
    carpetas = [os.path.join(STEAM, "steamapps")]
    lf = os.path.join(STEAM, "steamapps", "libraryfolders.vdf")
    if os.path.exists(lf):
        for ruta in re.findall(r'"path"\s+"([^"]+)"', open(lf, errors="ignore").read()):
            if os.path.isdir(os.path.join(ruta, "steamapps")):
                carpetas.append(os.path.join(ruta, "steamapps"))
    return sorted(set(carpetas))


def juegos_steam():
    """(id, nombre) de cada juego instalado, leyendo los appmanifest de cada biblioteca."""
    vistos = {}
    for c in bibliotecas():
        for f in os.listdir(c):
            if f.startswith("appmanifest_") and f.endswith(".acf"):
                txt = open(os.path.join(c, f), errors="ignore").read()
                appid = re.search(r'"appid"\s+"(\d+)"', txt)
                nombre = re.search(r'"name"\s+"([^"]+)"', txt)
                if appid and nombre:
                    vistos[appid.group(1)] = nombre.group(1)
    # herramientas de Steam (Proton, runtimes) no son juegos
    return [(a, n) for a, n in vistos.items()
            if not re.search(r"Proton|Steam Linux Runtime|Steamworks|Redistributable", n)]


def archivos_accesos():
    salida = []
    for usuario in os.listdir(os.path.join(STEAM, "userdata")):
        ruta = os.path.join(STEAM, "userdata", usuario, "config", "shortcuts.vdf")
        if os.path.exists(ruta):
            salida.append(ruta)
    return salida


def accesos_no_steam():
    """(id, nombre) de shortcuts.vdf (VDF binario). El id es el appid sin signo."""
    salida = []
    for ruta in archivos_accesos():
        datos = open(ruta, "rb").read()
        for m in re.finditer(rb"\x02appid\x00(.{4})", datos, re.S):
            appid = struct.unpack("<I", m.group(1))[0]
            resto = datos[m.end():m.end() + 600]
            n = re.search(rb"\x01(?:AppName|appname)\x00([^\x00]*)\x00", resto)
            if n:
                salida.append((str(appid), n.group(1).decode("utf-8", "ignore")))
    return salida


def id_sgdb(clave, appid, nombre, es_steam, ajustes):
    if nombre in ajustes:
        return ajustes[nombre]
    try:
        if es_steam:
            return pedir(f"{API}/games/steam/{appid}", clave)["data"]["id"]
    except Exception:
        pass  # si no lo encuentra por appid, se busca por nombre
    r = pedir(f"{API}/search/autocomplete/{urllib.parse.quote(nombre)}", clave)
    return r["data"][0]["id"] if r.get("data") else None


def buscar_portada(clave, gid, tamanos):
    q = f"dimensions={tamanos}&types=static&nsfw=false&humor=false"
    r = pedir(f"{API}/grids/game/{gid}?{q}", clave)
    return r["data"][0]["url"] if r.get("data") else None


def preparar_companero():
    """Crea el tema "PS XMB Portadas" la primera vez, ya activado."""
    for tipo in TIPOS:
        os.makedirs(os.path.join(COMPANERO, tipo["carpeta"]), exist_ok=True)
    tj = os.path.join(COMPANERO, "theme.json")
    if not os.path.exists(tj):
        json.dump({
            "name": NOMBRE,
            "author": "PS XMB",
            "version": "v1.0",
            "manifest_version": 9,
            "target": "System-Wide",
            "description": "Portadas de SteamGridDB para PS XMB (cuadradas y horizontales). "
                           "Las genera portadas_cuadradas.py.",
            "inject": {"portadas.css": ["SP"]},
        }, open(tj, "w"), indent=2)
    cfg = os.path.join(COMPANERO, "config_USER.json")
    if not os.path.exists(cfg):
        json.dump({"active": True}, open(cfg, "w"))


def generar_css():
    """Una regla por imagen guardada; cubre las tres formas de direccion de portada.
    Cada tipo va dentro de un @container que solo se cumple cuando las tarjetas de PS XMB
    ponen su marca en la fila (p. ej. tarjetas-ps4.css pone --psx-cuadradas: si)."""
    bloques, total = [], 0
    for tipo in TIPOS:
        carpeta = os.path.join(COMPANERO, tipo["carpeta"])
        reglas = []
        for f in sorted(os.listdir(carpeta)):
            appid, ext = os.path.splitext(f)
            if not appid.isdigit():
                continue
            sel = ",\n  ".join(
                f'.basicgamecarousel_BasicGameCarousel img[src*="/customimages/{appid}{s}"]'
                for s in ("p.", ".")) + \
                f',\n  .basicgamecarousel_BasicGameCarousel img[src*="/assets/{appid}/"]'
            reglas.append(f'  {sel} {{\n    content: url("{URL_BASE}{tipo["carpeta"]}/{f}");\n  }}')
        total += len(reglas)
        bloques.append(f'@container style({tipo["marca"]}: si) {{\n' + "\n\n".join(reglas) + "\n}\n")
    cab = ("/* Generado por portadas_cuadradas.py (tema PS XMB): portadas de SteamGridDB\n"
           "   para cada juego, cada tipo solo con las tarjetas que le tocan. */\n\n")
    open(CSS, "w").write(cab + "\n".join(bloques))
    return total


def instalar_auto():
    """Servicio de usuario de systemd que corre este script cuando cambian los juegos
    instalados (appmanifest) o los accesos no-Steam (shortcuts.vdf), y una vez al dia
    para reintentar los que no tenian portada. Queda en ~/.config, que las
    actualizaciones de SteamOS no borran."""
    if os.name == "nt":
        print("En Windows lo vigila windows/psxmb_windows.py (ver windows/LEEME.txt).")
        return
    vigilar = bibliotecas() + archivos_accesos()
    unidades = os.path.expanduser("~/.config/systemd/user")
    os.makedirs(unidades, exist_ok=True)
    script = os.path.abspath(__file__)
    open(os.path.join(unidades, "psxmb-portadas.service"), "w").write(
        "[Unit]\nDescription=PS XMB: portadas cuadradas de SteamGridDB\n"
        "After=network-online.target\n\n[Service]\nType=oneshot\n"
        # espera a que Steam termine de escribir antes de leer
        f'ExecStartPre=/usr/bin/sleep 20\nExecStart=/usr/bin/python3 "{script}"\n')
    open(os.path.join(unidades, "psxmb-portadas.path"), "w").write(
        "[Unit]\nDescription=PS XMB: vigila juegos nuevos\n\n[Path]\n"
        + "".join(f"PathChanged={v}\n" for v in vigilar)
        + "\n[Install]\nWantedBy=default.target\n")
    open(os.path.join(unidades, "psxmb-portadas.timer"), "w").write(
        "[Unit]\nDescription=PS XMB: reintento diario de portadas\n\n[Timer]\n"
        "OnCalendar=daily\nPersistent=true\n\n[Install]\nWantedBy=timers.target\n")
    os.system("systemctl --user daemon-reload && "
              "systemctl --user enable --now psxmb-portadas.path psxmb-portadas.timer")
    print("Vigilando:", *vigilar, sep="\n  ")


def main():
    if "--instalar-auto" in sys.argv:
        return instalar_auto()
    clave_nueva = any(not a.startswith("--") for a in sys.argv[1:])
    clave = clave_api()
    preparar_companero()
    ajustes = json.load(open(AJUSTES)) if os.path.exists(AJUSTES) else {}
    ajustes.pop("_ayuda", None)
    juegos = [(a, n, True) for a, n in juegos_steam()] + \
             [(a, n, False) for a, n in accesos_no_steam()]
    print(f"{len(juegos)} juegos encontrados")
    bajadas = ya = sin = 0
    ahora = time.time()
    gids = {}  # el id de SteamGridDB se busca una vez por juego, sirve para los dos tipos
    for tipo in TIPOS:
        carpeta = os.path.join(COMPANERO, tipo["carpeta"])
        archivo_sin = os.path.join(carpeta, "sin_portada.json")
        sin_portada = json.load(open(archivo_sin)) if os.path.exists(archivo_sin) else {}
        existentes = os.listdir(carpeta)
        for appid, nombre, es_steam in juegos:
            if any(f.startswith(appid + ".") for f in existentes):
                ya += 1
                continue
            if ahora - sin_portada.get(appid, 0) < REINTENTAR:
                sin += 1
                continue
            try:
                if appid not in gids:
                    gids[appid] = id_sgdb(clave, appid, nombre, es_steam, ajustes)
                gid = gids[appid]
                url = buscar_portada(clave, gid, tipo["tamanos"]) if gid else None
                if not url:
                    print(f"  sin portada {tipo['nombre']}: {nombre}")
                    sin_portada[appid] = ahora
                    sin += 1
                    continue
                ext = os.path.splitext(urllib.parse.urlparse(url).path)[1] or ".png"
                # el CDN de imagenes rechaza (403) el User-Agent por defecto de urllib
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 psxmb-portadas"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    open(os.path.join(carpeta, appid + ext), "wb").write(r.read())
                print(f"  ok ({tipo['nombre']}): {nombre}")
                sin_portada.pop(appid, None)
                bajadas += 1
                time.sleep(0.3)  # no saturar la API
            except Exception as e:
                # errores de red no se recuerdan: se reintenta en la siguiente corrida
                print(f"  error con {nombre}: {e}")
                sin += 1
        json.dump(sin_portada, open(archivo_sin, "w"))
    if bajadas or not os.path.exists(CSS) or "content:" not in open(CSS).read():
        n = generar_css()
        # CSS Loader recarga el tema cuando cambia algun archivo; solo si hubo algo nuevo
        os.utime(os.path.join(COMPANERO, "theme.json"))
    else:
        n = open(CSS).read().count("content:")
    if hasattr(os, "sync"):
        os.sync()
    print(f"Listo: {bajadas} nuevas, {ya} ya estaban, {sin} sin portada. {n} reglas en el CSS.")
    # la primera vez (con clave nueva) deja la Deck vigilando juegos nuevos
    if clave_nueva:
        instalar_auto()
        print(f'\nActiva el tema "{NOMBRE}" en CSS Loader si no aparece activo.')


if __name__ == "__main__":
    main()
