# Piezas de la comunidad

El catálogo de Pieza crece solo: cualquiera puede publicar una pieza en **su propio repo** y aparece en la
[página](https://pieza-app.github.io/pieza/#catalogo). Lo que aún no se revisa se ve como **«Sin revisar»**; cuando quien
mantiene Pieza la revisa, pasa a **«Revisada ✓»** y desde ahí se instala como segura.

## Publicar una pieza

1. Un repo público con un `pieza.json` en la raíz, su **`icono.svg`** y el código que nombra en `archivos` (formato en
   [enchufe.md](enchufe.md)). El ícono es obligatorio: 24×24, de línea, en `currentColor`, solo formas ([reglas del
   ícono](enchufe.md#el-ícono-toda-pieza-oficial-o-de-la-comunidad)); si no pasa la validación, la pieza no entra.
   Dice su `licencia` (MPL-2.0, como las oficiales, o MIT, Apache-2.0, BSD, LGPL, GPL o AGPL): la ve quien la instala.
   Mismas reglas que una pieza oficial: `estado: "lista"`, `recomendar`, `pantallas`, `permisos` y `red` honestos, `cambios`
   desde la primera versión y la **regla de oro** (lo que escribe la persona nunca va como argumento de un proceso).
2. Puede requerir piezas oficiales (por ejemplo `nucleo` o `ia`), no otras de la comunidad, y su `id` no puede ser el de una
   oficial ni el de otra pieza de la comunidad.
3. Ponle el topic **`pieza-comunidad`** al repo. Una vez al día el workflow `comunidad` la encuentra, la valida y la suma como
   «Sin revisar». Si algo no pasa, no entra (y si ya estaba, queda la versión anterior).
4. Para pedir la revisión, abre una conversación en [Discussions](https://github.com/pieza-app/pieza/discussions).

Antes de publicar, pruébala con tu copia de Pieza: `python3 herramientas/pieza.py revisar` valida las oficiales; para la tuya,
cópiala a `piezas/<id>/` en tu fork y corre lo mismo.

## Qué significa cada estado

| Estado | Qué quiere decir | Instalar |
|---|---|---|
| **Revisada ✓** | Alguien de Pieza leyó todo el código de ese commit con la skill de revisar aportes. | `pieza.py agregar <id> <app>`: se baja **ese** commit y cada archivo se compara con su huella. |
| **Sin revisar** | Pasó la validación automática, pero nadie leyó el código todavía. | Solo con `--sin-revisar`, bajo tu responsabilidad. |
| **Rechazada** | Se revisó y no es segura. No se muestra. | Nunca. |

Si el autor cambia el código después de una revisión, lo nuevo queda «Sin revisar» y `pieza.py agregar` sigue instalando la
**última versión revisada** (verificada con sus huellas) hasta que se revise la nueva. Lo mismo si cambia el ícono. Un rechazo es
del repo: sigue rechazado aunque cambie, hasta que alguien lo apruebe. Si la búsqueda de GitHub viene incompleta o cae de golpe, no
se quita nada (un error de GitHub no borra revisiones). Si cambia algo que no es código,
`pieza.json` ni el ícono, la revisión se mantiene.

## Revisar (quien mantiene Pieza)

Con la skill `revisar-aportes-open-source` (en Claude Code, Gemini CLI o Codex): lee `comunidad/catalogo.json`, baja el commit
de la pieza, revísalo como un PR (fase 2b: regla de oro, permisos y red honestos, brechas conocidas) y deja el veredicto:

```bash
python3 herramientas/comunidad.py revisar <id> aprobar <commit que leíste>
python3 herramientas/comunidad.py revisar <id> rechazar <commit> "por qué"
```

Fija la revisión a ese commit y a la huella de cada archivo. Haz commit de `comunidad/catalogo.json`: la página se actualiza sola.

## Tu app en la página («Hecho con Pieza»)

Si hiciste una app con Pieza, aparece sola en la [página](https://pieza-app.github.io/pieza/#proyectos), con su ícono:

1. Ponle el topic **`hecho-con-pieza`** al repo (público).
2. Su ícono: el que diga `"icono"` en su `app.json` o, si no, `docs/favicon.svg`, `favicon.svg` o `ui/favicon.svg`. Puede tener
   sus colores, pero solo formas y hasta 8 KB (las mismas reglas de seguridad que el ícono de una pieza). Sin uno válido se
   muestra una pieza genérica.
3. Una vez al día el workflow `comunidad` la encuentra (`comunidad/proyectos.json`) y la página la muestra como **«Sin
   revisar»**. Cuando quien mantiene Pieza la mira, pasa a **«Aprobada por la comunidad ✓»**.

Aprobar un proyecto dice que **es una app hecha con Pieza, que cumple el manifiesto y que no engaña** (no es una revisión
línea por línea de todo su código, como la de una pieza). Se aprueba el proyecto, no un commit; pero si cambia su nombre o el
enlace a su página, vuelve a «Sin revisar» (y la página solo enlaza el sitio de los aprobados). Uno rechazado no aparece.

```bash
python3 herramientas/comunidad.py proyecto <dueño/repo> aprobar
python3 herramientas/comunidad.py proyecto <dueño/repo> rechazar "por qué"
```
