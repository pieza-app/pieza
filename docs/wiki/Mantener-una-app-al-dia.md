# Mantener una app al día

## «Pieza al día»

Una vez por semana, cada app recibe un pull request con lo que se puede actualizar solo, y un issue con los pasos para lo demás.
Cada cambio dice su tipo: arreglo, mejora, rompe o seguridad.

## Dependabot

- **Actions:** Dependabot abre un PR cuando hay una versión nueva (fijadas por SHA, con `cooldown`).
- **Crates de Rust:** en las apps solo llegan los PR de **seguridad**. Las versiones nuevas suben primero en Pieza
  (`pruebas/tauri`, con sus pruebas) y llegan a las apps con «Pieza al día».
- `glib` se ignora: la versión arreglada necesita gtk4, y Tauri todavía usa gtk3 (solo en Linux).

## Publicar una versión

1. Sube `version` en `app.json` (también en `escritorio/Cargo.toml`, `Cargo.lock` y `escritorio/tauri.conf.json`: el contrato
   revisa que sean iguales).
2. En `CHANGELOG.md`, las líneas de «Sin publicar» pasan a «## X.Y.Z».
3. Junta el cambio en `main`.
4. «Publicar versión» arma la app en cada sistema y crea el Release con su `.sha256`.
5. El actualizador de la app la ofrece a quien ya la tiene.

## La wiki

La wiki se publica sola desde `docs/wiki/` (workflow `wiki.yml`). La primera vez hay que crearla a mano: pestaña «Wiki» →
«Create the first page» → «Save».
