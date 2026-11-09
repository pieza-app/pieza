# El programa Pieza: crear apps paso a paso

> Plan. Estado: en diseño. Repo de la app: `pieza-app/estudio` (la app se llama «Pieza»).
> Este documento es la fuente del plan. Cada fase abre sus issues en ese repo.

## Qué es

Pieza es una app de escritorio que crea apps con piezas ya hechas. Guía a la persona con «Siguiente, siguiente, siguiente». Usa la
IA de la persona, con su propia cuenta. Lo que ya es una pieza no gasta tokens. Así, cada app nueva sale más barata que la anterior.

No es un chat que escribe código (como Lovable). Es un asistente con pasos fijos, que revisa cada paso antes de seguir.

## Principios

1. **El idioma va primero.** Es la regla de toda la familia.
2. **La IA es la de la persona.** Claude Code, Codex o Gemini, con su cuenta. Pieza nunca usa una llave de API propia.
3. **Lo que ya existe no se paga.** Una pieza lista cuesta 0 tokens: se copia, no se escribe.
4. **Nada avanza en rojo.** Después de cada paso corren las pruebas. Si fallan, la IA ve el error y corrige.
5. **La persona ve el costo.** Cada paso muestra un estimado de tokens antes de gastarlos y lo gastado después.
6. **Los datos son de la persona.** La app nueva vive en su computador y en su GitHub. Nada pasa por un servidor nuestro.
7. **Las piezas se siguen usando sin la app.** `pieza.py` y los flujos para IA (skills) no dependen de Pieza.

## El flujo

| Paso | Qué pregunta o hace | Gasta tokens |
|---|---|---|
| 0. Idioma | Español o English (pieza «bienvenida») | No |
| 1. Sistemas | Escritorio (Mac, Windows, Linux), celular (iPhone, Android) o solo web | No |
| 2. La idea | «¿Qué hace tu app y para quién?» en una frase | Poco |
| 3. Las piezas | La IA propone piezas del catálogo (`pieza.py catalogo --json`). La persona marca o desmarca | Poco |
| 4. La ficha | Pantallas, configuración, permisos y red (`pieza.py ficha`). La persona confirma | No |
| 5. El plan | La IA desglosa lo propio en pasos chicos, con su estimado | Poco |
| 6. Crear | `pieza.py crear` con las piezas elegidas. Las pruebas quedan en verde | No |
| 7. Lo propio, paso a paso | La IA escribe cada paso del plan. Después de cada uno corren las pruebas | Sí |
| 8. Probar | Abrir la app (`cargo run`) y la vista previa | No |
| 9. Publicar | Repo en el GitHub de la persona, página, primera versión | No |
| 10. Proponer piezas | Lo nuevo que sirva a otras apps se ofrece a Pieza como pieza | Poco |

### Paso 1: sistemas

El sistema decide qué piezas aplican. Por eso va antes de la idea.

| Elige | Piezas de base |
|---|---|
| Escritorio | `host-tauri`, `empaquetado`, `actualizaciones` |
| iPhone | `host-ios` |
| Android | `host-movil` (planeada) |
| Solo web | ninguna de host: la interfaz y la vista previa |

### Paso 3: las piezas y el ícono de Pieza

- Cada pieza lista lleva el ícono de Pieza y la etiqueta **«0 tokens: ya está hecha»**.
- Una pieza planeada dice **«Por hacer»**. Pieza ofrece hacerla primero como pieza (así sirve para todas las apps).
- Las piezas de `siempre` (idioma, tema, componentes…) van marcadas y no se preguntan.

### Paso 5: el plan por pasos

- La IA devuelve el plan como una lista de pasos chicos, en JSON validado.
- Cada paso dice qué archivos toca y un estimado de tokens.
- La persona puede quitar, reordenar o juntar pasos.

### Paso 7: dos modos

| Modo | Cómo funciona |
|---|---|
| **Paso a paso** | La persona aprueba cada paso. Ve el consumo de su IA después de cada uno. |
| **Todo automático** | Pieza corre todos los pasos sola. Se detiene si llega al tope de tokens que la persona puso, o si un paso falla dos veces. |

En los dos modos, cada paso sigue este orden:

1. Pieza le manda a la IA **solo la guía de ese paso**, la ficha y las reglas que no se negocian. No manda un prompt gigante.
2. La IA responde un plan corto: qué archivos va a tocar y por qué.
3. La persona aprueba (o pasa solo en el modo automático).
4. La IA escribe.
5. Pieza corre las pruebas (`correr.sh`, el contrato y la privacidad).
6. Si fallan, la IA recibe el error y corrige. Tiene dos intentos.
7. Pieza anota los tokens gastados.

## La guía para la IA

- La guía es el flujo `skills/lanzar-proyecto-open-source/SKILL.md`, partido por paso.
- Cada paso tiene su archivo de guía corto en el repo de la app. Lleva una «versión del flujo».
- Lo que aprendemos en cada app se anota en la guía y sube su versión.

## El consumo de tokens

- Pieza mide lo que puede: el largo del pedido y de la respuesta, y lo que informe el CLI de la IA.
- Muestra el estimado antes del paso y lo gastado después.
- Muestra cuánto se ahorró por las piezas ya hechas (estimado con el tamaño de sus archivos).

## Publicar y la comunidad

- **Publicar es opcional.** La app nueva se publica en el GitHub de la persona, con su sesión de `gh`. Nadie da permisos a nadie.
- **El explorador.** Al crear el repo, Pieza pregunta: «¿Quieres aparecer en el explorador de Pieza?». Si dice que sí, el repo
  recibe el topic `hecho-con-pieza`. El catálogo diario de Pieza lo encuentra. Solo lee: no necesita tokens de terceros.
- **Dos exploradores dentro de la app:** piezas (oficiales y de la comunidad) y apps hechas con Pieza.
- **Aparecer no es confianza.** El sello «revisada» llega solo después de una revisión. Lo que se instala viene de un Release con su
  huella SHA-256.
- **Una pieza nueva** se propone con un PR desde la cuenta de la persona a `pieza-app/pieza`. Se revisa como cualquier aporte.

## Fases

| Fase | Entrega |
|---|---|
| 1. Esqueleto | La app creada con `pieza.py crear` (host-tauri, ia, trabajos), pruebas en verde, repo `pieza-app/estudio` |
| 2. Pasos 0 a 4 | Idioma, sistemas, idea, piezas con el ícono de Pieza y la ficha. Sin escribir código todavía |
| 3. Pasos 5 a 7 | El plan por pasos, los dos modos, las pruebas después de cada paso y el consumo |
| 4. Pasos 8 a 10 | Probar, publicar en el GitHub de la persona, el explorador y proponer piezas |
| 5. Temas y universos | Las piezas `tema` (Claro, Oscuro, Vidrio) y `universos`, con aportes de la comunidad por el catálogo |

## Lo que falta decidir

- El tope por defecto de tokens en el modo automático.
- Cómo leer el consumo real de cada CLI (Claude Code, Codex y Gemini lo informan distinto).
- Si la app nueva se crea en una carpeta que elige la persona o siempre en `~/Pieza/<app>`.
