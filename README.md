<p align="center"><img src="docs/favicon.svg" alt="" width="96" height="96"></p>

<h1 align="center">Pieza</h1>

<p align="center"><b>Framework abierto para apps que viven en tu computador.</b><br>
<a href="https://pieza-app.github.io/pieza/">Página</a> · <a href="https://pieza-app.github.io/pieza/#empezar">Empezar</a> ·
<a href="https://github.com/pieza-app/pieza/discussions">Comunidad</a> · <a href="CONTRIBUTING.md">Cómo aportar</a></p>

Piezas probadas para armar apps abiertas que viven en tu computador. Cada pieza resuelve una cosa (tu IA, el idioma, el
catálogo, las actualizaciones…) y se enchufa en cualquier app de la familia con un comando, en vez de escribirla de cero.

Las usan [Minuta](https://github.com/minuta-app/minuta), [Graba](https://github.com/graba-app/graba),
[Corta](https://github.com/corta-app/corta), [Alcancía](https://github.com/alcancia-app/alcancia),
[Repasa](https://github.com/repasa-app/repasa) y [Esquema](https://github.com/esquema-app/esquema).

**Instala los flujos** (crear una app y revisar aportes) en tu IA y pídele «creemos una app para…»:

| Claude Code | Gemini CLI | Codex |
|---|---|---|
| `/plugin marketplace add pieza-app/pieza`<br>`/plugin install pieza@pieza` | `gemini extensions install https://github.com/pieza-app/pieza --auto-update` | `python3 herramientas/pieza.py skills instalar codex` |

Con otra IA, que siga [`AGENTS.md`](AGENTS.md). Equivalencias entre herramientas en [docs/otras-ias.md](docs/otras-ias.md).
**Sin IA**, la herramienta funciona sola:

```bash
python3 herramientas/pieza.py catalogo                    # todas las piezas, listas y en camino
python3 herramientas/pieza.py ficha ia transcribir --plataformas mac,windows,linux   # la app completa antes de crearla
python3 herramientas/pieza.py listar                      # qué hay
python3 herramientas/pieza.py iniciar ~/MiApp miapp MiApp  # una vez por app: crea app.json
python3 herramientas/pieza.py agregar ia ~/MiApp           # copia la pieza (y lo que necesita)
python3 herramientas/pieza.py estado ~/MiApp               # qué tiene, qué hay nuevo, qué cambió la app
python3 herramientas/pieza.py actualizar ~/MiApp           # trae lo nuevo sin pisar tus cambios
```

**Copiar y adueñarse.** La pieza se copia dentro de tu app y desde ahí es tuya: la puedes cambiar. `piezas.json` recuerda la
versión y la huella de cada archivo, así `actualizar` nunca pisa lo que cambiaste y `diferencias` te muestra qué mejoraste para
devolverlo a la base.

- [El enchufe](docs/enchufe.md): cómo se conecta una pieza (contrato y reglas de seguridad).
- [Catálogo y plan](docs/catalogo.md): qué hay y qué viene.
- [Crear una app nueva](skills/lanzar-proyecto-open-source/SKILL.md): el flujo completo, con entrevista y ficha
  (`pieza.py ficha ia transcribir --plataformas mac,windows,linux` muestra pantallas, configuración, permisos y red).
- [Guía para contribuir](AGENTS.md).

**Al día solo.** Cada pieza dice qué tipo de cambio trae (arreglo, mejora, rompe, seguridad). Las apps reciben un PR semanal con
lo que se puede actualizar solo y un issue con los pasos para lo demás ([cómo](docs/enchufe.md#versiones-y-actualizaciones)).

**¿Hiciste una app con Pieza?** Ponle el topic `hecho-con-pieza` a su repo y aparece en la [página](https://pieza-app.github.io/pieza/).
Y si quieres, el sello: [![Hecho con Pieza](https://pieza-app.github.io/pieza/sello.svg)](https://pieza-app.github.io/pieza/)

Sin dependencias: Python con su biblioteca estándar. Licencia AGPL-3.0.

---

**English:** Pieza is an open framework of tested pieces for apps that live on your computer (your own AI, languages, safe
updates, a community catalog). Install the flows in Claude Code, Gemini CLI or Codex (table above) and ask for “let's build an
app for…”. Everything is documented in Spanish; any AI can follow it in your language.
