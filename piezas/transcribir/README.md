# Pieza «transcribir» — voz a texto en el computador

```python
import transcribir
segs = transcribir.transcribir(wav, idioma="es", vocabulario="Ana Pérez, Banco Ejemplo")  # [{desde, hasta, texto}] (segundos)
pal = transcribir.transcribir(wav, palabras=True)                                          # [{t, i, f}] palabra por palabra
segs = transcribir.transcribir(wav, energia_=transcribir.energia(wav))                     # además quita lo que cae en silencio
```
- Transcriptor: `<id>-transcribir` (Mac, el binario de la app) o `whisper-cli`, buscado en `<ID>_PROGRAMAS`/`<ID>_HERRAMIENTAS`,
  `bin/` y el sistema (`transcriptor()`).
- **El vocabulario nunca va como argumento**: `--prompt-archivo` (binario de la app) o `whisper-cli @archivo` (archivo de
  argumentos oficial), en una sola línea, en un temporal 0600 fuera de las carpetas de la persona que se borra siempre. Una ruta
  con salto de línea no se transcribe (`ruta`).
- `MODELOS` (`turbo`, `small`, `vad`) con tamaño, SHA-256 y URL de Hugging Face: los mismos de todas las apps. El host los
  descarga y verifica; `verificar(id)`, `modelos()` (acción `modelosVoz`), `modelo_elegido(preferido)` y `ruta_modelo(id)`
  (`<carpeta de datos>/modelos`). Con `vad` descargado, whisper salta los silencios.
- Limpieza (`limpiar(segs, energia_, partir=None)`): marcas (`[Música]`), créditos que nadie dice (`CREDITOS`: «…Amara.org»,
  siempre; dentro del segmento solo como palabras completas), bucles (más de 2 veces la misma frase seguida) y, con la energía,
  lo que cae en silencio. Las frases que whisper inventa pero la gente también dice (`ALUCINACIONES`: «Gracias», «Thank you»,
  «Gracias por ver»; coincidencia **exacta** con el segmento entero, así «Gracias, Ana» nunca cuenta) solo se quitan si caen en
  silencio o casi (`UMBRAL_INVENTO`, con la energía) o si no hay nada más en toda la transcripción (sin la energía).
  `partir(segs) -> segs` corre antes de filtrar (p. ej. partir por silencios).
- `whisper_de(segs)`: lo inverso de `segmentos_de` (el JSON de whisper, en milisegundos) para guardar y releer después.
- VAD: `vad=None` (por defecto: con segmentos sí, palabra por palabra no: cortaría la palabra al borde), `True`, `False` o la ruta
  del modelo (`ruta_vad`).
- Modelos en otra carpeta: `"transcribir": {"modelos": "~/ana/models"}` en `app.json` (con `~`, absoluta o relativa a la de
  datos; sin `..`). Para pruebas: `<ID>_MODELO_PRUEBA=<archivo>` es un modelo falso de cualquier tamaño (nunca dentro de la
  app: si está `<ID>_RECURSOS`, no cuenta).
- `transcriptor()`: primero las carpetas de la app (`<ID>_PROGRAMAS`, `<ID>_HERRAMIENTAS`, `bin/`) con todos los nombres, después
  el sistema.
- Errores: `ErrorTranscribir` con `codigo` (`sin_modelo`, `sin_transcriptor`, `fallo`, `ruta`), `detalle`, `plantilla` +
  `valores` (con detalle: «La transcripción falló: {detalle}»), `frase` (ya rellena) y `como_dict()`. `str(e)` es la frase corta.

## Si venías de la 0.1
- **Minuta:** quita `transcribir.carpeta_modelos = lambda: …` de `procesar.py` y pon `"transcribir": {"modelos": "~/minuta/models"}`
  en `app.json`. Con `energia_`, ahora un «Gracias.» dicho con voz queda en la nota.
- **Graba:** `transcripcion.json` con `transcribir.whisper_de(segs)`; el error con `e.frase` (o `e.como_dict()` para traducir)
  en vez de armar «frase: detalle»; en las pruebas, `GRABA_MODELO_PRUEBA=<archivo>` en vez del archivo disperso del tamaño exacto.
- **Corta:** palabra por palabra ya va sin VAD (lo que Corta quería); `vad=True` si lo quieres igual.
- Sin la energía, «Gracias por ver el video» al final de un video ahora queda (antes se borraba aunque se hubiera dicho).
- **Fase del host:** el binario Swift (`Sources/Transcribir`, whisper.xcframework con Metal + `--prompt-archivo`) y la descarga de
  modelos (`ModeloWhisper`) siguen en cada app hasta el host genérico.

## Pasar una app a esta pieza
**Minuta** (`bin/procesar.py`): borrar `_archivo_privado`, `_linea_ruta`, `comando_transcribir`, `herramienta` (para el
transcriptor), `ALUCINACIONES`, `leer_muestras`/`rms` (→ `transcribir.energia`/`rms`) y el bucle de `limpiar`; `transcribir(wav,
salida)` pasa a `transcribir.transcribir(wav, idioma=IDIOMA_AUDIO, modelo=MODELO, vocabulario=VOCABULARIO)`, que devuelve
`desde`/`hasta` (antes `ini`/`fin`) y ya no deja el JSON de whisper en la carpeta de la grabación. Lo propio de Minuta
(`corregir`, partir por silencios, «quien», eco) sigue en Minuta, sobre los segmentos. Los modelos viven en `~/minuta/models`:
dejar `"datos": {"carpeta": "~/minuta"}` y mover a `<datos>/modelos`, o pasar `modelo=` y la ruta del VAD (no mecánico). El
binario se llama `minuta-transcribir` = `<id>-transcribir`: sin cambios.
**Corta** (`bin/importar.py`): borrar `_archivo_privado`, `comando_transcribir`, `palabras_de_whisper`, `ALUCINACIONES` y
`ARCHIVOS_MODELO`; `transcribir(carpeta)` llama `transcribir.transcribir(audio, palabras=True, idioma=…, modelo=…,
vocabulario=vocabulario.prompt(vocab))` (devuelve `{t, i, f}`, lo mismo de antes). El binario `corta-transcribir` y
`CORTA_PROGRAMAS` ya calzan. Nuevo: con VAD si está descargado (decidir si Corta lo quiere: corta la palabra al borde).
**Graba** (`bin/procesar.py`): borrar `ALUCINACIONES`, `es_alucinacion`, `segmentos` y el armado del comando; `whisper-cli`
ahora **sí** recibe el vocabulario (antes no). `segmentos()` devolvía milisegundos (`desde`/`hasta` en ms): la pieza da
segundos (multiplicar por 1000 en `escribir_srt` o pasar a segundos). Las tres apps: la lista `Modelos` de Swift/Electron
puede leer `transcribir.py modelos` en vez de repetir huellas.
