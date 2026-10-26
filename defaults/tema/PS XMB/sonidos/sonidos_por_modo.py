#!/usr/bin/env python3
"""Cambia los sonidos y la musica de Audio Loader segun la consola elegida en PS XMB.

- PS2 -> sonidos y ambiente de PS2, PS3 -> sonidos del XMB y musica del menu
  de PS3, PS4 -> sonidos de PS4, PS5 -> sonidos de PS5, Steam Deck -> los normales.
- Donde no hay musica de esa consola, regresa la musica que tenias elegida.
- Al cambiar de consola, el color de fondo regresa a "Automatico (de la consola)";
  si despues eliges otro color, se respeta hasta que cambies de consola otra vez.

Los nombres de los paquetes estan en sonidos.json (junto a este script); si los
tuyos se llaman distinto, cambialos ahi. Un paquete que no este instalado se ignora.

Necesita el plugin Audio Loader y los paquetes bajados desde su tienda. Se instala
una vez y luego trabaja solo cada vez que cambias una opcion en CSS Loader:

    python3 ~/homebrew/themes/PS\\ XMB/sonidos/sonidos_por_modo.py --instalar-auto
"""
import base64
import json
import os
import shutil
import socket
import sys
import urllib.request

TEMA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_TEMA = os.path.join(TEMA, "config_USER.json")
SONIDOS = os.path.expanduser("~/homebrew/sounds")
CONFIG_AUDIO = os.path.join(SONIDOS, "config.json")
MAPA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sonidos.json")
# la musica que el usuario tenia antes de que pusieramos la de una consola
ESTADO = os.path.expanduser("~/.config/psxmb_sonidos.json")


def instalado(paquete):
    return paquete in ("Default", "None") or os.path.isdir(os.path.join(SONIDOS, paquete))


# sonidos que algunos paquetes no traen -> con que sonido del mismo paquete se rellenan
# (si falta uno, Audio Loader deja sonar el de Steam encima del del paquete; p. ej. en
# la cuadricula de la Biblioteca se oian los dos)
RELLENOS = {
    "deck_ui_tile_scroll.wav": ["deck_ui_navigation.wav"],
    "bumper_end.wav": ["deck_ui_bumper_end_02.wav", "deck_ui_navigation.wav"],
    "deck_ui_bumper_end_02.wav": ["bumper_end.wav", "deck_ui_navigation.wav"],
    "confirmation_positive.wav": ["deck_ui_default_activation.wav", "deck_ui_into_game_detail.wav"],
    "deck_ui_default_activation.wav": ["confirmation_positive.wav", "deck_ui_into_game_detail.wav"],
    "confirmation_negative.wav": ["deck_ui_out_of_game_detail.wav", "deck_ui_hide_modal.wav"],
}


def completar_paquete(nombre):
    """Copia del paquete con los sonidos que le faltan rellenados (ver RELLENOS), en
    "<nombre> (PS XMB)". Si no hace falta rellenar nada, se usa el original."""
    origen = os.path.join(SONIDOS, nombre)
    manifiesto = os.path.join(origen, "pack.json")
    if nombre in ("Default", "None") or not os.path.exists(manifiesto):
        return nombre
    with open(manifiesto) as f:
        datos = json.load(f)
    ignorar = set(datos.get("ignore", []))
    tiene = lambda a: a not in ignorar and os.path.exists(os.path.join(origen, a))
    rellenar = {}
    for archivo, opciones in RELLENOS.items():
        if not tiene(archivo):
            fuente = next((o for o in opciones if tiene(o)), None)
            if fuente:
                rellenar[archivo] = fuente
    if not rellenar:
        return nombre
    completo = nombre + " (PS XMB)"
    destino = os.path.join(SONIDOS, completo)
    hecho = os.path.join(destino, "pack.json")
    # se rehace solo si el paquete original cambio despues de la copia
    if not os.path.exists(hecho) or os.path.getmtime(hecho) < os.path.getmtime(manifiesto):
        shutil.rmtree(destino, ignore_errors=True)
        shutil.copytree(origen, destino)
        for archivo, fuente in rellenar.items():
            shutil.copy2(os.path.join(origen, fuente), os.path.join(destino, archivo))
        datos.update({"name": completo, "ignore": sorted(ignorar - set(rellenar))})
        datos.pop("id", None)  # para que la tienda no lo confunda con el original
        with open(hecho, "w") as f:
            json.dump(datos, f, indent=2)
    return completo


def elegir(cfg_tema, mapa, audio, estado):
    """Devuelve (paquete, musica) que tocan segun la consola elegida en el tema."""
    clave = cfg_tema.get("Consola", "").split(" ")[0].lower().replace("steam", "steam_deck")
    paquete = mapa.get("sonidos_" + clave) or mapa["sonidos_steam_deck"]
    if not instalado(paquete):
        paquete = audio.get("selected_pack", "Default")
    else:
        paquete = completar_paquete(paquete)

    nuestras = {v for k, v in mapa.items() if k.startswith("musica_") and v}
    actual = audio.get("selected_music", "None")
    if actual not in nuestras:
        estado["musica_usuario"] = actual
    musica = mapa.get("musica_" + clave)
    if not musica or not instalado(musica):
        musica = estado.get("musica_usuario", actual)
    return paquete, musica


COLOR_AUTO = "Automatico (de la consola)"


def color_por_consola(cfg_tema, estado):
    """Si cambio la consola desde la ultima vez, regresa el color al de la consola.
    Devuelve True si toco la configuracion del tema."""
    consola = cfg_tema.get("Consola")
    previa = estado.get("consola")
    estado["consola"] = consola
    if previa is None or previa == consola or cfg_tema.get("Color de fondo") == COLOR_AUTO:
        return False
    cfg_tema["Color de fondo"] = COLOR_AUTO
    json.dump(cfg_tema, open(CONFIG_TEMA, "w"))
    # CSS Loader vuelve a leer la configuracion cuando cambia un archivo del tema
    os.utime(os.path.join(TEMA, "theme.json"))
    print(f"Consola {previa} -> {consola}: color de fondo en automatico")
    return True


def evaluar_en_steam(js, es_pestana=lambda t: t["title"] == "SharedJSContext"):
    """Corre JS en una ventana de Steam por su depurador (localhost:8080); por defecto
    el contexto de Decky (SharedJSContext). WebSocket minimo con la libreria estandar
    para no depender de paquetes extra."""
    pestanas = json.load(urllib.request.urlopen("http://localhost:8080/json", timeout=5))
    ws_url = next(t["webSocketDebuggerUrl"] for t in pestanas if es_pestana(t))
    ruta = ws_url.split("localhost:8080", 1)[1]
    s = socket.create_connection(("localhost", 8080), timeout=15)
    llave = base64.b64encode(os.urandom(16)).decode()
    s.sendall((f"GET {ruta} HTTP/1.1\r\nHost: localhost:8080\r\nUpgrade: websocket\r\n"
               f"Connection: Upgrade\r\nSec-WebSocket-Key: {llave}\r\n"
               "Sec-WebSocket-Version: 13\r\n\r\n").encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        resp += s.recv(4096)
    datos = json.dumps({"id": 1, "method": "Runtime.evaluate",
                        "params": {"expression": js, "awaitPromise": True,
                                   "returnByValue": True}}).encode()
    mascara = os.urandom(4)
    largo = len(datos)
    cab = bytes([0x81]) + (bytes([0x80 | largo]) if largo < 126
                           else bytes([0x80 | 126]) + largo.to_bytes(2, "big"))
    s.sendall(cab + mascara + bytes(b ^ mascara[i % 4] for i, b in enumerate(datos)))
    sobra = resp.split(b"\r\n\r\n", 1)[1]
    while True:  # lee tramas hasta la respuesta con id 1
        while len(sobra) < 2:
            sobra += s.recv(4096)
        n = sobra[1] & 0x7F
        inicio = 2
        if n == 126:
            n, inicio = int.from_bytes(sobra[2:4], "big"), 4
        elif n == 127:
            n, inicio = int.from_bytes(sobra[2:10], "big"), 10
        while len(sobra) < inicio + n:
            sobra += s.recv(65536)
        trama, sobra = sobra[inicio:inicio + n], sobra[inicio + n:]
        try:
            msg = json.loads(trama)
        except ValueError:
            continue
        if msg.get("id") == 1:
            s.close()
            return msg


def recargar_audio_loader():
    """Audio Loader solo lee su config al cargar; Decky lo recarga sin reiniciar Steam.
    Antes se le pide a su parte interna que vuelva a buscar paquetes (solo lo hace al
    arrancar), para que un paquete bajado despues no quede en silencio."""
    js = ("(async () => { const L = window.DeckyPluginLoader;"
          " const p = L.plugins.find(p => p.name === 'Audio Loader');"
          " if (!p) return 'sin Audio Loader';"
          " await L.createLegacyPluginAPI(p.name).callPluginMethod('parse_packs', {});"
          " await L.importPlugin(p.name, p.version, p.loadType); return 'ok'; })()")
    return evaluar_en_steam(js).get("result", {}).get("result", {}).get("value")


def instalar_auto():
    """Servicio de usuario que corre este script cada vez que CSS Loader guarda las
    opciones del tema (config_USER.json)."""
    unidades = os.path.expanduser("~/.config/systemd/user")
    os.makedirs(unidades, exist_ok=True)
    script = os.path.abspath(__file__)
    open(os.path.join(unidades, "psxmb-sonidos.service"), "w").write(
        # sin limite de arranques: CSS Loader guarda varias veces seguidas al cambiar
        # opciones, y el script solo escribe la config al cambiar de consola (no hay ciclo)
        "[Unit]\nDescription=PS XMB: sonidos segun el modo\nStartLimitIntervalSec=0\n\n"
        "[Service]\nType=oneshot\n"
        # junta las escrituras seguidas en una sola corrida
        f'ExecStartPre=/usr/bin/sleep 1\nExecStart=/usr/bin/python3 "{script}"\n')
    open(os.path.join(unidades, "psxmb-sonidos.path"), "w").write(
        "[Unit]\nDescription=PS XMB: vigila las opciones del tema\n\n[Path]\n"
        f"PathChanged={CONFIG_TEMA}\nTriggerLimitIntervalSec=0\n\n[Install]\nWantedBy=default.target\n")
    os.system("systemctl --user daemon-reload && systemctl --user enable --now psxmb-sonidos.path")
    print("Listo: los sonidos van a cambiar solos con la forma de tarjetas y el fondo.")


def main():
    if "--instalar-auto" in sys.argv:
        instalar_auto()
    if not os.path.exists(CONFIG_AUDIO) or not os.path.exists(CONFIG_TEMA):
        sys.exit("Falta Audio Loader o la configuracion del tema")
    cfg_tema = json.load(open(CONFIG_TEMA))
    mapa = json.load(open(MAPA))
    audio = json.load(open(CONFIG_AUDIO))
    estado = json.load(open(ESTADO)) if os.path.exists(ESTADO) else {}
    color_por_consola(cfg_tema, estado)
    paquete, musica = elegir(cfg_tema, mapa, audio, estado)
    json.dump(estado, open(ESTADO, "w"))
    if (paquete, musica) == (audio.get("selected_pack"), audio.get("selected_music")):
        print(f"Sin cambios: {paquete} / {musica}")
        return
    audio["selected_pack"], audio["selected_music"] = paquete, musica
    json.dump(audio, open(CONFIG_AUDIO, "w"))
    os.sync()
    try:
        print("Audio Loader:", recargar_audio_loader())
    except Exception as e:
        # sin Steam abierto se aplica al siguiente arranque, porque ya quedo en la config
        print("No se pudo recargar Audio Loader ahora:", e)
    print(f"Sonidos: {paquete} | Musica: {musica}")


if __name__ == "__main__":
    main()
