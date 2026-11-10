# Todo en Rust

Pieza es Rust + Tauri. Sus piezas, su lógica y las apps que crea también van a Rust. Un solo lenguaje para la app nativa, las
piezas y las herramientas: menos piezas que mantener, un binario liviano y sin un Python portátil dentro de cada app.

La interfaz sigue siendo HTML, CSS y JavaScript en el WebView del sistema (las piezas de interfaz no cambian).

## Fases

Cada fase se publica sola y deja todo andando. Una pieza en Rust convive con su versión en Python hasta que ninguna app use la de
Python.

| Fase | Qué | Estado |
|---|---|---|
| 1 | Piezas de base en Rust: `ia` (`tauri/ia.rs`), `nucleo` (ya vive en `host-tauri/enchufe.rs`), `red` (`tauri/red.rs`), `trabajos` (`tauri/trabajos.rs`) | lista: `ia` 0.8.0, `red` 0.3.0, `trabajos` 0.3.0 |
| 2 | Acciones en Rust: `"rust": true` en `app.json` y `host.funcion(nombre, |entrada, avance| …)` en vez de un script, por el mismo camino (validar, inyectar, fila, límite, eco, después) | lista: `host-tauri` 0.2.0 |
| 3 | La lógica del programa Pieza (`proyectos`, `publicar`, `requisitos`, `piezas`) en Rust | por hacer |
| 4 | Lo que crea Pieza: el esqueleto, las reglas para la IA y las pruebas (`cargo test`) en Rust | por hacer |
| 5 | Las herramientas: un binario `pieza` en Rust reemplaza `pieza.py` y los scripts de prueba | por hacer |
| 6 | Las apps de hoy, una por una, sin cambiar sus datos: Pilota, Despeja, Repasa, Esquema, Corta, Alcancía, Minuta y Graba | por hacer |

## Reglas para el código Rust de una pieza

- Las mismas reglas que en Python: la IA es la de la persona, el pedido nunca como argumento, lo de afuera se valida, nada
  personal, liviano.
- Dependencias: solo las que ya trae `host-tauri` (`serde_json`, `regex`, `ureq`…). Una nueva se discute antes.
- Cada archivo Rust de una pieza va en `piezas/<id>/tauri/` con `solo_con: ["host-tauri"]` y sus pruebas en el mismo archivo
  (`#[cfg(test)]`). `pruebas/tauri` lo compila con `cargo test` y `cargo clippy -- -D warnings`.
