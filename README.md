<p align="center"><img src="docs/favicon.svg" alt="" width="96" height="96"></p>

<h1 align="center">Pieza</h1>

<p align="center"><b>Framework modular y abierto para apps que viven en tu computador.</b><br>
<a href="https://pieza-app.github.io/pieza/">Página</a> · <a href="https://pieza-app.github.io/pieza/#empezar">Empezar</a> ·
<a href="https://github.com/pieza-app/pieza/wiki">Wiki</a> · <a href="MANIFIESTO.md">Manifiesto</a> ·
<a href="https://github.com/pieza-app/pieza/discussions">Comunidad</a> · <a href="CONTRIBUTING.md">Cómo aportar</a></p>

<p align="center"><i>Construimos en abierto. Compartimos lo que funciona. Nadie es dueño de tu computador más que tú.</i></p>

Pieza arma una app por módulos. Cada módulo es una **pieza**. Una pieza resuelve una sola cosa: tu IA, el idioma, el catálogo,
las actualizaciones. Un comando la agrega a cualquier app. Así no la escribes de cero.

> **En construcción.** Las piezas salen de seis apps: [Minuta](https://github.com/minuta-app/minuta),
> [Graba](https://github.com/graba-app/graba), [Corta](https://github.com/corta-app/corta),
> [Alcancía](https://github.com/alcancia-app/alcancia), [Repasa](https://github.com/repasa-app/repasa) y
> [Esquema](https://github.com/esquema-app/esquema). Esas apps pasan a usarlas una por una. El [catálogo](docs/catalogo.md) dice
> qué piezas están listas. Las [issues](https://github.com/pieza-app/pieza/issues) dicen cuáles faltan.

## La app de escritorio

Toda app de Pieza usa la pieza `host-tauri` (Rust + Tauri) en Mac, Windows y Linux. Es un solo código para los tres sistemas.
Usa el navegador que ya trae el sistema. Por eso la app es liviana.

- Hechas con `host-tauri`: Alcancía, Corta, Despeja, Esquema y Repasa.
- Falta: Graba y Minuta. Usan funciones que solo existen en Apple (capturar la pantalla y el audio del sistema). Primero necesitan
  un ayudante en Swift.

## Crear una app con tu IA

1. Instala los flujos de Pieza en tu IA (tabla de abajo).
2. Pídele: «creemos una app para…».

| Claude Code | Gemini CLI | Codex |
|---|---|---|
| `/plugin marketplace add pieza-app/pieza`<br>`/plugin install pieza@pieza` | `gemini extensions install https://github.com/pieza-app/pieza --auto-update` | `python3 herramientas/pieza.py skills instalar codex` |

Con otra IA, sigue [`AGENTS.md`](AGENTS.md). La tabla de equivalencias está en [docs/otras-ias.md](docs/otras-ias.md).

## Crear una app sin IA

La herramienta funciona sola:

```bash
python3 herramientas/pieza.py catalogo                    # todas las piezas, listas y en camino
python3 herramientas/pieza.py ficha ia transcribir --plataformas mac,windows,linux   # la app completa antes de crearla
python3 herramientas/pieza.py listar                      # qué hay
python3 herramientas/pieza.py crear ~/MiApp --id miapp --nombre MiApp --piezas ia   # una app nueva andando, de una vez
python3 herramientas/pieza.py agregar transcribir ~/MiApp  # otra pieza después (y lo que necesita)
python3 herramientas/pieza.py iniciar ~/OtraApp otraapp OtraApp  # en una app que ya existe: solo app.json, y después agregar
python3 herramientas/pieza.py estado ~/MiApp               # qué tiene, qué hay nuevo, qué cambió la app
python3 herramientas/pieza.py actualizar ~/MiApp           # trae lo nuevo sin pisar tus cambios
```

## Copiar y adueñarse

- La pieza se copia dentro de tu app. Desde ahí es tuya y la puedes cambiar.
- `piezas.json` guarda la versión y la huella de cada archivo.
- `actualizar` nunca pisa lo que cambiaste.
- `diferencias` muestra lo que mejoraste. Así lo devuelves a la base.

## Más información

- [Wiki](https://github.com/pieza-app/pieza/wiki): guías paso a paso.
- [El enchufe](docs/enchufe.md): cómo se conecta una pieza (contrato y reglas de seguridad).
- [Catálogo y plan](docs/catalogo.md): qué hay y qué viene.
- [Crear una app nueva](skills/lanzar-proyecto-open-source/SKILL.md): el flujo completo, con entrevista y ficha.
  `pieza.py ficha ia transcribir --plataformas mac,windows,linux` muestra pantallas, configuración, permisos y red.
- [Guía para contribuir](AGENTS.md).

## Al día solo

- Cada pieza dice qué tipo de cambio trae: arreglo, mejora, rompe o seguridad.
- Cada semana, la app recibe un PR con lo que se actualiza solo ([cómo](docs/enchufe.md#versiones-y-actualizaciones)).
- Lo demás llega en un issue, con sus pasos.

## La comunidad

- **Tu pieza:** publícala en tu repo con el topic `pieza-comunidad`. Aparece en la página como «Sin revisar». Después de la
  revisión, se instala como segura ([cómo](docs/comunidad.md)).
- **Tu app hecha con Pieza:** ponle el topic `hecho-con-pieza` a su repo. Aparece en la [página](https://pieza-app.github.io/pieza/).
- **El sello:** [![Hecho con Pieza](https://pieza-app.github.io/pieza/sello.svg)](https://pieza-app.github.io/pieza/)

Pieza no tiene fines de lucro, cuentas ni telemetría. [Lee el manifiesto](MANIFIESTO.md) y súmate.

## Requisitos

- Python con su biblioteca estándar. Sin dependencias.
- Rust, solo para compilar la app de escritorio.

## Licencias

- Las piezas (`piezas/`) son [MPL-2.0](piezas/LICENSE). Si cambias un archivo de una pieza, compartes ese cambio. La app que la
  usa puede tener la licencia que quiera.
- Las herramientas (`herramientas/`, las skills y la página) son [AGPL-3.0](LICENSE).

*Pieces are MPL-2.0; tools are AGPL-3.0.*

---

**English:** Pieza is an open framework of tested pieces for apps that live on your computer: your own AI, languages, safe
updates and a community catalog. One desktop host (`host-tauri`, Rust + Tauri) runs every app on Mac, Windows and Linux.
Install the flows in Claude Code, Gemini CLI or Codex (table above). Then ask: “let's build an app for…”. The documentation is in
Spanish. Any AI can explain it in your language.
