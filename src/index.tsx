import {
  ButtonItem,
  DropdownItem,
  Field,
  PanelSection,
  PanelSectionRow,
  TextField,
  ToggleField,
  staticClasses,
} from "@decky/ui";
import { callable, definePlugin } from "@decky/api";
import { Fragment, useEffect, useState } from "react";

type Paquete = { nombre: string; uso: string; ok: boolean };
type Opcion = { nombre: string; tipo: string; valores: string[]; valor: string };
type Estado = {
  instalado: boolean;
  consolas: string[];
  colores: string[];
  consola: string;
  color: string;
  ajustes: Record<string, boolean>;
  clave: boolean;
  ultimo: string;
  paquetes: Paquete[];
  opciones: Opcion[];
};

const getEstado = callable<[], Estado>("get_estado");
const setAjuste = callable<[clave: string, valor: boolean], Record<string, boolean>>("set_ajuste");
const guardarClave = callable<[clave: string], string>("guardar_clave");
const actualizarPortadas = callable<[], string>("actualizar_portadas");

// Las opciones del tema se cambian por medio de CSS Loader, asi su panel y el archivo
// de configuracion no quedan desfasados.
function cambiarOpcion(opcion: string, valor: string) {
  const loader = (window as any).DeckyPluginLoader;
  return loader.createLegacyPluginAPI("CSS Loader").callPluginMethod("set_patch_of_theme", {
    themeName: "PS XMB",
    patchName: opcion,
    value: valor,
  });
}

function pluginsInstalados(): string[] {
  return ((window as any).DeckyPluginLoader?.plugins ?? []).map((p: any) => p.name);
}

const opciones = (lista: string[]) => lista.map((v) => ({ data: v, label: v }));

// El resto de las opciones del tema (las mismas de CSS Loader), en un apartado que se
// abre y se cierra; se arma solo a partir del theme.json.
function MasOpciones({ estado, recargar }: { estado: Estado; recargar: () => void }) {
  const [abierto, setAbierto] = useState(false);
  const cambiar = async (nombre: string, valor: string) => {
    await cambiarOpcion(nombre, valor);
    setTimeout(recargar, 1500);
  };
  return (
    <PanelSection title="Mas opciones del tema">
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={() => setAbierto(!abierto)}>
          {(abierto ? "▾ Ocultar" : "▸ Mostrar") + ` (${estado.opciones.length})`}
        </ButtonItem>
      </PanelSectionRow>
      {abierto &&
        estado.opciones.map((o) => (
          <PanelSectionRow key={o.nombre}>
            {o.tipo === "checkbox" ? (
              <ToggleField
                label={o.nombre}
                checked={o.valor === "Si"}
                onChange={(v) => cambiar(o.nombre, v ? "Si" : "No")}
              />
            ) : (
              <DropdownItem
                label={o.nombre}
                selectedOption={o.valor}
                rgOptions={opciones(o.valores)}
                onChange={(x) => cambiar(o.nombre, x.data)}
              />
            )}
          </PanelSectionRow>
        ))}
    </PanelSection>
  );
}

// Lista de lo que el tema necesita, con lo que falta y que hacer.
function Requisitos({ estado }: { estado: Estado }) {
  const plugins = pluginsInstalados();
  const marca = (ok: boolean) => (ok ? "✅ " : "❌ ");
  const nota = (ok: boolean, titulo: string, siFalta: string) => (
    <PanelSectionRow>
      <Field label={marca(ok) + titulo} description={ok ? undefined : siFalta} focusable bottomSeparator="none" />
    </PanelSectionRow>
  );
  const faltan = estado.paquetes.filter((p) => !p.ok).map((p) => p.nombre);
  return (
    <PanelSection title="Lo que se necesita">
      {nota(plugins.includes("CSS Loader"), "CSS Loader (obligatorio)",
        "Instalalo desde la tienda de Decky. Es el que muestra el tema.")}
      {nota(estado.instalado, "Tema PS XMB (lo instala este plugin)",
        "No se pudo instalar. Reinicia la Deck; si sigue, reinstala el plugin.")}
      {nota(plugins.includes("Audio Loader"), "Audio Loader (para sonidos y musica)",
        "Opcional. Instalalo desde la tienda de Decky.")}
      {plugins.includes("Audio Loader") && (
        <PanelSectionRow>
          <Field
            label={marca(faltan.length === 0) +
              `Paquetes de sonidos y musica (${estado.paquetes.length - faltan.length} de ${estado.paquetes.length})`}
            description={
              <div>
                {/* la lista con sangria, como sublista del renglon */}
                <div style={{ marginInlineStart: "16px" }}>
                  {estado.paquetes.map((p) => (
                    <div key={p.nombre}>{marca(p.ok) + p.uso + ": " + p.nombre}</div>
                  ))}
                </div>
                {faltan.length > 0 && <div style={{ marginTop: "8px" }}>Bajalos en Audio Loader &gt; tienda.</div>}
              </div>
            }
            focusable
            bottomSeparator="none"
          />
        </PanelSectionRow>
      )}
      {nota(estado.clave, "Clave de SteamGridDB (para portadas)",
        "Opcional. Gratis en steamgriddb.com > Preferences > API; pegala arriba.")}
      <PanelSectionRow>
        <Field
          label="Notas"
          focusable
          bottomSeparator="none"
          description="El tema se elige aqui o en CSS Loader. Sin Audio Loader suenan los sonidos normales de Steam. Sin clave de SteamGridDB las tarjetas usan la portada recortada."
        />
      </PanelSectionRow>
    </PanelSection>
  );
}

function Panel() {
  const [estado, setEstado] = useState<Estado | null>(null);
  const [clave, setClave] = useState("");
  const [mensaje, setMensaje] = useState("");

  const recargar = async () => setEstado(await getEstado());

  useEffect(() => {
    recargar();
    const t = setInterval(recargar, 3000);
    return () => clearInterval(t);
  }, []);

  if (!estado) {
    return (
      <PanelSection>
        <PanelSectionRow>Cargando...</PanelSectionRow>
      </PanelSection>
    );
  }
  if (!estado.instalado) {
    return (
      <PanelSection title="PS XMB">
        <PanelSectionRow>Instalando el tema PS XMB... si no aparece, revisa que CSS Loader este instalado.</PanelSectionRow>
      </PanelSection>
    );
  }

  const interruptor = (id: string, titulo: string, descripcion: string) => (
    <PanelSectionRow>
      <ToggleField
        label={titulo}
        description={descripcion}
        checked={!!estado.ajustes[id]}
        onChange={async (v) => {
          await setAjuste(id, v);
          recargar();
        }}
      />
    </PanelSectionRow>
  );

  return (
    <Fragment>
      <PanelSection title="Tema">
        <PanelSectionRow>
          <DropdownItem
            label="Consola"
            rgOptions={opciones(estado.consolas)}
            selectedOption={estado.consola}
            onChange={async (o) => {
              await cambiarOpcion("Consola", o.data);
              setTimeout(recargar, 1500);
            }}
          />
        </PanelSectionRow>
        <PanelSectionRow>
          <DropdownItem
            label="Color de fondo"
            rgOptions={opciones(estado.colores)}
            selectedOption={estado.color}
            onChange={async (o) => {
              await cambiarOpcion("Color de fondo", o.data);
              setTimeout(recargar, 1500);
            }}
          />
        </PanelSectionRow>
      </PanelSection>
      <MasOpciones estado={estado} recargar={recargar} />
      <PanelSection title="Extras">
        {interruptor("sonidos", "Sonidos por consola", "Cambia los paquetes de Audio Loader segun la consola")}
        {interruptor("controles", "Columna de PS3 con arriba/abajo", "Traduce los botones en la columna del XMB")}
        {interruptor("portadas", "Portadas automaticas", "Baja portadas de SteamGridDB para juegos nuevos")}
      </PanelSection>
      <PanelSection title="SteamGridDB">
        <PanelSectionRow>
          <Field
            label={estado.clave ? "Clave guardada" : "Sin clave"}
            description="Sacala gratis en steamgriddb.com > Preferences > API"
          />
        </PanelSectionRow>
        <PanelSectionRow>
          <TextField
            label={estado.clave ? "Cambiar clave" : "Pegar clave"}
            value={clave}
            bIsPassword
            onChange={(e) => setClave(e.target.value)}
          />
        </PanelSectionRow>
        {clave && (
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={async () => {
                setMensaje(await guardarClave(clave));
                setClave("");
                recargar();
              }}
            >
              Guardar clave
            </ButtonItem>
          </PanelSectionRow>
        )}
        {estado.clave && (
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={async () => {
                setMensaje("Bajando portadas...");
                setMensaje(await actualizarPortadas());
                recargar();
              }}
            >
              Actualizar portadas ahora
            </ButtonItem>
          </PanelSectionRow>
        )}
        {(mensaje || estado.ultimo) && (
          <PanelSectionRow>
            <Field label={mensaje || estado.ultimo} focusable={false} />
          </PanelSectionRow>
        )}
      </PanelSection>
      <Requisitos estado={estado} />
    </Fragment>
  );
}

// Icono: los simbolos de PlayStation dibujados en SVG.
function Icono() {
  return (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinejoin="round">
      <path d="M6 3 L10 10 L2 10 Z" />
      <circle cx={18} cy={6.5} r={3.5} />
      <path d="M3 15 L9 21 M9 15 L3 21" />
      <rect x={14.5} y={14.5} width={7} height={7} />
    </svg>
  );
}

export default definePlugin(() => ({
  name: "PS XMB",
  titleView: <div className={staticClasses.Title}>PS XMB</div>,
  content: <Panel />,
  icon: <Icono />,
}));
