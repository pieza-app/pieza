---
name: "app-escritorio-multiplataforma"
description: "Construir una app de escritorio para Mac, Windows y Linux con una sola interfaz web: ventanas y temas personalizables, puente nativo, empaquetado, instaladores y actualizaciones."
---

# App de escritorio multiplataforma (arquitectura probada en Minuta y Graba)

Versión del flujo: 2

Parte del flujo de Pieza (pieza-app/pieza). **Casi todo lo de esta arquitectura ya es pieza**: una app nueva sale andando de
`python3 herramientas/pieza.py crear <carpeta> --id … --nombre … --plataformas mac,windows,linux [--piezas …]` (interfaz,
host de Mac y de Electron, puente, contrato, bienvenida, actualizaciones, empaquetado, instaladores y workflows). Aquí queda lo que
**no** es pieza todavía y las lecciones; para lo demás, **usa la pieza** (su README dice la API) y no la reescribas. Si hay una
sección «Configuración local» al final, manda sobre lo genérico.

Referencias vivas para lo propio: `minuta-app/minuta` (ventana con forma, barra de menú, coach en vivo) y `graba-app/graba`
(grabar pantalla, burbuja, YouTube). Copia ideas, no datos ni nombres.

Orden de trabajo: 1) la interfaz en el navegador con `ui/demo.json`, 2) Mac, 3) Windows y Linux, 4) publicar. Muestra algo
funcionando a quien mantiene al final de cada paso.

## 1. Lo que ya es pieza (úsala)

| Necesitas… | Pieza | Nota |
|---|---|---|
| Una sola interfaz web, estado `E` + `pintar()`, vista previa con `simular()` | `esqueleto` (lo deja `crear`), `host-ui` | `window.<App>._probar(E => …)` y `_pruebas` para las pruebas; texto de la persona con `esc()` y `data-sin-traducir` |
| Puente `host.enviar(accion, datos)` → `window.<App>.<funcion>(json)` en Mac, Electron y navegador | `host-ui`, `host-mac`, `host-escritorio` | Lo que solo corre un script se **declara** en `app.json` → `acciones`; lo nativo, `p.registrar` y `host.acciones.registrar` (los dos) |
| Que ninguna plataforma se quede atrás | `contrato` | `pruebas/contrato.py`; lo propio y las excepciones con motivo en `pruebas/contrato_app.py` |
| Idiomas (español como clave, `T`, `traducirDOM`, prueba de «nada sin traducir») | `i18n` | En Swift, `Idioma.t()` del host |
| Claro/oscuro con tokens, diálogos, avisos, Tu IA, Acerca de | `tema`, `componentes` | |
| Primer uso con el idioma primero | `bienvenida` | La app nativa no muestra ni pide nada antes de `Idioma.elegido` (el host ya espera) |
| La IA de la persona, segura | `ia` | Nunca armes el comando de una IA en Swift ni en Electron (`contrato` lo revisa) |
| Scripts Python con límite de tiempo, entrada por archivo, sin `<ID>_*` de afuera | `nucleo`, `host-mac`, `host-escritorio` | Trabajos largos con latido: `trabajos` |
| Actualizaciones dentro de la app, solo de los Releases propios, con `.sha256` | `actualizaciones` | |
| Python portátil, `.app`, firma ad hoc por identificador, Electron, NSIS, AppImage, instaladores de un comando, `publicar.yml` | `empaquetado` | Publicar = subir `version` en `app.json` |
| `revisar.yml`, issues, PR, dependabot, guías, privacidad | `github` | `pieza.py repo configurar` |
| Transcribir, catálogo de la comunidad, cifrado, leer documentos, red | `transcribir`, `catalogo`, `cifrado`, `contenido`, `red` | `pieza.py catalogo` dice cuándo |
| Llavero/`safeStorage`, avisos del sistema, carpeta elegida y su vigilante | `host-mac`, `host-escritorio` | `Secretos`, `Notificaciones`, `CarpetaElegida`/`Vigilante` |

## 2. Varias vistas y ventanas propias
- La misma `ui/` puede tener varias vistas: ventana principal, panel de la barra de menú o bandeja (`#panel`), asistente.
- Barra de menú en Mac: `Host.Configuracion(barraDeMenu:abrirAlArrancar:)`; ventana sin barra de título: `barraTransparente`,
  `vidrio`. En Electron, otra ventana con la misma interfaz: `host.ventanas.agregar` (con las mismas guardas).
- `render({ mantenerScroll: true })` para no saltar.

## 3. Ventanas con forma (lo de Minuta; el host aún no lo trae)
**Mac:**
- App de barra de menú (`NSStatusItem`) con panel `WKWebView`; ventana principal `NSWindow` **sin borde y transparente**: la web
  dibuja la forma (esquinas, chaflanes, bordes rasgados) y la sombra sigue los píxeles. La web declara al nativo sus zonas de arrastre,
  exclusiones y bordes de cambio de tamaño; un `WKWebView` propio las atiende antes de pasar el clic a la página.
- Sin menú Edición (app de barra de menú): enruta ⌘C/V/X/A/Z a mano en `performKeyEquivalent`. Pantalla completa quita la forma.
- Alertas flotantes: `NSPanel` que no roba el foco, `acceptsFirstMouse` = true, vista SwiftUI con la paleta del tema, botón principal
  con atajo Enter. Nunca alertas del sistema para cosas propias de la app (actualizaciones, avisos): dentro de la app.
**Windows y Linux (Electron):**
- Ventana sin marco rectangular con la misma UI, bandeja (`Tray`) en vez de barra de menú, `requestSingleInstanceLock`, ventanas
  ocultas para trabajo en segundo plano (p. ej. grabar audio con AudioWorklet).
- Lo específico del sistema (audio del sistema, detectar uso del micrófono, calendario) en módulos separados por plataforma.

## 4. Temas como datos (todo personalizable sin código; la pieza `universos` está por extraer)
- Cada tema es un JSON de **solo datos**: colores (`#hex` o `rgba()` — todos los anfitriones deben entender ambos), radio, fuentes,
  forma de la ventana, íconos, textos (rangos, logros…), `categorias`. Nunca campos que se ejecuten ni HTML sin escapar.
- Validar al cargar y al descargar; texto sobre el acento elegido por contraste WCAG (#fff/#111) y prueba de contraste por tema.
- Incluidos en la app + repo catálogo público (`<proyecto>-catalogo`, con la pieza `catalogo`); los descargados viven en la
  carpeta del usuario y ganan sobre los incluidos. Galería con búsqueda, categorías y "no existe, ¿quieres crearlo?" que lo genera
  con la IA del usuario. Votos = reacciones en un issue por tema; propuestas = issue con etiqueta y el JSON.

## 5. Pruebas que no trae ninguna pieza
- Python con HOME temporal y una IA falsa en el PATH (nunca toca datos reales ni llama a una IA); `pruebas/test_app.py` del esqueleto
  es el molde. Evaluación de la salida de la IA (estructura y marcadores) antes de tocar un prompt.
- Linux de punta a punta con Xvfb (+ PulseAudio virtual si hay audio). Windows no se puede probar aquí: issue `probar` a la comunidad.

## 6. Instalar en el computador de desarrollo
Comprueba que la app no esté trabajando (grabando/procesando), `git pull --ff-only`, build en segundo plano con `nohup` y log
(`FIN $?`), reabrir. Si está ocupada, no compiles: deja la actualización lista en el aviso de la app.

## 7. Lecciones de Graba (grabador de pantalla)
- **Nombres:** antes de pedir que se cree la organización, revisa que `<nombre>-app` esté libre (`gh api users/<n>`).
- **macOS no distingue mayúsculas:** si los datos viven en `~/Nombre`, el checkout de desarrollo no puede ser `~/nombre`: usa
  `~/Developer/<repo>`. La marca de "instalación de desarrollo" va fuera del bundle (escribir dentro rompe la firma).
- **Grabar pantalla en Mac:** ScreenCaptureKit + AVAssetWriter propio (`SCRecordingOutput` con micrófono deja MP4 dañados en macOS 15).
  Ventana: filtro `including:` [ventana + burbuja] con `sourceRect`; área: `sourceRect` en coordenadas de la pantalla (arriba-izquierda).
  Lo que solo ve la persona (barra, teleprompter, marco, cuenta regresiva) se excluye por ID de ventana y `sharingType = .none`.
- **UX de grabación (Dieter Rams):** una sola barra abajo al centro (qué grabar · cámara · micrófono · guion · botón rojo Grabar · ✕).
  Nada empieza solo: sin atajo Enter para grabar; cuenta 3-2-1 grande al centro; la misma barra pasa a "● 00:12 · Terminar · ✕".
  Elegir dispositivo (cámara/micrófono) dentro de su menú. Teleprompter de una pieza: play y A−/A+ siempre visibles.
- **whisper inventa frases en silencio** ("Thank you.", "Gracias", créditos de Amara): fíltralas. Parte con el idioma del sistema en
  vez de "detectar solo" (con poca voz adivina mal).
- **IA con archivos:** copia los adjuntos a la carpeta temporal de la IA (solo lectura) y además extrae texto de pptx/docx con zipfile.
- **Corregir con IA** = reescribir el texto + REEMPLAZOS aplicados a transcripción/subtítulos + vocabulario aprendido (prompt de whisper).
- **YouTube:** OAuth de escritorio con PKCE y redirección a 127.0.0.1, token en el Llavero/safeStorage, subida reanudable + subtítulos.
  Necesita un proyecto de Google Cloud de quien mantiene (cuota de la API limitada por proyecto; sin verificación de Google los videos
  quedan privados): la app muestra "Muy pronto" hasta que exista el cliente y permite usar un cliente propio (avanzado).
- **Windows/Linux:** un agente aparte (o una sesión aparte de tu IA) arma `escritorio/` siguiendo el contrato; avísale cada acción nueva del puente mientras trabaja.
  ffmpeg estático (GPL) va como programa aparte, con huella fija y aviso de licencia en el README.