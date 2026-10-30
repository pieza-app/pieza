## Qué cambia / What changes

<!-- En una o dos frases, desde el punto de vista de las apps que usan la pieza (o de quien usa el flujo). -->

## Cómo lo probaste / How you tested it

- [ ] `bash pruebas/correr.sh` pasa (valida todos los `pieza.json`, corre las pruebas, revisa workflows y privacidad)
- [ ] Si toqué una pieza: su `pieza.json` está completo y honesto (`pantallas`, `permisos`, `red`, `recomendar`, `requiere`,
      `compatible`), trae su `icono.svg` (24×24, `currentColor`, solo formas) y cada acción tiene `limite`; nada de lo que
      escribe la persona va en `args`
- [ ] Si cambia lo que la app recibe: subí `version` y anoté en `cambios` el `tipo` (`arreglo`, `mejora` o `rompe` con `migrar`;
      `seguridad: true` si corresponde)
- [ ] Agregué o ajusté pruebas en `pruebas/test_piezas.py` (con datos ficticios)
- [ ] Sin dependencias nuevas (Python solo biblioteca estándar; sin npm ni CDN en la interfaz)
- [ ] Si toqué un flujo (`skills/`): subí «Versión del flujo»
- [ ] Anoté el cambio en `CHANGELOG.md` (y `docs/catalogo.md` si una pieza pasa a «lista»), o lo digo aquí para que lo completen
      quienes mantienen / Updated `CHANGELOG.md` (or said so here)
- [ ] No agregué datos reales ni personales (`bash herramientas/revisar_privacidad.sh --generico`)

<!-- Si usaste una IA para programarlo, perfecto: AGENTS.md y docs/enchufe.md tienen las reglas del proyecto. -->
