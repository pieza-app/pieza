// La app de prueba de la pieza «host-tauri»: arranca con la app ficticia de app/, registra una acción propia y un medio.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
#[path = "../../../piezas/host-tauri/tauri/mod.rs"]
mod pieza;
#[path = "../../../piezas/trabajos/tauri/progreso.rs"]
#[allow(dead_code)]
mod progreso;
#[path = "../../../piezas/actualizaciones/tauri/actualizaciones.rs"]
#[allow(dead_code)]
mod actualizaciones;

use serde_json::json;

fn main() {
    let raiz = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("app");
    let op = pieza::host::Opciones {
        recursos: Some(raiz.clone()),
        lector_progreso: Some(std::sync::Arc::new(progreso::Lector)),
        actualizaciones: actualizaciones::Actualizaciones::nuevas("pieza-app/pieza", "Prueba").ok().map(|a| std::sync::Arc::new(a) as _),
        ..Default::default()
    };
    pieza::host::arrancar(tauri::generate_context!(), op, move |host| {
        host.registrar("propia", |d, h, ctx| {
            h.llamar("propia", json!({"n": d["n"].as_i64().unwrap_or(0) * 2}), ctx.destino());
        });
        let r = raiz.clone();
        host.registrar_medios("imagenes", move |ruta, _| (ruta == "punto.png").then(|| r.join("punto.png")));
    });
}
