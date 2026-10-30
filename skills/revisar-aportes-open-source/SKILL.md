---
name: "revisar-aportes-open-source"
description: "Revisar pull requests y propuestas de la comunidad en los repos open source de David: seguridad, defectos, pruebas, contenido y aprendizajes, con veredicto. Nunca junta sin su aprobación."
---

# Revisar aportes de la comunidad

Versión del flujo: 2

La comunidad hace el trabajo; nosotros verificamos. Revisar debe ser barato: leer el diff, mirar las pruebas y aplicar la lista.
No reescribas el aporte: si falta algo, se pide con un comentario amable. Si el repo tiene `.claude/agents/*revisor*.md` o un
`CONTRIBUTING.md` con "Cómo revisamos", esas reglas mandan sobre esta lista.

David quiere dos cosas **siempre**, en cada revisión: buscar defectos de verdad (no solo "se ve bien") y aprender de cada aporte.
Si alguien hace algo mejor que nosotros, se anota como aprendizaje y se aplica en sus otros proyectos.

## 0. Traer lo último (siempre)
Este flujo vive en **pieza-app/pieza** (`skills/revisar-aportes-open-source/SKILL.md`); esta skill instalada es una copia. Consigue
Pieza al día (`add_repo` pieza-app/pieza, o `~/Pieza` en el Mac con `git pull`). Si la «Versión del flujo» del repo es mayor que la
de esta copia, sigue la del repo, y al cerrar ofrécele a David actualizar la skill instalada con `propose_skills` (improvement,
SKILL.md completo del repo). Los aprendizajes también viven ahí: léelos todos, no solo los de esta copia.

## 1. Encontrar y leer
- `gh pr list -R <org>/<repo>` (y las propuestas: `gh issue list -l propuesta`). Si la sesión no tiene acceso a GitHub, usa `gh` en el
  Mac de David (`/opt/homebrew/bin`, vía osascript). Orgs: minuta-app, graba-app, alcancia-app, corta-app, repasa-app, esquema-app y pieza-app.
- `gh pr view <n> --json files,body,author,statusCheckRollup` y `gh pr diff <n>`. Mira quién es el autor (cuenta nueva vs. con historial).
- Lee también la descripción del PR: lo que la persona probó y lo que le falló (aunque no sea de su cambio) suele revelar defectos nuestros.

## 2. ¿Es seguro? (antes de correr nada)
Lee **todo** el diff. No lo corras ni lo apruebes, y avisa, si trae: cambios en `.github/workflows/`, scripts de build, instalación o
empaquetado, huellas SHA-256 o URLs de descarga; llamadas de red nuevas, `eval`/`exec`, `subprocess` con texto armado, binarios, código
ofuscado, dependencias nuevas, o cualquier lectura de tokens, llaveros o `~/.ssh`.
Si está limpio y GitHub dice "Approve and run": `gh api -X POST repos/<org>/<repo>/actions/runs/<id>/approve` y espera el resultado.
PRs de Dependabot: revisa que solo cambien versiones y lockfile, que el `resolved` sea el registro oficial con `integrity`, que sea
salto menor/parche y lee las notas por avisos de seguridad (GHSA).

## 2b. ¿Toca una pieza? (siempre)
Si el repo tiene `piezas.json`, cruza los archivos del diff con los de cada pieza (`archivos`):
- **El aporte cambia el archivo de una pieza** → es un cambio que podrían querer todas las apps. Revísalo con más cuidado y, si
  sirve, llévalo a Pieza (`pieza.py diferencias <app> <pieza>` muestra todo lo que difiere), sube la versión de la pieza, y las demás
  apps lo reciben con `pieza.py actualizar`. Da crédito a la persona en el commit de Pieza.
- **El aporte reescribe a mano algo que ya es pieza** (otra forma de llamar a la IA, otro catálogo, otro puente) → pide usar la pieza.
- **En Pieza misma** (pieza-app/pieza): `bash pruebas/correr.sh` valida todos los `pieza.json` (la regla de oro: lo que escribe la
  persona nunca va como argumento de un proceso) y corre las pruebas. Una pieza nueva necesita `recomendar`, `pantallas`,
  `permisos` y `red` completos y honestos: son lo que el creador de proyectos le muestra a David.
Revisa también estas brechas que ya aparecieron en las apps (un aporte no puede traerlas de vuelta): el puente acepta mensajes solo
del marco principal y del origen de la app; las actualizaciones solo bajan de los Releases del propio repo, con sha256; lo del
catálogo exige sha256; la IA nunca corre sin sus protecciones (ni «reintento sin protecciones» para CLIs viejos), sin las variables
de la app y nunca con el pedido como argumento; los valores que van a HTML se escapan.

## 3. Buscar defectos (siempre)
Además de que "funcione", busca activamente:
- **Casos borde:** teclado/foco (inputs, contentEditable, modificadores), estados de la app (grabando, procesando, vacío), listas más
  largas o más cortas de lo esperado, idiomas, ancho de celular.
- **Pruebas que faltan:** si el aporte agrega un comportamiento y no una prueba que lo cubra, la agregamos nosotros (o se la pedimos
  con cariño). Un cambio sin prueba es un defecto.
- **Consistencia:** mismos textos traducidos, misma lógica en Python y JS cuando el repo lo exige, ortografía en comentarios y textos.
- **Plataformas:** Windows (codificación: abrir y leer siempre con `encoding="utf-8"`, también la salida de `subprocess`), Linux, Mac.
- **Defectos nuestros que el aporte destapa:** arréglalos aparte, dando crédito en el commit.
Verifica de verdad: corre las pruebas del repo (Playwright está en la nube, no en el Mac) antes de decir que algo está bien.

## 4. Revisar según el tipo
- **Código:** pruebas en verde; respeta el formato de datos documentado; textos nuevos traducidos; sin dependencias nuevas sin conversarlo;
  datos de ejemplo ficticios; privacidad (`revisar_privacidad.sh --generico` si existe).
- **Contenido (universos, temas, plantillas):** solo datos válidos (corre el validador del repo), sin HTML ni scripts, sin textos copiados
  (letras, guiones), nada personal ni de empresas reales, tono amable, colores legibles.
- **Traducciones:** mismas claves que la referencia, mismos marcadores (`{n}`, `{x}`), marcas sin traducir, muestra de 15–20 textos
  revisada; pide revisión de una persona nativa antes de juntar.

## 5. Aprender del aporte (siempre)
Pregúntate: ¿qué hizo esta persona mejor que nosotros? (cómo estructuró el código, cómo probó, cómo explicó el PR, algo que vio y
nosotros no). Si hay algo, anótalo en «Aprendizajes» **de la copia en pieza-app/pieza** (fecha, repo y PR; sube «Versión del flujo») y dile a
David qué es y dónde más conviene aplicarlo. Si el aprendizaje es código, el lugar es una pieza: así llega solo a todas las apps.

## 6. Veredicto para David (pocas líneas)
Qué cambia, si es seguro, defectos encontrados (del aporte y nuestros), cómo salieron las pruebas, qué aprendimos y la recomendación:
**juntar**, **pedir cambios** (con el comentario sugerido, cálido y concreto) o **cerrar** (con el motivo). Explícalo sin jerga.

## 7. Solo cuando David diga que sí
`gh pr review <n> --approve -b "<agradecimiento específico, en el idioma de la persona>"`, `gh pr merge <n> --squash`, cierra el issue que
resuelve dando crédito (`Resuelto en #n por @autor`), y para contenido nuevo crea lo que el repo pida (p. ej. issue de votos).
Sincroniza el clon local (`git pull --rebase`) e instala la app si cambió (respetando que Minuta no se reinstala grabando).
Agradece siempre: quien se siente bien recibido vuelve.

## Aprendizajes
- **2026-10-27 · minuta #17 (@charliechinhay, primer colaborador):**
  - Un solo camino para el clic y el teclado (`elegirTipoPanel`): menos código duplicado y el mismo comportamiento con mouse o teclas.
    Aplicarlo en los otros proyectos cuando un mismo gesto tenga varias entradas.
  - Mostrar el atajo en el propio menú (`<kbd>1</kbd>`) hace que se descubra solo, sin texto de ayuda extra.
  - Ignorar atajos dentro de `input/textarea/select/contentEditable` y con ⌘/Ctrl/Alt.
  - Su PR contaba qué probó y qué le falló en Windows: eso destapó que nuestras pruebas leían la salida de los scripts sin UTF-8
    (Matías → MatÃas). Arreglado en ec5b5a1; revisar lo mismo en Graba, Alcancía, Corta y Repasa.
  - Defecto que no traía: prueba de interfaz de las teclas 1–9. La agregamos nosotros (ec5b5a1).