// Para pruebas/test_piezas.py: las reglas de una acción en Rust (enchufe.rs de «host-tauri»), para compararlas con las de
// pieza.py y enchufe.js. Recibe una lista de acciones en JSON y responde una lista de true/false (pasa o no pasa).
#[path = "../../../../piezas/host-tauri/tauri/enchufe.rs"]
#[allow(dead_code)]
mod enchufe;

fn main() {
    let casos: Vec<serde_json::Value> = serde_json::from_str(&std::env::args().nth(1).unwrap_or_default()).expect("una lista JSON");
    let r: Vec<bool> = casos.iter().map(|a| enchufe::errores_accion("x", a).is_empty()).collect();
    println!("{}", serde_json::to_string(&r).expect("JSON"));
}
