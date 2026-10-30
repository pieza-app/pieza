---
name: "app-escritorio-multiplataforma"
description: "Construir una app de escritorio para Mac, Windows y Linux con una sola interfaz web: ventanas y temas personalizables, puente nativo, empaquetado, instaladores y actualizaciones."
---

# App de escritorio multiplataforma (arquitectura probada en Minuta y Graba)

Versión del flujo: 1

Parte del flujo de Pieza (pieza-app/pieza): antes de escribir algo de esta lista, mira si ya es una pieza
(`python3 herramientas/pieza.py catalogo`) y enchúfala en vez de reescribirla. Si hay una sección «Configuración local» al final,
manda sobre lo genérico.

Referencias vivas: repos `minuta-app/minuta` y `graba-app/graba` (clónalos si necesitas ver código real: `ui/app.js`, `app/Sources/Minuta/VisorWeb.swift`,
`app/Sources/Graba/` (Barra, Grabadora, Flotantes, Actualizaciones), `escritorio/src/main.js`, `herramientas/empaquetar.sh`, `.github/workflows/`). Copia ideas, no datos ni nombres.

Orden de trabajo: 1) interfaz web con datos de demo en el navegador, 2) Mac nativo, 3) Electron para Windows/Linux, 4) empaquetado,
instaladores y actualizaciones. Muestra algo funcionando a quien mantiene al final de cada paso.

## 1. Una sola interfaz web (`ui/`)
- HTML + CSS + JS sin framework ni build (`app.js` con un estado `E` y `render()`), igual en todas las plataformas. Se sirve desde
  archivos locales; en Electron con un protocolo propio (`app://ui/…`) para que `fetch` relativo funcione igual que en Mac.
- `demo.json` con datos ficticios: la interfaz corre en el navegador (`python3 -m http.server`) con `E.plataforma === "web"` simulando
  al anfitrión. Así se diseña, se prueba con Playwright y se sacan capturas para la página sin compilar nada.
- La app nativa inyecta `window.<APP>_HOST = "mac" | "windows" | "linux"` y clases en `<html>`; la interfaz se adapta (p. ej. ventana
  con forma solo en Mac, textos sin "Mac" en los otros).
- Hook de pruebas: `window.<App>._probar(E => {…})` para saltar a cualquier vista y `_pruebas` con funciones puras.
- Varias vistas de la misma UI: ventana principal, panel compacto de la barra de menú/bandeja (`#panel`), asistente de bienvenida.
- `render({ mantenerScroll: true })` para no saltar; texto del usuario siempre con `esc()`.

## 2. Puente interfaz ↔ app (un contrato, tres anfitriones)
- La UI llama `host.enviar(accion, datos)`; el anfitrión responde llamando `window.<App>.<funcion>(json)`.
- Mac: `WKScriptMessageHandler` con un `switch` por acción. Electron: `preload` + `ipcMain` hacia un objeto `ACCIONES` con un caso por
  acción. Navegador: respuestas simuladas.
- **Prueba de contrato** (`pruebas/contrato.py`): toda acción que envía la UI existe en Swift **y** en Electron, y toda función que
  llaman las apps existe en la UI. Excepciones explícitas con motivo. Es lo que evita que una plataforma se quede atrás.

## 3. Ventanas personalizables
**Mac (Swift Package Manager, sin proyecto de Xcode, macOS 15):**
- App de barra de menú (`NSStatusItem`) con panel `WKWebView`; ventana principal `NSWindow` **sin borde y transparente**: la web
  dibuja la forma (esquinas, chaflanes, bordes rasgados) y la sombra sigue los píxeles. La web declara al nativo sus zonas de arrastre,
  exclusiones y bordes de cambio de tamaño; un `WKWebView` propio las atiende antes de pasar el clic a la página.
- Sin menú Edición (app de barra de menú): enruta ⌘C/V/X/A/Z a mano en `performKeyEquivalent`. Pantalla completa quita la forma.
- Alertas flotantes: `NSPanel` que no roba el foco, `acceptsFirstMouse` = true, vista SwiftUI con la paleta del tema, botón principal
  con atajo Enter. Nunca alertas del sistema para cosas propias de la app (actualizaciones, avisos): dentro de la app.
- Firma ad hoc con requisito por identificador (`--identifier app.<x>.mac` + designated requirement) para que los permisos de
  micrófono, pantalla, etc. sobrevivan a cada actualización.
**Windows y Linux (Electron):**
- Ventana sin marco rectangular con la misma UI, bandeja (`Tray`) en vez de barra de menú, `requestSingleInstanceLock`, ventanas
  ocultas para trabajo en segundo plano (p. ej. grabar audio con AudioWorklet), `safeStorage` para secretos.
- Lo específico del sistema (audio del sistema, detectar uso del micrófono, calendario) en módulos separados por plataforma.

## 4. Temas como datos (todo personalizable sin código)
- Cada tema es un JSON de **solo datos**: colores (`#hex` o `rgba()` — todos los anfitriones deben entender ambos), radio, fuentes,
  forma de la ventana, íconos, textos (rangos, logros…), `categorias`. Nunca campos que se ejecuten ni HTML sin escapar.
- Validar al cargar y al descargar; texto sobre el acento elegido por contraste WCAG (#fff/#111) y prueba de contraste por tema.
- Incluidos en la app + repo catálogo público (`<proyecto>-catalogo`) con `index.json` para vista previa; los descargados viven en la
  carpeta del usuario y ganan sobre los incluidos. Galería con búsqueda, categorías y "no existe, ¿quieres crearlo?" que lo genera
  con la IA del usuario. Votos = reacciones en un issue por tema; propuestas = issue con etiqueta y el JSON.

## 5. Idiomas
- El español es el idioma del código y las claves. `traducirDOM()` traduce el DOM ya pintado con un diccionario (`textos` con `{n}`/`{x}`,
  `palabras` para fechas); en Swift `Idioma.t()`/`Idioma.f()`. Contenido del usuario marcado `data-sin-traducir`.
- Prueba de interfaz que falla si queda un texto sin traducir. Más idiomas como paquetes JSON en el catálogo, creados con la IA y
  revisados por una persona nativa.

## 6. Lógica compartida y la IA del usuario
- Procesamiento en Python **solo biblioteca estándar**, igual en las tres plataformas; contrato: el último argumento es la ruta del JSON
  de salida. Python portátil (python-build-standalone) dentro de la app, verificado por SHA-256: el usuario no instala nada.
- Binarios pesados: oficiales en Mac (xcframework/Metal); en Windows/Linux compilados con zig (estáticos, sin DLLs, glibc antigua). Toda
  descarga con huella SHA-256 fija.
- IA: una sola función (`ejecutar_ia`) que arma el comando según la IA elegida (`claude -p`, `codex exec … -o archivo -`,
  `agy -p` de Antigravity) y amplía el PATH (Homebrew, npm, nvm, `~/.local/bin`). Mensajes con el nombre de la IA elegida.
- Datos del usuario fuera de la app, en formato abierto documentado (Markdown con frontmatter, marcadores fijos). Respaldo opcional en un
  repo **privado del usuario**, token en el Llavero/safeStorage y pasado a git en memoria (`-c http.extraHeader`), nunca en disco.

## 7. Primera vez y actualizaciones
- Asistente de bienvenida: idioma → quién eres → IA (detecta y prueba) → descargas verificadas → carpeta de datos → respaldo opcional
  → permisos → tema. Todo lo que haya que preguntar se pregunta en la app, nunca editando archivos.
- Actualizaciones: revisar al abrir y cada 6 h contra GitHub Releases; aviso en banner/Preferencias con barra de progreso por pasos y
  "Estás en la última versión". Un script espera a que la app cierre, reemplaza (deja `.anterior` si falla) y la reabre. Instalación de
  desarrollo (checkout git): `git pull` + build. Nunca actualizar en medio de un trabajo en curso.

## 8. Empaquetado e instaladores
- Mac: `herramientas/empaquetar.sh` → `.app` con todo adentro + `.zip` + `.sha256`; `build.sh` instala en `~/Applications` y se niega si
  hay trabajo en curso.
- Windows: `electron-builder --win dir` + NSIS propio por usuario (`/S` silencioso) en `%LOCALAPPDATA%\Programs`. Linux: AppImage y tar.gz;
  instalador en `~/.local/share/<App>` con lanzador que agrega `--no-sandbox` si el sistema lo exige. Todo se arma desde Linux, sin Wine.
- Instaladores de un comando (`instalar.sh` para Mac/Linux, `instalar.ps1` para Windows) que bajan la última Release y verifican la huella.
- `publicar.yml`: al cambiar la versión (`Info.plist` y `package.json` iguales) compila las tres plataformas y crea el Release con
  nombres fijos.

## 9. Pruebas
- Python con HOME temporal y una IA falsa en el PATH (nunca toca datos reales ni llama a una IA). Interfaz con Playwright en todos los
  idiomas y temas (errores de JS, textos sin traducir, contraste, capturas). Contrato. Compilación Swift en `macos-15` si cambió `app/`.
  Linux de punta a punta con Xvfb + PulseAudio virtual. Windows no se puede probar aquí: pídeselo a la comunidad con un issue `probar`.
- Evaluación de la salida de la IA (estructura y marcadores) antes de tocar un prompt.

## 10. Instalar en el computador de desarrollo
Comprueba que la app no esté trabajando (grabando/procesando), `git pull --ff-only`, build en segundo plano con `nohup` y log
(`FIN $?`), reabrir. Si está ocupada, no compiles: deja la actualización lista en el aviso de la app.

## 11. Lecciones de Graba (grabador de pantalla)
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