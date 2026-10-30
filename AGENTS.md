# Pieza — guía para trabajar en la base

> Para personas y para cualquier IA de programación (Claude Code, Codex, Gemini/Antigravity…). `CLAUDE.md` y `GEMINI.md` solo
> importan este archivo.

Pieza es la base de la familia de apps (Minuta, Graba, Corta, Alcancía, Repasa, Esquema y las que vengan). Guarda **piezas**:
código probado que se enchufa en cualquier app en vez de escribirlo de cero. El objetivo es hacer apps nuevas más rápido y con
menos tokens: elegir piezas, no reescribirlas.

## Antes de escribir algo en una app

1. **Mira `docs/catalogo.md`.** Si la pieza existe, `python3 herramientas/pieza.py agregar <pieza> <app>`. No la reescribas.
2. **Si está «por extraer»**, extráela aquí primero (abajo) y después agrégala a la app. Una vez, para todas.
3. **Si es nueva y la van a necesitar dos apps o más**, nace aquí como pieza. Si es solo de una app, va en la app.

## Cómo se hace una pieza

1. Carpeta `piezas/<id>/` con `pieza.json` (formato en `docs/enchufe.md`), su código (`python/`, `ui/`, `mac/`, `escritorio/`),
   un `README.md` corto (qué resuelve, API, ejemplo) y lo que necesite en `pruebas/test_piezas.py`.
2. **Partir de la mejor versión** que ya exista en las apps y sumarle lo que otras resolvieron mejor. Decir de dónde salió en
   `origen`.
3. **Nada de la app adentro**: ni nombres, ni rutas, ni prefijos. Lo que cambia por app sale de `app.json` (`nucleo.app()`).
4. Correr `bash pruebas/correr.sh` (valida todos los `pieza.json` y corre las pruebas).
5. Subir `version` (X.Y.Z) si cambia lo que la app recibe y anotarlo **en `cambios` del `pieza.json`** (tipo `arreglo`, `mejora` o
   `rompe` con sus pasos en `migrar`; `seguridad: true` si corresponde) y en `CHANGELOG.md`. Si cambia lo que otra pieza
   necesita, ajusta su `compatible`. Esto es lo que «Pieza al día» le avisa a cada app: escríbelo para quien lo va a leer.
6. Actualizar `docs/catalogo.md` (mover la fila de «por extraer» a «listas»).

## Las reglas que no se negocian (heredadas de las apps)

- **Solo biblioteca estándar** en Python; sin dependencias ni CDN en la UI.
- **La IA es la de la persona**, con su cuenta, sin herramientas ni memoria, y el pedido **nunca** como argumento del proceso.
- **Lo que escribe la persona nunca va como argumento** de un proceso: va por archivo de entrada o por la entrada estándar.
- **Todo lo que viene de afuera se valida** (catálogos, traducciones, respuestas de la IA) y se escapa antes de mostrarse.
- **Los datos son de la persona**: en su computador o en su git, nunca en un servidor nuestro.
- **El idioma se pregunta primero** en toda bienvenida.
- **Nada personal en el código**: ejemplos y pruebas con datos ficticios (Ana Pérez, Matías Soto).
- **Liviano**: poco consumo, sin sacrificar que se vea bien.

## Cuando una app mejora una pieza

Las piezas se copian y la app es dueña de su copia. Si en una app se arregla o mejora una pieza:
`pieza.py diferencias <app> <pieza>` muestra el cambio. Si sirve para todas, se trae aquí, se sube la versión y las demás apps
lo reciben con `pieza.py actualizar <app>` (que nunca pisa lo que una app cambió).

## El creador de proyectos (la skill)

`skills/lanzar-proyecto-open-source/SKILL.md` es la versión oficial del flujo para crear una app nueva; las skills instaladas son
copias que, al usarse, comparan su «Versión del flujo» con esta y siguen la más nueva. El creador no tiene piezas escritas
adentro: las lee con `pieza.py catalogo` y `pieza.py ficha`. Por eso:
- **Pieza nueva o campo nuevo** (pantallas, permisos, red, tareas) → aparece solo en el creador. No hay que tocar la skill.
- **Paso nuevo en el flujo** o aprendizaje → editar ese SKILL.md, subir «Versión del flujo» y anotarlo en `CHANGELOG.md`.
- Igual con `skills/revisar-aportes-open-source/`: sus «Aprendizajes» se anotan aquí, no en la copia instalada.

## Mapa

| Ruta | Qué es |
|---|---|
| `piezas/<id>/` | Cada pieza: `pieza.json` + código + README |
| `herramientas/pieza.py` | `listar`, `catalogo`, `ficha`, `iniciar`, `agregar`, `estado`, `actualizar`, `diferencias`, `revisar` |
| `docs/enchufe.md` | El contrato: `pieza.json`, `app.json`, `piezas.json`, reglas de seguridad, host genérico |
| `docs/catalogo.md` | Qué piezas hay, cuáles faltan y en qué orden, y brechas encontradas en las apps |
| `plantillas/pieza-al-dia.yml` | El workflow que `iniciar` agrega a cada app para que se entere de las versiones nuevas |
| `docs/` | La página pública (`index.html`, `pagina.js`, `pagina.css`, `sello.svg`) y los datos que arma `herramientas/pagina.py` |
| `.claude-plugin/` | El plugin de Claude Code (las skills de `skills/`) y su marketplace |
| `skills/` | Los flujos oficiales (las skills), cada uno con su «Versión del flujo»: `lanzar-proyecto-open-source` (crear una app) y `revisar-aportes-open-source` (revisar PRs, con sus aprendizajes) |
| `pruebas/` | `correr.sh` y `test_piezas.py` (una app ficticia con CLIs de IA falsos) |

Licencia AGPL-3.0, como las apps.
