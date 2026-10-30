---
name: "diseno-y-calidad-de-producto"
description: "Criterios de diseño UX/UI y buenas prácticas de construcción para cualquier app o página de la familia Pieza: claridad, respeto al usuario, accesibilidad, idiomas, pruebas y verificación."
---

# Diseño y calidad de producto (lo aprendido construyendo Minuta)

Versión del flujo: 1

Parte del flujo de Pieza (pieza-app/pieza). Si hay una sección «Configuración local» al final, manda sobre lo genérico.

Úsala al diseñar o construir cualquier pantalla, flujo o función. Actúa como el mejor diseñador UX/UI y como un ingeniero cuidadoso:
las dos cosas a la vez. Cuando alguien manda una captura con un problema, arregla la causa (no solo ese caso) y revisa dónde más pasa.

## Diseño: cómo se siente usarla
**Nunca dejar a la persona en incertidumbre**
- Toda espera muestra qué está pasando: pasos y barra de progreso ("Preparando la versión nueva… 2/3"), no un botón congelado.
- Toda acción tiene respuesta, también cuando no hay nada que hacer ("Estás en la última versión", "Sin conexión, reintento luego").
- Búsqueda sin resultados = una salida: "Aún no existe «X», ¿quieres crearlo?" con el botón que lo hace.

**Respetar a la persona**
- Los avisos propios de la app van **dentro de la app** (banner, Preferencias), nunca como alerta del sistema.
- Nada obligatorio ni insistente: comentarios, votos, compartir o cuentas aparecen solo cuando la persona los busca. Sin pop-ups que
  sugieran cosas.
- Acciones que borran o cambian mucho preguntan con opciones claras (p. ej. "Borrar solo aquí" / "Borrar también del respaldo") y
  guardan copia antes. Las correcciones con IA dejan respaldo.
- Que la app haga el trabajo: la persona dice lo que quiere en palabras ("Matías no es el PO, es el Scrum Master") y la app corrige
  todo lo relacionado, en vez de obligarla a buscar y reemplazar.
- Plug and play: lo que haya que configurar se pregunta en la app, nunca editando archivos.
- Créditos y enlaces (sitio, código, comunidad) en "Acerca de", sin ocupar espacio principal.

**Compacto y sin redundancia**
- Cada cosa vive en un solo lugar; si dos elementos muestran lo mismo, sobra uno. En vistas chicas (paneles, barra de menú): una fila por
  idea, menús desplegables en vez de chips que se desbordan, filas delgadas para avisos.
- Jerarquía clara: una acción principal por pantalla, el resto secundaria.
- Al volver a pintar, mantener el scroll y el foco donde estaban.

**Que se vea bien en todos los casos**
- Contraste WCAG calculado (texto #fff o #111 sobre el acento) y probado en **todos** los temas, no solo en el que se está mirando.
  Colores en cualquier formato que use un tema (`#hex`, `rgba()`): un formato no entendido no puede caer a negro.
- Revisar a ancho de celular y en paneles angostos: nada solapado ni scroll horizontal (`minmax(0,1fr)` en grillas, textos que cortan).
- Probar con textos largos, en inglés (suele ser más largo o más corto) y con datos vacíos.
- Accesible: se puede usar con teclado, foco visible, botones con nombre, `Esc` cierra diálogos.

**Idiomas**
- **Lo primero que pregunta una app es el idioma.** En el primer uso, el paso 0 de la bienvenida es solo elegir idioma: título
  bilingüe fijo ("Elige tu idioma · Choose your language"), un botón grande por idioma escrito en su propio idioma (no pasa por el
  traductor), el del sistema marcado como sugerido y con el foco. Nada se muestra ni se pide antes: ni la app detrás, ni avisos de
  actualización, ni permisos del sistema, ni alertas, ni atajos que abran cosas; las tareas de arranque que muestran algo esperan a que
  haya idioma. Al elegir se guarda por el mismo camino que Ajustes y todo lo que sigue (incluidos menús y avisos nativos) sale en ese
  idioma. Quien ya hizo la bienvenida no la repite. Con prueba que lo revise.
- Frases completas con marcadores (`{n}`, `{x}`), nunca pedazos pegados en la interfaz: se traducen mal o no se traducen.
- Contenido del usuario nunca pasa por el traductor. Todo texto nuevo entra con su traducción en el mismo cambio.

**Honestidad**
- Nada inventado en la app ni en la página: sin testimonios, cifras ni promesas que no se cumplen. Si algo falta (firma, una plataforma
  sin probar), se dice y se explica cómo seguir.

## Construcción: buenas prácticas
**Antes de cambiar**
- Lee la guía del repo (`AGENTS.md`) y el código que vas a tocar. Respeta los principios que no se negocian y el formato de datos
  documentado (otros dependen de él: compatibilidad o versión nueva explícita).
- Busca la causa raíz y dónde más aparece el mismo error.

**Al construir**
- Lo más simple que funcione: biblioteca estándar, sin dependencias nuevas sin conversarlo, sin frameworks si no hacen falta.
- Nombres descriptivos y comentarios que explican el porqué, en el idioma del proyecto.
- Funciones puras para la lógica, con casos de prueba compartidos entre lenguajes cuando la misma regla existe en dos lados (un JSON de
  casos que leen Python y JS).
- Contratos explícitos entre piezas (interfaz ↔ apps, scripts ↔ app) y una prueba que los revise.
- Seguridad por defecto: secretos en el Llavero/almacenamiento seguro, nunca en disco, URL ni logs; descargas con huella SHA-256 fija;
  todo dato externo (temas, traducciones, respuestas de la IA) se valida y se escapa antes de mostrarse.
- La salida de una IA se valida (estructura, marcadores) antes de aplicarla; si no cumple, no se aplica y se avisa.
- Datos de ejemplo siempre ficticios; revisión de privacidad antes de cada commit en repos públicos.

**Antes de decir "listo"**
- Corre las pruebas (lógica, contrato, interfaz en todos los idiomas). Si agregaste algo, agrega su caso.
- Mira el resultado: abre la página o la vista, captura a ancho normal y de celular, en los temas afectados. No confíes solo en que
  compile.
- Si hay CI, espera que quede en verde. Si toca la app instalada del usuario, comprueba que no esté trabajando antes de reinstalar.
- Commits pequeños y en español que digan qué cambia para quien usa la app. Nunca reescribas historia publicada.
- Explica a la persona en pocas líneas qué cambió y qué tiene que hacer él (si algo), sin jerga.