// {{nombre|linea}}: la app nativa (pieza «host-tauri»). Desde aquí es de la app: registra lo propio (acciones que no son un
// script, medios, menús) y deja lo demás al host. Lo que solo corre un script se declara en app.json → acciones.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
mod pieza;
{{#si piezas.trabajos}}
#[path = "pieza/progreso.rs"]
mod progreso;
{{/si}}
{{#si piezas.catalogo}}
#[path = "pieza/catalogo.rs"]
mod catalogo;
{{/si}}
{{#si piezas.actualizaciones}}
#[path = "pieza/actualizaciones.rs"]
mod actualizaciones;
{{/si}}

use pieza::host::{arrancar, Opciones};
#[allow(unused_imports)]
use std::sync::Arc;

fn main() {
    let op = Opciones {
        global: Some("{{nombre_ascii}}".into()),
        sitio: Some("{{web|https}}".into()),
        codigo: Some("https://github.com/{{repo}}".into()),
{{#si piezas.trabajos}}
        lector_progreso: Some(Arc::new(progreso::Lector)),
{{/si}}
{{#si piezas.actualizaciones}}
        actualizaciones: actualizaciones::Actualizaciones::nuevas("{{repo}}", {{nombre|json}}).ok().map(|a| Arc::new(a) as _),
{{/si}}
        ..Default::default()
    };
    arrancar(tauri::generate_context!(), op, |_host| {
        // _host.registrar("exportar", |datos, host, ctx| { … host.llamar("exportado", serde_json::json!({"ok": true}), ctx.destino()); });
    });
}
