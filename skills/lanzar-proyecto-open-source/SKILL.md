---
name: "lanzar-proyecto-open-source"
description: "Lanzar un proyecto open source completo desde una idea: entrevista con piezas recomendadas de Pieza, ficha con pantallas, configuración, permisos y red, repos, app, página con SEO, CI, comunidad y anuncio."
---

# Lanzar un proyecto open source (playbook de David)

Versión del flujo: 2

David dice "creemos una aplicación para…" y espera el paquete completo, no preguntas una por una. Este playbook sale de lanzar
Minuta (minuta-app) y las apps hermanas. Trabaja por fases, con lista de tareas visible, y entrega algo usable al final de cada fase.
**Nada se escribe de cero si ya existe como pieza en Pieza** (pieza-app/pieza): se elige, se enchufa y se mejora ahí.

## 0. Traer lo último (siempre, antes de preguntar nada)
Este flujo y el catálogo de piezas viven en el repo **pieza-app/pieza**; esta skill instalada es solo una copia.
1. Consigue Pieza al día: `add_repo` pieza-app/pieza (lectura basta) y clónalo; si no se puede, `~/Pieza` en el Mac de David
   (`git pull`).
2. Lee `skills/lanzar-proyecto-open-source/SKILL.md` del repo. Si su «Versión del flujo» es mayor que la de esta copia, **sigue la
   del repo** desde aquí, y al cerrar ofrécele a David actualizar la skill instalada con `propose_skills` (kind `improvement`,
   target `lanzar-proyecto-open-source`, el SKILL.md completo del repo).
3. `python3 herramientas/pieza.py catalogo --json`: todas las piezas, listas y planeadas, con cuándo recomendarlas, pantallas,
   permisos, red y tareas. **Nunca uses una lista de piezas de memoria**: el catálogo cambia.

## 1. Entrevista (una sola ronda, con recomendaciones)
Con AskUserQuestion, todo junto (si no responde, usa los valores por defecto y dilo):
- Nombre (termina en «a», org `<nombre>-app`) y una frase de qué hace y para quién.
- Plataformas: Mac, Windows, Linux, iPhone, Android (por defecto las tres de escritorio; móvil después).
- Idiomas (por defecto español de Chile neutro + inglés). Licencia (por defecto **AGPL-3.0**, como las apps hermanas).
- Qué NO se negocia (privacidad, gratis, datos del usuario, etc.).
- **Qué piezas sumar.** Con la frase de David, elige del catálogo las que calzan (`recomendar.cuando` y `recomendar.palabras`) y
  pregúntalas en una o dos preguntas `multiSelect` agrupadas por categoría, la recomendada primero con «(Recomendada)» y en la
  descripción una línea de por qué. Las de `siempre` no se preguntan: se avisa que van. Las `planeadas` se pueden elegir: se dice
  que hay que extraerlas primero (de dónde, `tomar_de`) y que el proyecto lo hará.

## 2. Ficha del proyecto (mostrarla y confirmar antes de crear nada)
`python3 herramientas/pieza.py ficha <piezas elegidas> --plataformas <elegidas>` y arma con eso la ficha completa, en un doc que
David guarde (y después en `docs/ficha.md` del repo):
- **Qué es**: nombre, frase, para quién, plataformas, idiomas, licencia, lo que no se negocia.
- **Piezas**: listas, por extraer (y de dónde), y las que van siempre. Lo que no exista y vayan a necesitar dos apps o más, se
  propone como pieza nueva.
- **Pantallas**: las de las piezas (la ficha las ordena: Bienvenida con el idioma primero, la app, Ajustes, web) **más las propias
  de la app** que salen de la idea de David (propónlas tú: pantalla principal, flujo central, vacíos). Para cada una, qué hace.
- **Páginas y repos**: `<org>/<app>` (app), `<org>/<app>-catalogo` si hay catálogo, `<org>/.github` (portada de la org),
  `<org>/<org>.github.io` (raíz y `robots.txt`), página pública bilingüe con demo, Discussions.
- **Configuración** (`app.json`): cada clave y sus valores.
- **Permisos por plataforma**: la clave exacta (Info.plist, Android) o el aviso del sistema, y la frase de para qué que verá la persona.
- **Red**: a qué dominios sale y por qué; si no sale a ninguno, decirlo: «funciona sin internet».
- **Acciones** que trae el enchufe y las que hay que escribir para la app.
- **Lo que solo hace David** (de la ficha + lo de la fase 3).
- **Plataformas donde una pieza no está** (`faltan_en`) y qué se hace ahí.
David confirma o ajusta; recién ahí crea la lista de tareas con las fases de abajo.

## 3. Lo que solo puede hacer David (pídeselo al inicio, en un solo mensaje)
- Crear la organización en GitHub (no hay API para eso): github.com/account/organizations/new, plan Free.
- Lo de `tareas_david` de la ficha (repo de catálogo, cuentas de desarrollador, proyecto de Google Cloud…).
- Más adelante: verificar Google Search Console (fase 9) y pagar firmas de código si las quiere (Apple Developer USD 99/año).
Nunca ingreses contraseñas ni códigos de verificación: eso lo hace él.

## 4. Cómo trabajar con GitHub desde esta sesión
- Primero intenta `add_repo` con `access: "push"` para cada repo.
- Si la sesión no puede empujar, usa el Mac de David (bridge `mcp__remote-devices__*`): `gh` está en `/opt/homebrew/bin` con sesión
  `soydavidcornejo` (scopes repo, workflow, read:org — **sin admin:org**). Flujo: commit local → `git bundle create X.bundle origin/main..main`
  → `device_commit_files` a una carpeta conectada → en el Mac `git fetch X.bundle main:refs/tmp && git push origin refs/tmp:refs/heads/main`,
  borrar ref y bundle. Comandos osascript de ≤25 s; lo largo con `nohup` y un log que se consulta por tramos.
- Autor de commits: `soydavidcornejo <soydavidcornejo@users.noreply.github.com>` (nunca su correo personal) + las líneas de atribución
  que pida la sesión. Si un hook pide cambiar el autor de commits ya publicados, no reescribas historia pública: explícalo.
- Lo que `gh` no puede (avatar y nombre visible de la org, social preview, renombrar/fijar Discussions, fijar repos): navegador
  integrado, que tiene la sesión de GitHub. Para subir imágenes: `fetch` desde `raw.githubusercontent.com` (permitido por la CSP de
  github.com; github.io no) → `new File` → `DataTransfer` → `input.files` + evento `change`. Formularios: leer el form con DOMParser y
  enviarlo con `fetch` + `FormData`.

## 5. Repos y estructura
- Los repos de la ficha (fase 2).
- **Una sola guía para personas e IAs:** `AGENTS.md` (principios que no se negocian, mapa del repo, cómo se conectan las piezas,
  reglas, pruebas, despliegue, privacidad). `CLAUDE.md` y `GEMINI.md` solo contienen `@AGENTS.md`. Agentes por área en `.claude/agents/`
  (incluye siempre uno de privacidad y uno revisor de aportes).
- `app.json` en la raíz (lo crea `pieza.py iniciar`) y `piezas.json` (lo escribe `pieza.py`): se versionan.
- `.gitignore` como lista blanca si la carpeta del repo también guarda datos del usuario.
- Código, comentarios, commits y textos en español; inglés con archivo de traducciones y prueba que exija traducir todo texto nuevo.

## 6. Construir la app (con piezas)
1. **Piezas planeadas que eligió David: extráelas primero en Pieza** (su `AGENTS.md`: partir de la mejor versión, `tomar_de`,
   pruebas, `estado: lista`, subir versión), y publícalas en pieza-app/pieza. Una vez, para todas las apps.
2. `pieza.py iniciar <app> <id> <Nombre>` y `pieza.py agregar <pieza> <app>` por cada pieza. Revisa `pieza.py estado <app>`.
3. Lo propio de la app: si es de escritorio (o web + escritorio), sigue la skill **app-escritorio-multiplataforma** (una sola
   interfaz web, app nativa en Mac y Electron en Windows/Linux, ventanas y temas, empaquetado e instaladores). Para web o móvil,
   las mismas ideas: interfaz única, datos del usuario en formato abierto, temas como datos y contrato probado.
4. Acciones de la app: si son «correr un script y devolver JSON», se declaran en el enchufe (`docs/enchufe.md` de Pieza), no se
   escriben tres veces.
Construye primero lo mínimo que funcione de punta a punta en una plataforma, muéstraselo a David y después amplía.
En todo el diseño y la construcción aplica la skill **diseno-y-calidad-de-producto** (criterios UX/UI y buenas prácticas).

## 7. Calidad automática desde el día uno
- `pruebas/correr.sh` + workflow `revisar.yml` en `push` a main **y** `pull_request`: sintaxis, privacidad, pruebas de lógica, contrato
  entre interfaz y apps (si hay varias), pruebas de interfaz con Playwright en todos los idiomas y capturas como artefacto.
- Privacidad: `herramientas/revisar_privacidad.sh` que busca términos de un archivo local **nunca versionado** (`.terminos-privados`:
  nombres, empresas, correos y rutas reales) + correos y rutas `/Users/…`. Córrelo antes de cada commit. Ejemplos solo con datos
  ficticios (Ana Pérez, Matías Soto…). El repo es público: cada commit se ve al tiro.
- Seguridad que ya costó aprender (las piezas lo traen; si escribes algo a mano, cúmplelo): el puente solo acepta mensajes del marco
  principal y del origen de la app; las actualizaciones solo bajan de los Releases del propio repo y verifican sha256; lo del
  catálogo exige sha256; la IA nunca se corre sin sus protecciones ni con el pedido como argumento; todo proceso tiene límite de tiempo.
- Contraste: el texto sobre colores de acento se elige por WCAG (#fff o #111), con prueba.
- Versiones: `publicar.yml` que al subir el número de versión compila todas las plataformas y crea el Release con nombres de archivo
  fijos + `.sha256`. Instaladores de un comando (`curl … | bash`, `irm … | iex`) que verifican la huella. Avisos de actualización
  **dentro de la app** con barra de progreso y "Estás en la última versión"; nunca alertas del sistema.

## 8. Identidad visual
- Logo simple en SVG (favicon), PNG 512×512 para la org (fondo lleno, la figura dentro del círculo), `apple-touch-icon.png` 180×180.
- Imagen para compartir 1200×630 (`docs/img/compartir.png`) con nombre, frase y captura con datos ficticios.
- Org: avatar, nombre visible, descripción, URL, portada (`.github/profile/README.md` centrado con logo, frase y enlaces: Descargar ·
  Código · Comunidad · Cómo aportar), repos fijados y ocultar "tareas sugeridas". Social preview en cada repo.
- Temas o colores definidos por el usuario: acepta `#hex` y `rgba()` en todas las plataformas (un parser que solo entendía `#` dejó
  botones negros en Minuta).

## 9. Página pública (GitHub Pages en `docs/`)
- Bilingüe con detección del sistema operativo del visitante y botón de descarga correcto; sección "cómo funciona" animada;
  tabla comparativa honesta; preguntas frecuentes (incluye "¿por qué mi computador dice que no puede verificar la app?" si no está
  firmada: macOS 15 → Ajustes del Sistema → Privacidad y seguridad → "Abrir igualmente"; Windows → "Más información" → "Ejecutar de
  todas formas"); sección comunidad. Si depende de herramientas de terceros, una guía paso a paso aparte.
- Lista honesta de **qué permisos pide y por qué** y **a qué sale a internet**, sacada de la ficha.
- SEO: `<title>` con palabras que la gente busca, description, canonical, Open Graph/Twitter con la imagen, JSON-LD
  (SoftwareApplication + FAQPage), `sitemap.xml`, `robots.txt` en la raíz del dominio (repo `<org>.github.io`), topics del repo.
- Search Console: propiedad "Prefijo de la URL"; David descarga el archivo `google….html` y tú lo subes a `docs/`. Sitemap: "No se ha
  podido obtener" recién enviado es normal; sugiere "Inspeccionar URL → Solicitar indexación".
- Nada inventado: sin testimonios, cifras de usuarios ni estrellas falsas.
- Cuando la app esté operativa (prototipo o MVP OK), súmala a la página personal de David (soydavidcornejo.github.io).

## 10. Comunidad
- Discussions activado, categorías en español (Novedades, General, Ideas, Encuestas, Preguntas y ayuda, Muestra lo que armaste);
  al renombrar cambia el slug → actualiza los links. Publicación de bienvenida fijada + 1–2 conversaciones para romper el hielo.
- `CONTRIBUTING.md` (sin programar / programando con o sin IA / **Cómo revisamos**), `CODE_OF_CONDUCT.md`, plantillas de issue
  (error, idea) y de PR con checklist, etiquetas (`good first issue`, `idea`, `error`, `probar`…).
- 6–10 tareas de bienvenida bien especificadas (qué hacer, archivos, cómo probar, "comenta si lo tomas"), la mitad sin programar
  (probar en una plataforma real, crear contenido, traducir).
- Si la app tiene feedback interno: issues desde la app con la cuenta de GitHub del usuario si la conectó, si no abre GitHub prellenado.
  **Nunca obligatorio ni sugerido**: solo cuando la persona lo pide.
- Formato de datos abierto y documentado + carpeta `ejemplos/` con scripts para que la gente construya encima.

## 11. Seguridad del repo
- Nadie de afuera puede juntar: todo entra por PR y lo junta quien mantiene, **solo con aprobación de David**.
- `PUT repos/<org>/<repo>/actions/permissions/fork-pr-contributor-approval` con `approval_policy=all_external_contributors`.
- Ruleset en la rama por defecto: `deletion` + `non_fast_forward` (sin exigir PR, para que David pueda empujar directo).

## 12. Anuncio
Redacta textos para pegar (LinkedIn en español, Reddit y Show HN en inglés), con licencia real y sin cifras inventadas. Recomienda
que alguien pruebe cada plataforma en uso real antes de anunciar.

## Cierre de cada fase
Verifica (pruebas en verde, página en vivo con `curl` desde el Mac, capturas a ojo), comprueba que el Mac esté libre antes de
instalar algo que cierre una app, borra temporales y capturas, y cuenta en pocas líneas qué quedó y qué falta que haga David.

## Al terminar: que el flujo aprenda (así esta skill escala sola)
- Código que sirvió y lo usarán dos apps o más → **pieza nueva en Pieza** (o mejora de una, con `pieza.py diferencias`).
- Un paso nuevo, un error que costó o una mejor forma de hacer algo → edita **este archivo en pieza-app/pieza**
  (`skills/lanzar-proyecto-open-source/SKILL.md`), sube «Versión del flujo» y anótalo en el `CHANGELOG.md` de Pieza.
- Ofrécele a David actualizar la skill instalada con `propose_skills` (improvement, SKILL.md completo). La próxima vez, la fase 0
  detecta igual si la copia instalada quedó atrás.
