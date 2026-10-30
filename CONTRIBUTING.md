# Cómo aportar a Pieza

Pieza es la base de una familia de apps abiertas que viven en tu computador (Minuta, Graba, Corta, Alcancía, Repasa, Esquema…).
Guarda **piezas**: código probado que se enchufa en cualquier app en vez de escribirlo de cero, y los **flujos** (skills) para crear
una app y revisar aportes. Hay lugar para cualquiera, programes o no. *(English below.)*

## Sin programar
- **Haz una app con Pieza y cuéntanos cómo te fue:** qué pieza te faltó, qué paso del flujo te confundió, qué permiso o qué salida a
  internet no estaba bien contada en la ficha. Ese relato vale oro.
- **Prueba una pieza en tu sistema** (sobre todo Windows y Linux): los issues con la etiqueta
  [`probar`](https://github.com/pieza-app/pieza/labels/probar) piden justo eso. Usa solo datos ficticios.
- **Propón una pieza** que necesitaste en dos apps o más, con el formulario
  [«Proponer una pieza»](https://github.com/pieza-app/pieza/issues/new?template=pieza.yml). Basta con contarla en palabras.
- **Conversa:** dudas, ideas o lo que armaste → [Discussions](https://github.com/pieza-app/pieza/discussions).
- **Cuéntanos qué falla o qué te gustaría** en [issues](https://github.com/pieza-app/pieza/issues/new/choose).
- **Mejora los textos:** las fichas (`descripcion`, `pantallas`, `permisos`) y las traducciones al inglés (`textos` de cada
  `pieza.json`) las lee gente que no programa.

## Programando (con o sin IA)
1. Lee [`AGENTS.md`](AGENTS.md) y [`docs/enchufe.md`](docs/enchufe.md): cómo se hace una pieza, el contrato (`pieza.json`,
   `app.json`, `piezas.json`) y las reglas de seguridad. Sirven igual para personas y para tu IA.
2. Haz un fork, una rama y tu cambio. Pieza no tiene dependencias: basta Python 3 con su biblioteca estándar.
3. Corre `bash pruebas/correr.sh` (lo mismo que revisa GitHub en cada cambio: valida todos los `pieza.json`, corre las pruebas,
   revisa los workflows y la privacidad).
4. Si tu cambio se nota, deja al día lo que lo cuenta: el `pieza.json` (`cambios`, `version`), [`CHANGELOG.md`](CHANGELOG.md),
   [`docs/catalogo.md`](docs/catalogo.md) y el README. Si no sabes bien qué tocar, dilo en el pull request y lo completamos.
5. Abre un pull request contando qué cambia para las apps que usan la pieza y cómo lo probaste.

**Con tu IA.** Aportamos con los flujos de Pieza:
- **Claude Code:** instala el plugin con `/plugin marketplace add pieza-app/pieza` y `/plugin install pieza@pieza`. Trae los flujos
  para crear una app (`lanzar-proyecto-open-source`) y revisar aportes (`revisar-aportes-open-source`); `CLAUDE.md` ya apunta a
  `AGENTS.md`.
- **Gemini CLI:** `gemini extensions install https://github.com/pieza-app/pieza`. `GEMINI.md` también apunta a `AGENTS.md`.
- **Codex:** lee las skills desde `.agents/skills` y las reglas desde `AGENTS.md`.
- **Con cualquier otra IA:** pídele que siga [`AGENTS.md`](AGENTS.md) y, para crear una app, `skills/lanzar-proyecto-open-source/SKILL.md`.

Reglas que importan: código, comentarios y textos en español (de Chile neutro), con su traducción al inglés en `textos`; Python solo
con biblioteca estándar y sin dependencias ni CDN en la interfaz; **lo que escribe la persona nunca va como argumento de un
proceso**; nada personal en el código (ejemplos y pruebas con Ana Pérez, Matías Soto); **nunca subas datos reales**.

Los aportes entran con la licencia del proyecto, [AGPL-3.0](LICENSE).

## Cómo proponer una pieza nueva
Una pieza nace en Pieza cuando **dos apps o más** la van a necesitar; si es solo de una app, va en esa app. Antes de escribirla,
mira [`docs/catalogo.md`](docs/catalogo.md) y `python3 herramientas/pieza.py catalogo`: puede que ya exista o esté «por extraer».

1. **Parte de la mejor versión que ya exista** en las apps y súmale lo que otras resolvieron mejor. Dilo en `origen`.
2. Carpeta `piezas/<id>/` con su código (`python/`, `ui/`, `mac/`, `escritorio/`), un `README.md` corto (qué resuelve, API,
   ejemplo) y su `pieza.json` **completo y honesto** (formato en [`docs/enchufe.md`](docs/enchufe.md)):
   - `descripcion`, `categoria`, `plataformas`, `requiere` y `compatible`.
   - `recomendar` (cuándo sugerirla al crear una app), `pantallas` (lo que suma a la app), `permisos` (por plataforma, con para
     qué) y `red` (cada dominio al que sale; vacío = funciona sin internet; `red_nota` si sale algo de la persona, como su IA).
     **Es lo que el creador de proyectos le muestra a alguien antes de crear su app**: un permiso o un dominio que falte es un error.
   - `tareas_persona`: lo que solo puede hacer una persona (crear una cuenta, verificar un sitio).
   - Cada acción con `limite` (segundos) y `datos` cerrados. **Regla de oro:** un campo de tipo `texto` nunca va en `args`; va en
     el archivo de entrada (`"entrada": "archivo"`). `pieza.py revisar` lo rechaza.
3. **Nada de una app adentro:** ni nombres, ni rutas, ni prefijos. Lo que cambia por app sale de `app.json` (`nucleo.app()`).
4. **Pruebas** en `pruebas/test_piezas.py`, con la app ficticia «Prueba» y datos inventados.
5. **Versión y cambios:** sube `version` (X.Y.Z) si cambia lo que la app recibe y anota en `cambios` (del más nuevo al más viejo)
   `{version, tipo, resumen}` con `tipo` = `arreglo`, `mejora` o `rompe`; un `rompe` trae `migrar` con los pasos, y si arregla
   una falla de seguridad, `seguridad: true`. Es lo que «Pieza al día» le avisa a cada app: escríbelo para quien lo va a leer.
   Súmalo también a `CHANGELOG.md` y mueve la fila en `docs/catalogo.md`.

Si solo tienes la idea, abre el issue [«Proponer una pieza»](https://github.com/pieza-app/pieza/issues/new?template=pieza.yml) y la
armamos juntos.

## Cómo aportar a un flujo (las skills)
Los flujos oficiales viven en `skills/` (`lanzar-proyecto-open-source`, `revisar-aportes-open-source`). Las copias instaladas
comparan su «Versión del flujo» con la de este repo y siguen la más nueva, así que el cambio se hace **aquí**:
1. Edita el `SKILL.md` (un paso nuevo, un error que costó, una mejor forma de hacer algo; los aprendizajes de revisar PRs van en
   su sección «Aprendizajes», con fecha, repo y PR).
2. **Sube «Versión del flujo»** (`pruebas/correr.sh` exige que la línea exista).
3. Anótalo en `CHANGELOG.md`.
Si el cambio es una pieza nueva o un campo nuevo de `pieza.json`, no hace falta tocar la skill: el creador lee las piezas con
`pieza.py catalogo` y `pieza.py ficha`.

## Cómo revisamos
Todo entra por pull request y lo junta alguien que mantiene el proyecto, **solo con su aprobación**: nadie puede subir cambios
directo. Revisamos:
- **Siempre:** que las pruebas de GitHub pasen, que no haya datos personales y que el cambio haga lo que dice. Si es tu primer
  aporte, GitHub espera a que aprobemos correr las pruebas (es normal). Leemos todo el diff antes de correr nada.
- **Seguridad:** las reglas de [`docs/enchufe.md`](docs/enchufe.md#reglas-de-seguridad-las-revisa-piezapy-revisar-y-el-host-al-cargar)
  y que no vuelva ninguna de las brechas que ya encontramos en las apps ([`docs/catalogo.md`](docs/catalogo.md)): el puente solo
  atiende al marco principal y al origen de la app; actualizaciones y catálogo solo con SHA-256; la IA siempre con sus
  protecciones y sin las variables de la app; lo que va a HTML se escapa. Cambios en `.github/workflows/`, en
  `plantillas/pieza-al-dia.yml` o en `herramientas/pieza.py` (que se copia y corre en todas las apps) se miran con lupa.
- **`pieza.json`:** completo y honesto (permisos, red, pantallas), versión y `cambios` al día, `compatible` ajustado si cambia lo
  que otra pieza necesita.
- **Que la documentación diga la verdad:** `CHANGELOG.md`, `docs/catalogo.md`, el README y la ficha cuentan la pieza como queda.
- **Si mejoras algo que tomamos de una app**, lo anotamos como aprendizaje y se lo llevamos a las demás.

Si algo falta te lo pedimos con un comentario; casi nunca cerramos un aporte sin conversar.

¿Buscas por dónde empezar? Mira los issues con la etiqueta
[`good first issue`](https://github.com/pieza-app/pieza/labels/good%20first%20issue) o las piezas «por extraer» de
[`docs/catalogo.md`](docs/catalogo.md), o pregunta en Discussions.

**¿Encontraste una falla de seguridad?** No abras un issue: repórtala en privado como explica [SECURITY.md](SECURITY.md).

Al participar aceptas el [código de conducta](CODE_OF_CONDUCT.md).

---

## Contributing (English)
- **No code needed:** build an app with Pieza and tell us how it went, test a piece on your system (label `probar`, fictional data
  only), propose a piece in words with the [“Propose a piece”](https://github.com/pieza-app/pieza/issues/new?template=pieza.yml)
  form, chat in [Discussions](https://github.com/pieza-app/pieza/discussions), report bugs or ideas, and improve the English texts.
- **Code (with or without AI):** read [`AGENTS.md`](AGENTS.md) and [`docs/enchufe.md`](docs/enchufe.md), fork, branch, run
  `bash pruebas/correr.sh` and open a pull request. Claude Code: `/plugin marketplace add pieza-app/pieza` and
  `/plugin install pieza@pieza`. Gemini CLI: `gemini extensions install https://github.com/pieza-app/pieza`. Codex: skills in
  `.agents/skills`. Any other AI: follow `AGENTS.md`. Code and comments are in Spanish; Python standard library only; whatever a
  person types never goes as a process argument; never commit real data.
- **New pieces:** only when two or more apps need it. A complete and honest `pieza.json` (permissions, network, screens), tests,
  and a bumped `version` with a `cambios` entry (`arreglo`, `mejora` or `rompe` with `migrar` steps; `seguridad: true` if relevant).
- **Flows (skills):** edit `skills/<flow>/SKILL.md` here, bump “Versión del flujo” and note it in `CHANGELOG.md`.
- **Review:** everything goes through a pull request and a maintainer merges it, only with their approval. Contributions are
  licensed under AGPL-3.0.
- **Security issues:** don't open a public issue; report them privately as explained in [SECURITY.md](SECURITY.md).
