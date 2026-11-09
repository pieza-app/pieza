# Crear una app

## Con tu IA (recomendado)

1. Instala los flujos de Pieza en tu IA:
   - Claude Code: `/plugin marketplace add pieza-app/pieza` y después `/plugin install pieza@pieza`.
   - Gemini CLI: `gemini extensions install https://github.com/pieza-app/pieza --auto-update`.
   - Codex: `python3 herramientas/pieza.py skills instalar codex`.
2. Pídele: «Creemos una app para…».
3. Tu IA te entrevista, te muestra la **ficha** (pantallas, permisos, red) y crea la app con sus pruebas en verde.

## Sin IA

1. Clona Pieza: `git clone https://github.com/pieza-app/pieza`.
2. Mira lo que hay: `python3 herramientas/pieza.py catalogo`.
3. Mira la app antes de crearla: `python3 herramientas/pieza.py ficha ia --plataformas mac,windows,linux`.
4. Créala: `python3 herramientas/pieza.py crear ~/MiApp --id miapp --nombre MiApp --plataformas mac,windows,linux --piezas ia`.
5. Pruébala: `cd ~/MiApp && bash pruebas/correr.sh`.
6. Ábrela: `cd escritorio && cargo run`.

Al final, `crear` dice qué te toca a ti (por ejemplo, crear la organización en GitHub) y qué le toca a tu IA.

## Reglas que trae toda app

- El **idioma** se pregunta primero.
- La **IA** es la tuya, con tu cuenta.
- Los **datos** quedan en tu computador.
- Nada personal en el código: ejemplos con datos ficticios (Ana Pérez, Matías Soto).
