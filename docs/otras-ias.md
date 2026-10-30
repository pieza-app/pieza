# Pieza con Claude Code, Gemini CLI, Codex u otra IA

Los flujos de Pieza (crear una app, revisar aportes, app de escritorio multiplataforma y diseño y calidad) son **skills**: un `SKILL.md` con `name` y `description`, el mismo
formato en Claude Code, Gemini CLI y Codex. Viven una sola vez en [`skills/`](../skills) y cada herramienta los toma de ahí.

## Instalar

| Herramienta | Cómo | Se actualiza con |
|---|---|---|
| **Claude Code** | `/plugin marketplace add pieza-app/pieza` y `/plugin install pieza@pieza`. En las apps hechas con Pieza, abrir el repo ya lo sugiere (`.claude/settings.json`). | `/plugin marketplace update pieza` |
| **claude.ai** | Descarga los `.zip` desde la [página](https://pieza-app.github.io/pieza/#empezar) y súbelos en las capacidades de tu cuenta. | La skill avisa cuando quedó atrás |
| **Gemini CLI** | `gemini extensions install https://github.com/pieza-app/pieza --auto-update`. Trae las skills (Gemini CLI descubre solo las de `skills/<nombre>/SKILL.md` de una extensión, [ver su guía](https://geminicli.com/docs/extensions/writing-extensions/)) y los comandos `/pieza:crear <idea>` y `/pieza:revisar <repo o PR>`. | Solo (con `--auto-update`) o `gemini extensions update pieza` |
| **Codex** | Dentro del repo de Pieza ya las ve (`.agents/skills`). Para tenerlas en todos lados: clona Pieza y corre `python3 herramientas/pieza.py skills instalar codex` (las deja en `~/.agents/skills`). | `git pull` y el mismo comando (`pieza.py skills estado codex` dice si quedó atrás) |
| **Otra IA** | Clona Pieza y pídele que siga [`AGENTS.md`](../AGENTS.md) y el `SKILL.md` del flujo que quieras. | `git pull` |

`pieza.py skills instalar` conserva tu sección **«Configuración local»** al final de cada skill (lo propio tuyo: tu computador, tu
cuenta, tus páginas), así actualizar nunca la borra. Esa sección no se sube nunca al repo.

## Equivalencias

Cada skill trae esta tabla: el flujo es el mismo y solo cambia la herramienta para cada cosa.

| Para… | Claude Code | Gemini CLI | Codex |
|---|---|---|---|
| Preguntar todo junto | `AskUserQuestion` | un mensaje con preguntas numeradas y opciones, la recomendada marcada | igual que Gemini |
| Lista de tareas | `TaskCreate` / `TaskUpdate` | `write_todos` | `update_plan` |
| Trabajo en paralelo | subagentes | uno a la vez | uno a la vez |
| Conectar un repo | `add_repo` o `gh` | `git` / `gh` | `git` / `gh` |
| Leer páginas web | `WebFetch` | `web_fetch` | su navegación o `curl` |
| Las reglas del repo | `CLAUDE.md` → `AGENTS.md` | `GEMINI.md` → `AGENTS.md` | `AGENTS.md` |

**Lo que no cambia en ninguna:** preguntar antes de publicar, nunca juntar un PR sin aprobación, la regla de oro (lo que escribe
la persona nunca va como argumento de un proceso), la IA de la persona con su cuenta y sin herramientas dentro de las apps, y nada
inventado.

## Dentro de las apps: la IA de la persona

Las apps hechas con Pieza llaman a la IA que la persona ya tiene, con su cuenta, a través de la pieza [`ia`](../piezas/ia):

| IA | Comando que arma la pieza | Cómo le llega el pedido | Protecciones |
|---|---|---|---|
| Claude Code | `claude -p --output-format text --strict-mcp-config --disallowedTools "*"` (+ `--safe-mode` si lo conoce) | entrada estándar | sin MCP, sin herramientas, sin la memoria de la persona (`CLAUDE_CODE_DISABLE_CLAUDE_MDS`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY`) |
| Codex | `codex exec --skip-git-repo-check -s read-only -C <temporal> -o respuesta.txt -` | entrada estándar | solo lectura, en una carpeta temporal vacía |
| Gemini (Antigravity, `agy`) | `agy --output-format text --sandbox --add-dir <temporal> -p "<frase fija>"` | archivo `instrucciones.md` en la carpeta temporal | sandbox; el pedido nunca como argumento |
| Gemini CLI (`gemini`) | `gemini -p "<frase fija>" -o text` | entrada estándar | en una carpeta temporal vacía |

Ninguna recibe las variables de la app (`<ID>_*`). Si un CLI viejo no conoce una protección, la pieza no lo corre y pide
actualizarlo: nunca quita protecciones para que funcione.
