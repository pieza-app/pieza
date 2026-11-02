# Pieza «github» — el repo listo para la comunidad

Lo que cada app copiaba de Esquema o de Alcancía y adaptaba a mano: las plantillas de GitHub, los workflows de revisión, las guías
para aportar y la configuración del repo. **Generado desde `app.json`** con las plantillas de Pieza (`docs/enchufe.md`,
«Plantillas»). Agrégala **al final**, después de las demás piezas: `AGENTS.md` y `CONTRIBUTING.md` nombran las que ya están.

```bash
python3 herramientas/pieza.py agregar github <app>
python3 herramientas/pieza.py repo configurar <app>             # muestra los comandos de gh (no toca nada)
python3 herramientas/pieza.py repo configurar <app> --aplicar   # los corre (gh con permisos de admin del repo)
```

## Qué genera

Se mantienen al día (huella en `piezas.json`; si la app los cambia, son de la app):

| Archivo | Qué es |
|---|---|
| `.github/ISSUE_TEMPLATE/error.yml`, `idea.yml`, `config.yml` | Error (con las plataformas de la app), idea y los enlaces a la falla de seguridad privada y a Discussions. |
| `.github/dependabot.yml` | Actions y, si hay, npm de `escritorio/` y `movil/`, con `cooldown`. |
| `.github/workflows/revisar.yml` | `bash pruebas/correr.sh` en `ubuntu-24.04` con Playwright 1.56.1 y capturas; job `mac` en `macos-15` que compila `app/` solo si cambió `app/`, `app.json`, `acciones.json` o el empaquetado. |
| `.github/workflows/pieza-al-dia.yml` | La de `plantillas/` de Pieza (una prueba exige que sean iguales). |
| `.claude/settings.json` | Solo `extraKnownMarketplaces` de Pieza: Claude Code **ofrece** sus flujos (nunca `enabledPlugins`). |
| `herramientas/revisar_privacidad.sh` | `.terminos-privados` (local) antes de cada commit; `--generico` en `correr.sh`. |

Se escriben **una vez** y desde ahí son de la app (la IA completa lo marcado con `<!-- La app: … -->` o `# La app:`):

| Archivo | Qué completa la IA de la app |
|---|---|
| `AGENTS.md` | Qué es, sus principios, su mapa, sus secciones propias, qué usa de cada pieza (la tabla «Piezas» ya viene con las instaladas), sus reglas. «Reglas al cambiar cosas», «Lo que rodea a un cambio» y «Revisar aportes» ya vienen. |
| `CONTRIBUTING.md` | Lo que se aporta sin programar en esta app y lo que se revisa en lo propio. El resto (programando con o sin IA, archivos de piezas, «Cómo revisamos», inglés, la línea de los flujos de Pieza) ya viene. |
| `SECURITY.md` | Qué cuenta y cómo se protege lo propio. |
| `CODE_OF_CONDUCT.md` | Una frase: para qué existe la app. |
| `.claude/agents/<id>-revisor.md`, `<id>-privacidad.md` | La lista de lo propio. |
| `.github/ISSUE_TEMPLATE/probar.yml` | 3 a 5 cosas que se prueban en esta app. |
| `.github/pull_request_template.md`, `CLAUDE.md`, `GEMINI.md`, `CHANGELOG.md` («Sin publicar»), `LICENSE` (AGPL-3.0), `.gitignore` (lista blanca con las carpetas de la app) | Nada (o sumar al checklist y a la lista blanca lo propio). |

## `pieza.py repo configurar`
Lo que antes se hacía a mano en cada repo, desde `app.json` → `repo` (y `github.topics`, opcional): Discussions y los topics
(`hecho-con-pieza` y los de la app), reporte privado de fallas (lo usa `SECURITY.md`), `fork-pr-contributor-approval` =
`all_external_contributors`, workflows con permisos de lectura que pueden abrir PRs (lo necesita «Pieza al día»), el ruleset
«Rama principal» (`deletion` + `non_fast_forward`, sin exigir PR; no se crea dos veces) y las etiquetas `good first issue`, `idea`,
`error` y `probar`. Sin `--aplicar` no toca nada.

## Lo que nunca va solo
Lo de `.github/` no se actualiza con el PR automático de «Pieza al día»: el token de Actions no puede escribir workflows y un
workflow nuevo lo tiene que ver una persona. Si una versión nueva lo cambia, llega en el issue con `pieza.py actualizar . github`.

## Revisar a mano (no se puede probar aquí)
- En GitHub: que `revisar.yml` corra en un PR (y el job `mac` solo cuando cambia `app/`), que los formularios de issues se vean, y
  que `pieza.py repo configurar . --aplicar` deje todo (Settings → Rules, Discussions, Security → Private vulnerability reporting).

## Cómo lo adoptan las seis apps
Ya tienen su `.github/` y sus guías: `pieza.py agregar github .` deja como de la app lo que ya existe y es distinto y no reescribe
ningún documento (los de una vez solo se crean si faltan). Con `pieza.py diferencias . github` ven qué cambió; lo que quieran
igualar (p. ej. `revisar.yml` con `app.json` y `acciones.json` en el job `mac`, que les falta a Esquema, Graba, Minuta y Corta) lo
toman con `pieza.py generar . github --forzar`.
