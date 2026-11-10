// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.
//! Pieza «trabajos» en Rust: lo que tarda minutos corre en un hilo, por etapas, sin perder nada. Solo `serde_json` y `regex`.
//!
//! La misma pieza que `python/trabajos.py`, con el mismo formato en disco (`formato: 1`): un trabajo de antes se sigue viendo.
//! - Su estado en `<carpeta de datos>/trabajos/<id>.json` (0600), escrito de una vez en cada cambio.
//! - Sus eventos van a la interfaz por `emitir` (la app lo conecta a su función de avance): `{"t": "estado", "trabajo": <vista>}`
//!   en cada cambio y `{"t": "lee" | "busca", …}` por cada archivo que lee la IA.
//! - Un «latido» cada 5 s: si el estado dice «corriendo» y el latido es viejo, la app se cerró y el trabajo queda «interrumpido»,
//!   listo para «Seguir».
//! - «Detener» deja `trabajos/<id>.detener`: el trabajo lo ve con `detenido()` (se lo pasa a `ia.preguntar_vivo` como `detener`).
//! - «esperando»: el trabajo le preguntó algo a la persona (`esperar`); la respuesta lo retoma (`seguir`).
//!
//! ```ignore
//! let t = trabajos.crear("resumir", &carpeta, &["leer", "escribir"], json!({}))?;
//! t.latir();
//! let r = ia.preguntar_vivo(&pedido, &o, &mut |e| match &e { Evento::Lee { ruta } => t.leyo(ruta), _ => {} }, &|| t.detenido());
//! match r { Ok(_) => t.terminar("listo", None), Err(e) if e.detenido() => t.terminar("detenido", None),
//!           Err(e) => t.terminar("error", Some(Fallo::Ia(e.json()))) }
//! ```
//!
//! Estados: corriendo → listo | con-fallas | detenido | error | esperando; un «corriendo» sin latido es «interrumpido».

use regex::Regex;
use serde_json::{json, Map, Value};
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex, OnceLock};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

pub const LATIDO: Duration = Duration::from_secs(5);
/// Sin latido por más que esto (segundos) = el proceso ya no está.
pub const MUERTO: f64 = 45.0;
/// Trabajos viejos que se conservan.
pub const MAX_GUARDADOS: usize = 40;

pub type Emisor = Arc<dyn Fn(Value) + Send + Sync>;

/// Por qué terminó mal: un texto, o un error de la IA ({codigo, plantilla, valores}) que la interfaz traduce.
#[derive(Clone, Debug)]
pub enum Fallo {
    Texto(String),
    Ia(Value),
}

fn segundos() -> f64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0)
}

/// (año, mes, día, hora, minuto, segundo) en UTC, sin dependencias.
fn fecha_utc(s: u64) -> (i64, u32, u32, u64, u64, u64) {
    let dias = (s / 86_400) as i64;
    let resto = s % 86_400;
    // Días civiles (H. Hinnant).
    let z = dias + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    let a = yoe + era * 400 + i64::from(m <= 2);
    (a, m, d, resto / 3600, resto % 3600 / 60, resto % 60)
}

/// La hora en ISO 8601 (UTC), como guarda el estado.
pub fn ahora() -> String {
    let (a, m, d, h, mi, s) = fecha_utc(segundos() as u64);
    format!("{a:04}-{m:02}-{d:02}T{h:02}:{mi:02}:{s:02}+00:00")
}

fn hex(n: usize) -> String {
    use std::hash::{BuildHasher, Hasher};
    let mut x = std::collections::hash_map::RandomState::new().build_hasher();
    x.write_u128(SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0));
    format!("{:016x}", x.finish()).chars().take(n).collect()
}

pub fn id_valido(i: &str) -> bool {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"^\d{8}T\d{6}-[0-9a-f]{6}$").expect("regex")).is_match(i)
}

fn carpeta_privada(c: &Path) -> std::io::Result<()> {
    fs::create_dir_all(c)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(c, fs::Permissions::from_mode(0o700))?;
    }
    Ok(())
}

fn escribir_json(ruta: &Path, v: &Value) -> std::io::Result<()> {
    let tmp = ruta.with_extension(format!("{}.tmp", hex(6)));
    let mut o = fs::OpenOptions::new();
    o.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        o.mode(0o600);
    }
    o.open(&tmp)?.write_all(&serde_json::to_vec_pretty(v).unwrap_or_default())?;
    fs::rename(&tmp, ruta)
}

fn leer_json(ruta: &Path) -> Option<Value> {
    if fs::metadata(ruta).ok()?.len() > 20 * 1024 * 1024 {
        return None;
    }
    serde_json::from_slice(&fs::read(ruta).ok()?).ok()
}

fn texto_error(f: Option<Fallo>) -> (String, Option<Value>) {
    match f {
        None => (String::new(), None),
        Some(Fallo::Texto(t)) => (t.chars().take(600).collect(), None),
        Some(Fallo::Ia(e)) => {
            let s = |k: &str| e.get(k).and_then(Value::as_str).unwrap_or("").to_string();
            let valores: Map<String, Value> = e.get("valores").and_then(Value::as_object).map(|m| m.iter()
                .map(|(k, v)| (k.clone(), json!(v.as_str().map(String::from).unwrap_or_else(|| if v.is_null() { String::new() } else { v.to_string() })
                    .chars().take(300).collect::<String>()))).collect()).unwrap_or_default();
            let mut t = s("plantilla");
            for (k, v) in &valores {
                t = t.replace(&format!("{{{k}}}"), v.as_str().unwrap_or(""));
            }
            (t.trim().chars().take(600).collect(), Some(json!({"codigo": s("codigo"), "plantilla": s("plantilla"), "valores": valores})))
        }
    }
}

/// «corriendo» con un latido viejo es un trabajo interrumpido (se cerró la app).
pub fn estado_real(x: &Value) -> String {
    let estado = x.get("estado").and_then(Value::as_str).unwrap_or("").to_string();
    if estado == "corriendo" && segundos() - x.get("latido").and_then(Value::as_f64).unwrap_or(0.0) > MUERTO {
        return "interrumpido".into();
    }
    estado
}

/// Todos los trabajos de una app (la carpeta `trabajos/` dentro de su carpeta de datos).
#[derive(Clone)]
pub struct Trabajos {
    carpeta: PathBuf,
    emitir: Emisor,
}

impl Trabajos {
    pub fn nuevos(datos: &Path, emitir: Emisor) -> Self {
        Trabajos { carpeta: datos.join("trabajos"), emitir }
    }

    fn nombres(&self) -> Vec<String> {
        let mut v: Vec<String> = fs::read_dir(&self.carpeta).into_iter().flatten().flatten()
            .filter_map(|e| e.file_name().into_string().ok())
            .filter(|n| n.strip_suffix(".json").is_some_and(id_valido))
            .collect();
        v.sort();
        v.reverse();
        v
    }

    fn envolver(&self, x: Value) -> Arc<Trabajo> {
        Arc::new(Trabajo { x: Mutex::new(x), carpeta: self.carpeta.clone(), emitir: self.emitir.clone(), latiendo: Arc::new(AtomicBool::new(false)) })
    }

    pub fn crear(&self, tipo: &str, proyecto: &str, etapas: &[&str], datos: Value) -> std::io::Result<Arc<Trabajo>> {
        let (a, m, d, h, mi, s) = fecha_utc(segundos() as u64);
        let id = format!("{a:04}{m:02}{d:02}T{h:02}{mi:02}{s:02}-{}", hex(6));
        let t = self.envolver(json!({"formato": 1, "id": id, "tipo": tipo, "proyecto": proyecto, "estado": "corriendo",
            "etapa": etapas.first().copied().unwrap_or(""), "etapas": etapas, "hechas": [], "inicio": ahora(), "latido": segundos(),
            "datos": datos, "items": [], "leidos": 0, "leyendo": "", "error": ""}));
        t.guardar(true)?;
        self.limpiar_viejos();
        Ok(t)
    }

    pub fn cargar(&self, id: &str) -> Result<Arc<Trabajo>, String> {
        if !id_valido(id) {
            return Err("No encontré ese trabajo.".into());
        }
        match leer_json(&self.carpeta.join(format!("{id}.json"))) {
            Some(x) if x.get("formato") == Some(&json!(1)) => Ok(self.envolver(x)),
            _ => Err("No encontré ese trabajo.".into()),
        }
    }

    fn de(&self, filtro: impl Fn(&Value) -> bool) -> Vec<Arc<Trabajo>> {
        self.nombres().iter().take(MAX_GUARDADOS * 3).filter_map(|n| leer_json(&self.carpeta.join(n)))
            .filter(|x| x.is_object() && filtro(x)).map(|x| self.envolver(x)).collect()
    }

    /// El último trabajo de esta carpeta (el más nuevo), de uno de esos tipos si se dicen.
    pub fn del_proyecto(&self, proyecto: &str, tipos: &[&str]) -> Option<Arc<Trabajo>> {
        self.de(|x| x.get("proyecto").and_then(Value::as_str) == Some(proyecto)
            && (tipos.is_empty() || x.get("tipo").and_then(Value::as_str).is_some_and(|t| tipos.contains(&t)))).into_iter().next()
    }

    /// Los trabajos de esta carpeta que esperan respuestas de la persona.
    pub fn esperando(&self, proyecto: &str) -> Vec<Arc<Trabajo>> {
        self.de(|x| x.get("proyecto").and_then(Value::as_str) == Some(proyecto) && x.get("estado").and_then(Value::as_str) == Some("esperando"))
    }

    /// Borra los viejos (más de MAX_GUARDADOS); los que esperan respuestas no se borran.
    pub fn limpiar_viejos(&self) {
        for n in self.nombres().into_iter().skip(MAX_GUARDADOS) {
            if leer_json(&self.carpeta.join(&n)).and_then(|x| x.get("estado").cloned()) == Some(json!("esperando")) {
                continue;
            }
            let base = n.trim_end_matches(".json");
            for ext in [".json", ".antes.json", ".detener"] {
                let _ = fs::remove_file(self.carpeta.join(format!("{base}{ext}")));
            }
        }
    }

    /// «Detener»: deja la marca que el trabajo revisa con `detenido()`. Solo si sigue corriendo.
    pub fn detener(&self, id: &str) -> Result<Value, String> {
        let t = self.cargar(id)?;
        if t.estado() != "corriendo" {
            return Ok(json!({"ok": true, "trabajo": t.vista()}));
        }
        carpeta_privada(&self.carpeta).map_err(|e| e.to_string())?;
        fs::write(t.ruta_detener(), ahora()).map_err(|e| e.to_string())?;
        Ok(json!({"ok": true, "deteniendo": true, "trabajo": t.vista()}))
    }

    pub fn ver(&self, id: &str) -> Result<Value, String> {
        Ok(json!({"ok": true, "trabajo": self.cargar(id)?.vista()}))
    }
}

/// Un trabajo: {formato, id, tipo, proyecto, estado, etapa, etapas, hechas, inicio, fin, latido, datos, items, leidos, leyendo, error}.
pub struct Trabajo {
    x: Mutex<Value>,
    carpeta: PathBuf,
    emitir: Emisor,
    latiendo: Arc<AtomicBool>,
}

impl Trabajo {
    fn con<R>(&self, f: impl FnOnce(&mut Value) -> R) -> R {
        f(&mut self.x.lock().unwrap_or_else(|e| e.into_inner()))
    }

    pub fn id(&self) -> String {
        self.con(|x| x["id"].as_str().unwrap_or("").to_string())
    }

    pub fn estado(&self) -> String {
        self.con(|x| estado_real(x))
    }

    /// Lo propio del tipo de trabajo (`datos`), para leer o cambiar.
    pub fn datos<R>(&self, f: impl FnOnce(&mut Value) -> R) -> R {
        self.con(|x| f(&mut x["datos"]))
    }

    pub fn guardar(&self, emitir_estado: bool) -> std::io::Result<()> {
        carpeta_privada(&self.carpeta)?;
        let (x, id) = self.con(|x| (x.clone(), x["id"].as_str().unwrap_or("").to_string()));
        escribir_json(&self.carpeta.join(format!("{id}.json")), &x)?;
        if emitir_estado {
            (self.emitir)(json!({"t": "estado", "trabajo": self.vista()}));
        }
        Ok(())
    }

    pub fn etapa(&self, nombre: &str) {
        self.con(|x| {
            let actual = x["etapa"].clone();
            if actual != json!(nombre) && !x["hechas"].as_array().is_some_and(|h| h.contains(&actual)) {
                if let Some(h) = x["hechas"].as_array_mut() {
                    h.push(actual);
                }
            }
            x["etapa"] = json!(nombre);
        });
        let _ = self.guardar(true);
    }

    /// Termina: listo, con-fallas, detenido o error. Lo que quedó «escribiendo» vuelve a la cola («Seguir» lo retoma).
    pub fn terminar(&self, estado: &str, fallo: Option<Fallo>) {
        let (texto, error_ia) = texto_error(fallo);
        self.con(|x| {
            let actual = x["etapa"].clone();
            if estado == "listo" && !x["hechas"].as_array().is_some_and(|h| h.contains(&actual)) {
                if let Some(h) = x["hechas"].as_array_mut() {
                    h.push(actual);
                }
            }
            for i in x["items"].as_array_mut().into_iter().flatten() {
                if i.get("estado") == Some(&json!("escribiendo")) {
                    i["estado"] = json!("cola");
                }
            }
            x["estado"] = json!(estado);
            x["fin"] = json!(ahora());
            x["error"] = json!(texto);
            x["leyendo"] = json!("");
            let o = x.as_object_mut().expect("objeto");
            o.remove("error_ia");
            if let Some(e) = error_ia {
                o.insert("error_ia".into(), e);
            }
        });
        let _ = self.guardar(true);
        self.latiendo.store(false, Ordering::SeqCst);
        let _ = fs::remove_file(self.ruta_detener());
    }

    /// Le pregunta algo a la persona (preguntas ya validadas con `limpiar_preguntas`): queda «esperando».
    pub fn esperar(&self, preguntas: Value, publico: Map<String, Value>) {
        self.con(|x| {
            let o = x.as_object_mut().expect("objeto");
            let p = o.entry("publico").or_insert_with(|| json!({}));
            if let Some(p) = p.as_object_mut() {
                p.insert("preguntas".into(), preguntas);
                p.extend(publico);
                p.remove("visto");
            }
            o.insert("estado".into(), json!("esperando"));
            o.insert("fin".into(), json!(ahora()));
            o.insert("error".into(), json!(""));
            o.insert("leyendo".into(), json!(""));
            o.remove("error_ia");
        });
        let _ = self.guardar(true);
        self.latiendo.store(false, Ordering::SeqCst);
    }

    /// Vuelve a correr (después de responder, «Seguir» o «Reintentar»).
    pub fn seguir(&self) {
        self.con(|x| {
            let o = x.as_object_mut().expect("objeto");
            o.insert("estado".into(), json!("corriendo"));
            o.insert("error".into(), json!(""));
            o.insert("latido".into(), json!(segundos()));
            o.remove("error_ia");
            o.remove("fin");
            if let Some(p) = o.get_mut("publico").and_then(Value::as_object_mut) {
                p.remove("preguntas");
            }
        });
        let _ = self.guardar(true);
    }

    /// Crea o cambia un ítem de la lista visible (`{ruta, titulo, tipo, estado, error?}`).
    pub fn poner_item(&self, ruta: &str, mut campos: Map<String, Value>, fallo: Option<Fallo>) {
        let tiene_error = fallo.is_some();
        if let Some(f) = fallo {
            let (t, ia) = texto_error(Some(f));
            campos.insert("error".into(), json!(t));
            if let Some(ia) = ia {
                campos.insert("error_ia".into(), ia);
            }
        }
        self.con(|x| {
            let items = x["items"].as_array_mut().expect("items");
            let k = match items.iter().position(|i| i.get("ruta") == Some(&json!(ruta))) {
                Some(k) => k,
                None => {
                    items.push(json!({"ruta": ruta}));
                    items.len() - 1
                }
            };
            let i = items[k].as_object_mut().expect("ítem");
            let estado = campos.get("estado").and_then(Value::as_str).unwrap_or("");
            if !tiene_error && matches!(estado, "escribiendo" | "listo" | "cola") {
                i.remove("error");
                i.remove("error_ia");
            }
            i.extend(campos);
        });
        let _ = self.guardar(true);
    }

    /// La IA está leyendo `ruta`: cuenta y avisa, sin guardar todo el estado cada vez (lo guarda el latido).
    pub fn leyo(&self, ruta: &str) {
        let (id, n) = self.con(|x| {
            let o = x.as_object_mut().expect("objeto");
            let vistos = o.entry("vistos").or_insert_with(|| json!([])).as_array_mut().expect("vistos");
            if !vistos.contains(&json!(ruta)) && vistos.len() < 5000 {
                vistos.push(json!(ruta));
            }
            let n = vistos.len();
            o.insert("leidos".into(), json!(n));
            o.insert("leyendo".into(), json!(ruta));
            (o["id"].as_str().unwrap_or("").to_string(), n)
        });
        (self.emitir)(json!({"t": "lee", "id": id, "ruta": ruta, "n": n}));
    }

    pub fn busco(&self, patron: &str) {
        (self.emitir)(json!({"t": "busca", "id": self.id(), "patron": patron.chars().take(200).collect::<String>()}));
    }

    pub fn ruta_detener(&self) -> PathBuf {
        self.carpeta.join(format!("{}.detener", self.id()))
    }

    /// Si la persona pidió detenerlo (se le pasa a la IA como `detener`).
    pub fn detenido(&self) -> bool {
        self.ruta_detener().exists()
    }

    /// Un hilo que actualiza el latido (y guarda lo leído) mientras el trabajo corre.
    pub fn latir(self: &Arc<Self>) {
        self.latiendo.store(true, Ordering::SeqCst);
        let t = Arc::downgrade(self);
        let vivo = self.latiendo.clone();
        thread::spawn(move || {
            while vivo.load(Ordering::SeqCst) {
                let Some(t) = t.upgrade() else { break };
                t.con(|x| x["latido"] = json!(segundos()));
                let _ = t.guardar(false);
                drop(t);
                thread::sleep(LATIDO);
            }
        });
    }

    /// Lo que ve la interfaz.
    pub fn vista(&self) -> Value {
        self.con(|x| {
            let mut v = json!({"id": x["id"], "tipo": x["tipo"], "carpeta": x["proyecto"], "estado": estado_real(x), "etapa": x["etapa"],
                "etapas": x["etapas"], "hechas": x["hechas"], "inicio": x["inicio"], "fin": x.get("fin").cloned().unwrap_or(Value::Null),
                "items": x["items"], "leidos": x.get("leidos").cloned().unwrap_or(json!(0)), "leyendo": x.get("leyendo").cloned().unwrap_or(json!("")),
                "error": x.get("error").cloned().unwrap_or(json!(""))});
            if let Some(e) = x.get("error_ia") {
                v["error_ia"] = e.clone();
            }
            if let Some(p) = x.get("publico").and_then(Value::as_object) {
                for (k, val) in p {
                    v[k] = val.clone();
                }
            }
            v
        })
    }
}

fn espacios(s: &str) -> String {
    s.split_whitespace().collect::<Vec<_>>().join(" ")
}

/// Las preguntas para la persona, validadas: [{id, pregunta, porque, opciones}]. Lo que no sirve se descarta.
pub fn limpiar_preguntas(lista: &Value, prefijo: &str, maximo: usize) -> Value {
    let mut r: Vec<Value> = vec![];
    for p in lista.as_array().into_iter().flatten() {
        let Some(pregunta) = p.get("pregunta").and_then(Value::as_str).map(espacios).filter(|s| !s.is_empty()) else { continue };
        let mut opciones: Vec<String> = vec![];
        for o in p.get("opciones").and_then(Value::as_array).into_iter().flatten().filter_map(Value::as_str) {
            let o: String = espacios(o).chars().take(100).collect();
            if !o.is_empty() && !opciones.contains(&o) && opciones.len() < 5 {
                opciones.push(o);
            }
        }
        let porque: String = espacios(p.get("porque").and_then(Value::as_str).unwrap_or("")).chars().take(200).collect();
        r.push(json!({"id": format!("{prefijo}-{}", r.len() + 1), "pregunta": pregunta.chars().take(300).collect::<String>(),
            "porque": porque, "opciones": opciones}));
        if r.len() >= maximo {
            break;
        }
    }
    json!(r)
}

/// Lo que respondió la persona, contra las preguntas hechas: {id: {respuesta, nose, saltada}}. Lo desconocido se ignora.
pub fn limpiar_respuestas(respuestas: &Value, preguntas: &Value) -> Value {
    let ids: Vec<String> = preguntas.as_array().into_iter().flatten().filter_map(|p| p.get("id").and_then(Value::as_str)).map(String::from).collect();
    let mut r = Map::new();
    for x in respuestas.as_array().into_iter().flatten() {
        let Some(id) = x.get("id").and_then(Value::as_str).filter(|i| ids.iter().any(|j| j == i)) else { continue };
        let texto: String = espacios(&match x.get("respuesta") {
            Some(Value::String(s)) => s.clone(),
            Some(Value::Null) | None => String::new(),
            Some(v) => v.to_string(),
        }).chars().take(1000).collect();
        let nose = x.get("nose").and_then(Value::as_bool).unwrap_or(false) && texto.is_empty();
        let saltada = texto.is_empty() && !x.get("nose").and_then(Value::as_bool).unwrap_or(false);
        r.insert(id.into(), json!({"respuesta": texto, "nose": nose, "saltada": saltada}));
    }
    for i in ids {
        r.entry(i).or_insert_with(|| json!({"respuesta": "", "nose": false, "saltada": true}));
    }
    Value::Object(r)
}

#[cfg(test)]
mod pruebas {
    use super::*;

    fn trabajos() -> (Trabajos, PathBuf, Arc<Mutex<Vec<Value>>>) {
        let dir = std::env::temp_dir().join(format!("trabajos-prueba-{}", hex(10)));
        let vistos = Arc::new(Mutex::new(vec![]));
        let v = vistos.clone();
        (Trabajos::nuevos(&dir, Arc::new(move |e| v.lock().unwrap().push(e))), dir, vistos)
    }

    #[test]
    fn fechas_civiles() {
        assert_eq!(fecha_utc(0), (1970, 1, 1, 0, 0, 0));
        assert_eq!(fecha_utc(1_762_800_000), (2025, 11, 10, 18, 40, 0));
        assert_eq!(fecha_utc(951_782_400), (2000, 2, 29, 0, 0, 0));
    }

    #[test]
    fn un_trabajo_de_punta_a_punta() {
        let (ts, dir, eventos) = trabajos();
        let t = ts.crear("resumir", "/ana/notas", &["leer", "escribir"], json!({"n": 1})).unwrap();
        assert!(id_valido(&t.id()));
        t.leyo("a.md");
        t.leyo("a.md");
        t.busco("atr");
        t.etapa("escribir");
        t.poner_item("a.md", json!({"titulo": "A", "estado": "escribiendo"}).as_object().unwrap().clone(), None);
        t.terminar("error", Some(Fallo::Ia(json!({"codigo": "demora", "plantilla": "{ia} se demoró.", "valores": {"ia": "Claude", "n": 3}}))));
        let v = ts.ver(&t.id()).unwrap()["trabajo"].clone();
        assert_eq!(v["estado"], "error");
        assert_eq!(v["error"], "Claude se demoró.");
        assert_eq!(v["error_ia"]["valores"]["n"], "3");
        assert_eq!(v["hechas"], json!(["leer"]));
        assert_eq!(v["leidos"], 1);
        assert_eq!(v["items"][0]["estado"], "cola", "lo que quedó escribiendo vuelve a la cola");
        let e = eventos.lock().unwrap();
        assert!(e.iter().any(|x| x["t"] == "lee" && x["n"] == 1));
        assert!(e.iter().any(|x| x["t"] == "busca" && x["patron"] == "atr"));
        assert_eq!(ts.del_proyecto("/ana/notas", &["resumir"]).map(|t| t.id()), Some(t.id()));
        assert!(ts.del_proyecto("/ana/notas", &["otro"]).is_none());
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let m = fs::metadata(dir.join("trabajos").join(format!("{}.json", t.id()))).unwrap().permissions().mode() & 0o777;
            assert_eq!(m, 0o600);
        }
        let _ = fs::remove_dir_all(dir);
    }

    #[test]
    fn detener_esperar_y_seguir() {
        let (ts, dir, _) = trabajos();
        let t = ts.crear("plan", "/p", &["a"], json!({})).unwrap();
        assert!(!t.detenido());
        assert_eq!(ts.detener(&t.id()).unwrap()["deteniendo"], true);
        assert!(t.detenido());
        t.terminar("detenido", None);
        assert!(!t.detenido(), "la marca se borra al terminar");
        let preguntas = limpiar_preguntas(&json!([{"pregunta": "  ¿Para  quién? ", "opciones": ["Ana", "Ana", "Matías"]}, {"pregunta": ""}, "x"]), "p", 5);
        assert_eq!(preguntas, json!([{"id": "p-1", "pregunta": "¿Para quién?", "porque": "", "opciones": ["Ana", "Matías"]}]));
        t.esperar(preguntas.clone(), Map::new());
        assert_eq!(ts.esperando("/p").len(), 1);
        let r = limpiar_respuestas(&json!([{"id": "p-1", "respuesta": " Ana "}, {"id": "otra", "respuesta": "x"}]), &preguntas);
        assert_eq!(r, json!({"p-1": {"respuesta": "Ana", "nose": false, "saltada": false}}));
        t.seguir();
        assert_eq!(t.estado(), "corriendo");
        assert!(t.vista().get("preguntas").is_none());
        let _ = fs::remove_dir_all(dir);
    }

    #[test]
    fn sin_latido_queda_interrumpido() {
        assert_eq!(estado_real(&json!({"estado": "corriendo", "latido": segundos() - 100.0})), "interrumpido");
        assert_eq!(estado_real(&json!({"estado": "corriendo", "latido": segundos()})), "corriendo");
        assert_eq!(estado_real(&json!({"estado": "listo", "latido": 0})), "listo");
        assert!(!id_valido("../x") && !id_valido("20261110T120000-zzzzzz"));
    }
}
