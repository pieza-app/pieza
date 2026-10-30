# Piezas de la comunidad

El catálogo de Pieza crece solo: cualquiera puede publicar una pieza en **su propio repo** y aparece en la
[página](https://pieza-app.github.io/pieza/#catalogo). Lo que aún no se revisa se ve como **«Sin revisar»**; cuando quien
mantiene Pieza la revisa, pasa a **«Revisada ✓»** y desde ahí se instala como segura.

## Publicar una pieza

1. Un repo público con un `pieza.json` en la raíz y el código que nombra en `archivos` (formato en [enchufe.md](enchufe.md)).
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

Si el autor cambia el código después de una revisión, la pieza vuelve a «Sin revisar» (la versión revisada sigue siendo la que
se instala como segura hasta que se revise la nueva). Si cambia algo que no es código ni `pieza.json`, la revisión se mantiene.

## Revisar (quien mantiene Pieza)

Con la skill `revisar-aportes-open-source` (en Claude Code, Gemini CLI o Codex): lee `comunidad/catalogo.json`, baja el commit
de la pieza, revísalo como un PR (fase 2b: regla de oro, permisos y red honestos, brechas conocidas) y deja el veredicto:

```bash
python3 herramientas/comunidad.py revisar <id> aprobar
python3 herramientas/comunidad.py revisar <id> rechazar "por qué"
```

Fija la revisión a ese commit y a la huella de cada archivo. Haz commit de `comunidad/catalogo.json`: la página se actualiza sola.
