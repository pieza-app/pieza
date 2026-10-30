# Seguridad

Pieza es código que se copia dentro de muchas apps: una falla aquí puede terminar en todas. Si encuentras una, gracias por avisar:
la arreglamos antes de contarla. *(English below.)*

## Cómo reportar una falla (en privado)
**No abras un issue público ni lo cuentes en Discussions.** Usa el reporte privado de GitHub:
[**Reportar una vulnerabilidad**](https://github.com/pieza-app/pieza/security/advisories/new) (pestaña *Security* → *Report a
vulnerability*). Solo lo ven quienes mantienen el proyecto.

Cuéntanos qué pasa, cómo repetirlo (pasos y un ejemplo **con datos ficticios**), qué versión de la pieza o qué commit usas y en qué
sistema. Si la falla está en una app de la familia y no en Pieza, repórtala en el repo de esa app; si no sabes dónde está, aquí.

Qué puedes esperar:
- Respuesta en **7 días** como máximo, diciendo si lo pudimos repetir.
- Mientras lo arreglamos te contamos cómo va. Cuando salga el arreglo publicamos un aviso (GitHub Security Advisory), la pieza sube
  su versión con `seguridad: true` en `cambios` (así «Pieza al día» lo marca en el PR o el issue de cada app) y, si quieres, te
  damos el crédito.
- Pedimos no publicar detalles hasta que el arreglo esté disponible (como regla general, 90 días como máximo).

## Qué cuenta
- **`herramientas/pieza.py`:** que `agregar`, `actualizar`, `iniciar` o `diferencias` escriban fuera de la app elegida, pisen un
  archivo que la app cambió, sigan enlaces que salgan de la app, o que un `pieza.json` malicioso logre ejecutar algo o colar
  archivos fuera de su lugar. Que `revisar` deje pasar algo que las reglas prohíben (abajo).
- **Las piezas:** que lo que escribe la persona llegue como argumento de un proceso; que la IA corra sin sus protecciones, con
  herramientas, con las variables de la app o con más de lo que se le pide; que algo de afuera (catálogo, traducciones,
  respuestas de la IA) se use sin validar o se muestre sin escapar; descargas sin SHA-256 o desde otro lugar que el propio;
  procesos sin límite de tiempo; datos que salgan del computador sin que la persona lo pida.
- **Las plantillas** (`plantillas/`) y el workflow **«Pieza al día»** (`plantillas/pieza-al-dia.yml`, que `pieza.py iniciar`
  copia en cada app): que permitan colar código en una app, usar su token para algo más que abrir el PR y el issue, o correr
  código de un pull request de afuera.
- **Este repo:** workflows de GitHub (`.github/workflows/`), la página pública (`docs/`, `herramientas/pagina.py`) y el plugin y
  las skills (`.claude-plugin/`, `skills/`) si permiten colar código o instrucciones.

No cuentan: fallas de tu IA (Claude Code, Codex, Gemini; repórtalas a ellos, salvo que una pieza las exponga de más); ataques que
ya necesitan control total del computador; o encabezados que GitHub Pages no deja configurar en la página pública.

## Las reglas que protegen a todas las apps
Están en [`docs/enchufe.md`](docs/enchufe.md#reglas-de-seguridad-las-revisa-piezapy-revisar-y-el-host-al-cargar) y
`pieza.py revisar` las comprueba en cada `pieza.json` (y `pruebas/correr.sh` en cada cambio):
1. **Lo que escribe la persona nunca va como argumento** del proceso: va en el archivo de entrada. Un `$campo` de tipo `texto` en
   `args` se rechaza.
2. **Rutas absolutas, secretos y la carpeta actual nunca vienen de la interfaz:** solo por `inyectar` o por una capacidad. Los
   secretos van por la entrada estándar.
3. **El script tiene que existir en `bin/`** y llamarse `^\w+\.py$`.
4. **El entorno del script** no hereda nada raro; el de la IA, además, sin las variables `<ID>_*` de la app.
5. **Todo tiene límite de tiempo** (`limite` es obligatorio en cada acción).

Además, las brechas que ya encontramos en las apps ([`docs/catalogo.md`](docs/catalogo.md)) no pueden volver: el puente solo
atiende al marco principal y al origen de la app; actualizaciones solo de los Releases del propio repo, con SHA-256; lo del
catálogo exige SHA-256; la IA nunca se reintenta sin sus protecciones; los valores que van a HTML se escapan.

## Cómo nos protegemos
- Todo entra por pull request y lo junta quien mantiene el proyecto, después de leer el diff completo ([CONTRIBUTING.md](CONTRIBUTING.md)).
- Sin dependencias: Python con su biblioteca estándar; sin npm ni CDN en las piezas de interfaz.
- Las piezas se **copian** dentro de cada app y `piezas.json` guarda la huella SHA-256 de cada archivo: `pieza.py actualizar`
  nunca pisa lo que la app cambió, y lo que rompe nunca se actualiza solo (trae los pasos en `migrar`).
- Las GitHub Actions (aquí y en «Pieza al día») están fijadas por SHA con su versión en un comentario, con permisos mínimos,
  `persist-credentials: false` (salvo el checkout de la app en «Pieza al día», que necesita empujar su rama y lo dice en un
  comentario), sin `pull_request_target` y sin expresiones de GitHub dentro de `run:`. Dependabot propone actualizaciones con
  unos días de espera (`.github/dependabot.yml`) y `pruebas/correr.sh` revisa que todo siga fijado.
- `herramientas/revisar_privacidad.sh` corre en cada cambio: nada de correos personales, rutas de usuario ni datos reales.

---

## Security policy (English)
Pieza is code that gets copied into many apps, so a flaw here can end up in all of them. **Please don't open a public issue.**
Report vulnerabilities privately through GitHub: [**Report a vulnerability**](https://github.com/pieza-app/pieza/security/advisories/new).
Include what happens, how to reproduce it (with **fictional data only**), the piece version or commit and your OS. We reply within
**7 days**, keep you posted, publish a GitHub Security Advisory with the fix (the piece gets a new version marked `seguridad: true`,
which “Pieza al día” flags in every app) and credit you if you want. Please don't disclose details until a fix is out (90 days at most).

In scope: `herramientas/pieza.py` writing outside the target app, overwriting files the app changed or being abused by a malicious
`pieza.json`; pieces that pass user text as process arguments, run the AI without its protections, skip validation, escaping,
SHA-256 checks or time limits, or send data out without the person asking; the templates and the “Pieza al día” workflow; this
repo's workflows, page, plugin and skills. Out of scope: bugs in your own AI CLI, attacks that already require full control of the
device, and headers GitHub Pages can't set. The rules every piece must follow are in [`docs/enchufe.md`](docs/enchufe.md).
