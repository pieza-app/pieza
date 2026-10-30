# Pieza

Piezas probadas para armar apps abiertas que viven en tu computador. Cada pieza resuelve una cosa (tu IA, el idioma, el
catálogo, las actualizaciones…) y se enchufa en cualquier app de la familia con un comando, en vez de escribirla de cero.

Las usan [Minuta](https://github.com/minuta-app/minuta), [Graba](https://github.com/graba-app/graba),
[Corta](https://github.com/corta-app/corta), [Alcancía](https://github.com/alcancia-app/alcancia),
[Repasa](https://github.com/repasa-app/repasa) y [Esquema](https://github.com/esquema-app/esquema).

```bash
python3 herramientas/pieza.py listar                      # qué hay
python3 herramientas/pieza.py iniciar ~/MiApp miapp MiApp  # una vez por app: crea app.json
python3 herramientas/pieza.py agregar ia ~/MiApp           # copia la pieza (y lo que necesita)
python3 herramientas/pieza.py estado ~/MiApp               # qué tiene, qué hay nuevo, qué cambió la app
python3 herramientas/pieza.py actualizar ~/MiApp           # trae lo nuevo sin pisar tus cambios
```

**Copiar y adueñarse.** La pieza se copia dentro de tu app y desde ahí es tuya: la puedes cambiar. `piezas.json` recuerda la
versión y la huella de cada archivo, así `actualizar` nunca pisa lo que cambiaste y `diferencias` te muestra qué mejoraste para
devolverlo a la base.

- [El enchufe](docs/enchufe.md): cómo se conecta una pieza (contrato y reglas de seguridad).
- [Catálogo y plan](docs/catalogo.md): qué hay y qué viene.
- [Guía para contribuir](AGENTS.md).

Sin dependencias: Python con su biblioteca estándar. Licencia AGPL-3.0.
