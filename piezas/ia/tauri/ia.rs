// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.
//! Pieza «ia» en Rust: la IA de la persona (Claude Code, Codex o Gemini) con SU propia cuenta. Solo `regex` y `serde_json`.
//!
//! Es la misma pieza que `python/ia.py`, con las mismas protecciones, en Rust (las apps de Pieza son Rust + Tauri):
//! - La IA corre en una carpeta temporal vacía, sin herramientas ni servidores MCP y sin la memoria de la persona.
//! - El pedido NUNCA va como argumento del proceso: va por la entrada estándar o en un archivo de la carpeta temporal.
//! - Material opcional (fotos, PDF): se copia a la carpeta temporal y la IA solo puede leer esas copias.
//! - Leer una carpeta (solo lectura, nunca los secretos) o escribir en una carpeta (solo ahí, sin terminal ni internet).
//! - Nunca se quitan protecciones para que un CLI viejo funcione: se pregunta antes qué conoce (`soporta`).
//! - La IA no recibe las variables de entorno de la app (`<PREFIJO>_*`).
//! - Los errores salen como código + plantilla + valores, para que la interfaz los traduzca.
//! - En vivo (`preguntar_vivo`): qué lee, busca y escribe la IA, cuántos tokens usa, y se puede detener.
//!
//! Uso:
//! ```ignore
//! let ia = Ia::nueva(Contexto { app_id: "pieza".into(), app_nombre: "Pieza".into(), prefijo: "PIEZA".into(),
//!                               datos: carpeta_datos, ayuda: String::new() });
//! let texto = ia.preguntar("Hola", &Opciones::de("claude"))?;
//! ```

use regex::Regex;
use serde_json::{json, Map, Value};
use std::collections::{HashMap, HashSet};
use std::ffi::OsString;
use std::fs;
use std::io::{BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::mpsc;
use std::sync::{Mutex, Once, OnceLock};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

/// id → (comandos posibles, nombre visible). Gemini: Antigravity CLI (`agy`) o el Gemini CLI.
pub const IAS: [(&str, &[&str], &str); 3] =
    [("claude", &["claude"], "Claude"), ("codex", &["codex"], "ChatGPT (Codex)"), ("gemini", &["agy", "gemini"], "Gemini")];
const IMAGENES: [&str; 6] = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic"];
/// Claude Code carga la memoria de la persona (CLAUDE.md, memoria automática) aunque corra sin herramientas: esto lo apaga.
const SIN_MEMORIA_CLAUDE: [(&str, &str); 2] = [("CLAUDE_CODE_DISABLE_CLAUDE_MDS", "1"), ("CLAUDE_CODE_DISABLE_AUTO_MEMORY", "1")];
/// Lo que nunca puede hacer la IA, ni siquiera en revisión a fondo.
const PROHIBIDO: [&str; 8] = ["Bash", "Edit", "Write", "MultiEdit", "NotebookEdit", "WebFetch", "WebSearch", "Task"];
/// Lo que sí puede usar Claude al escribir (y nada más: ni terminal, ni internet, ni subagentes).
const ESCRIBE_CLAUDE: [&str; 6] = ["Read", "Glob", "Grep", "Edit", "Write", "MultiEdit"];
/// Herramientas que Claude Code ya no trae desde esa versión (solo se quitan si el CLI conoce --tools).
const RETIRADAS: [(&str, (u32, u32, u32)); 1] = [("MultiEdit", (2, 1, 0))];
/// Errores que la persona arregla en la app: a estos se les suma la «ayuda» de app.json.
const CON_AYUDA: [&str; 2] = ["no_instalada", "actualizar"];
const INSTRUCCION_ARCHIVO: &str = "Lee el archivo instrucciones.md de esta carpeta (y el material que menciona) y haz exactamente lo que \
    pide. Entrega solo el resultado pedido, sin comentarios. No modifiques ni crees archivos.";
const LEE_CODEX: [&str; 8] = ["cat", "sed", "head", "tail", "nl", "less", "bat", "wc"];
const BUSCA_CODEX: [&str; 6] = ["rg", "grep", "find", "ls", "fd", "git"];

/// Texto de cada error (la clave de traducción es el texto en español; {ia}, {detalle} y {app} se reemplazan en la interfaz).
pub fn plantilla(codigo: &str) -> &'static str {
    match codigo {
        "no_instalada" => "No encontré {ia} en este computador.",
        "demora" => "{ia} se demoró demasiado en responder. Inténtalo de nuevo.",
        "sin_respuesta" => "{ia} no respondió. {detalle}",
        "sin_respuesta_corta" => "{ia} no respondió.",
        "actualizar" => "Actualiza {ia} para usarla con {app}: tu versión no conoce las protecciones que necesitamos.",
        "detenido" => "Detuviste a {ia}.",
        _ => "No conozco esa IA.",
    }
}

/// Lo que la pieza necesita saber de la app (en host-tauri sale de `enchufe::App` y de la carpeta de datos).
#[derive(Clone, Debug)]
pub struct Contexto {
    pub app_id: String,
    pub app_nombre: String,
    /// Prefijo de las variables de la app (`ALCANCIA`): la IA nunca recibe `ALCANCIA_*`.
    pub prefijo: String,
    /// Carpeta de datos de la app: ahí se recuerda qué herramientas no conoce cada versión de Claude.
    pub datos: PathBuf,
    /// `app.json` → `"ia": {"ayuda": "Revisa en Ajustes → Tu IA."}` (o vacío).
    pub ayuda: String,
}

/// Un error de la IA: la interfaz hace `Tp(plantilla, valores)`; `frase()` lo da en español para registros.
#[derive(Clone, Debug, PartialEq)]
pub struct ErrorIa {
    pub codigo: String,
    pub plantilla: String,
    pub valores: Map<String, Value>,
    pub ayuda: Option<String>,
}

impl ErrorIa {
    pub fn json(&self) -> Value {
        let mut m = json!({"codigo": self.codigo, "plantilla": self.plantilla, "valores": self.valores});
        if let Some(a) = &self.ayuda {
            m["ayuda"] = json!(a);
        }
        m
    }
    pub fn frase(&self) -> String {
        let mut t = self.plantilla.clone();
        for (k, v) in &self.valores {
            t = t.replace(&format!("{{{k}}}"), v.as_str().unwrap_or(""));
        }
        format!("{} {}", t.trim(), self.ayuda.as_deref().unwrap_or("")).trim().to_string()
    }
    /// Si la persona (o quien llama, con `detener`) cortó la IA: no es una falla.
    pub fn detenido(&self) -> bool {
        self.codigo == "detenido"
    }
}

/// Lo que la IA va haciendo, en vivo.
#[derive(Clone, Debug, PartialEq)]
pub enum Evento {
    Lee { ruta: String },
    Escribe { ruta: String },
    Busca { patron: String, ruta: Option<String> },
    /// Tokens que la IA dice haber usado: «entrada» lo nuevo que leyó, «cache» lo que reusó, «salida» lo que escribió.
    Uso { entrada: u64, cache: u64, salida: u64 },
}

impl Evento {
    pub fn json(&self) -> Value {
        match self {
            Evento::Lee { ruta } => json!({"t": "lee", "ruta": ruta}),
            Evento::Escribe { ruta } => json!({"t": "escribe", "ruta": ruta}),
            Evento::Busca { patron, ruta: Some(r) } => json!({"t": "busca", "patron": patron, "ruta": r}),
            Evento::Busca { patron, ruta: None } => json!({"t": "busca", "patron": patron}),
            Evento::Uso { entrada, cache, salida } => json!({"t": "uso", "entrada": entrada, "cache": cache, "salida": salida}),
        }
    }
}

/// Cómo correr una pregunta.
#[derive(Clone, Debug)]
pub struct Opciones {
    /// claude, codex o gemini.
    pub ia: String,
    pub timeout: Duration,
    /// Material que la IA puede leer (se copia a la carpeta temporal como material-N.ext).
    pub archivos: Vec<PathBuf>,
    /// Una carpeta que la IA puede LEER entera, nunca lo de `no_leer`. Se ignora si la IA no sabe leer.
    pub leer: Option<PathBuf>,
    pub no_leer: Vec<String>,
    pub modelo: Option<String>,
    /// Una carpeta donde la IA puede EDITAR archivos (solo ahí, sin terminal). Antes, `puede_escribir()`.
    pub escribir: Option<PathBuf>,
}

impl Opciones {
    pub fn de(ia: &str) -> Self {
        Opciones { ia: ia.into(), timeout: Duration::from_secs(600), archivos: vec![], leer: None, no_leer: vec![], modelo: None, escribir: None }
    }
}

#[derive(Debug)]
enum Falla {
    NoInstalada,
    VersionVieja,
    Otra(String),
}

/// Lo armado para correr la IA: comando, entrada, entorno, archivo de salida y formato de lo que imprime.
#[derive(Debug, Clone, PartialEq)]
pub struct Armado {
    pub cmd: Vec<OsString>,
    pub entrada: Option<String>,
    pub env: Vec<(OsString, OsString)>,
    pub salida: Option<PathBuf>,
    /// "texto", "claude-json" o "codex-json".
    pub formato: &'static str,
    pub comando: PathBuf,
}

type Version = (u32, u32, u32);

pub struct Ia {
    ctx: Contexto,
    ayudas: Mutex<HashMap<(PathBuf, String), String>>,
    versiones: Mutex<HashMap<PathBuf, Option<Version>>>,
    desconocidas: Mutex<HashMap<PathBuf, HashSet<String>>>,
}

static PATH: Once = Once::new();

/// Las apps no heredan el PATH de la terminal: suma donde suelen quedar los CLI de IA (Mac, Linux y Windows).
pub fn preparar_path() {
    PATH.call_once(|| {
        let casa = casa();
        let mut extra: Vec<PathBuf> = [".local/bin", ".claude/local", ".npm-global/bin", ".volta/bin", ".bun/bin", ".codex/bin"]
            .iter()
            .map(|r| casa.join(r))
            .chain(["/opt/homebrew/bin", "/usr/local/bin"].iter().map(PathBuf::from))
            .collect();
        let nvm = casa.join(".nvm/versions/node");
        if let Ok(d) = fs::read_dir(&nvm) {
            let mut vs: Vec<PathBuf> = d.flatten().map(|e| e.path().join("bin")).collect();
            vs.sort();
            vs.reverse();
            extra.extend(vs);
        }
        if cfg!(windows) {
            if let Some(a) = std::env::var_os("APPDATA") {
                extra.push(PathBuf::from(a).join("npm"));
            }
            if let Some(a) = std::env::var_os("LOCALAPPDATA") {
                extra.push(PathBuf::from(a).join("Programs").join("claude"));
            }
        }
        let actual: Vec<PathBuf> = std::env::var_os("PATH").map(|p| std::env::split_paths(&p).collect()).unwrap_or_default();
        let mut todas = actual.clone();
        for d in extra {
            if d.is_dir() && !actual.contains(&d) {
                todas.push(d);
            }
        }
        if let Ok(p) = std::env::join_paths(todas) {
            std::env::set_var("PATH", p);
        }
    });
}

fn casa() -> PathBuf {
    std::env::var_os(if cfg!(windows) { "USERPROFILE" } else { "HOME" }).map(PathBuf::from).unwrap_or_default()
}

/// Un ejecutable en el PATH (con PATHEXT en Windows).
pub fn buscar(nombre: &str) -> Option<PathBuf> {
    let path = std::env::var_os("PATH")?;
    let exts: Vec<String> = if cfg!(windows) {
        std::env::var("PATHEXT").unwrap_or_else(|_| ".EXE;.CMD;.BAT".into()).split(';').map(|e| e.to_lowercase()).collect()
    } else {
        vec![String::new()]
    };
    for d in std::env::split_paths(&path) {
        for e in &exts {
            let p = d.join(format!("{nombre}{e}"));
            if es_ejecutable(&p) {
                return Some(p);
            }
        }
    }
    None
}

fn es_ejecutable(p: &Path) -> bool {
    let Ok(m) = fs::metadata(p) else { return false };
    if !m.is_file() {
        return false;
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        m.permissions().mode() & 0o111 != 0
    }
    #[cfg(not(unix))]
    true
}

fn info(ia: &str) -> Option<(&'static [&'static str], &'static str)> {
    IAS.iter().find(|x| x.0 == ia).map(|x| (x.1, x.2))
}

/// El nombre visible de una IA («Claude»).
pub fn nombre(ia: &str) -> &'static str {
    info(ia).map(|x| x.1).unwrap_or("IA")
}

/// Dónde está el CLI de esa IA, si está.
pub fn comando(ia: &str) -> Option<PathBuf> {
    preparar_path();
    info(ia)?.0.iter().find_map(|c| buscar(c))
}

/// Las tres IA, con si están instaladas.
pub fn lista() -> Vec<Value> {
    IAS.iter().map(|(id, _, n)| json!({"id": id, "nombre": n, "instalada": comando(id).is_some()})).collect()
}

fn es_agy(cmd: &Path) -> bool {
    let n = cmd.file_name().and_then(|n| n.to_str()).unwrap_or("").to_lowercase();
    matches!(n.split('.').next().unwrap_or(""), "agy" | "antigravity")
}

/// Si la IA sabe leer una carpeta con permisos de solo lectura (material o revisión a fondo).
pub fn puede_leer(ia: &str) -> bool {
    ia != "gemini" || comando(ia).is_some_and(|c| es_agy(&c))
}

/// Si la IA sabe editar archivos limitada a una carpeta (`escribir`): Claude y Codex.
pub fn puede_escribir(ia: &str) -> bool {
    matches!(ia, "claude" | "codex") && comando(ia).is_some()
}

fn numero(v: &Value) -> u64 {
    v.as_u64().filter(|n| *n < 10_000_000_000).unwrap_or(0)
}

/// Los tokens que dice el CLI → `Evento::Uso`. Claude da el total al final; Codex, uno por turno (se suman afuera).
fn uso(u: &Value) -> Option<Evento> {
    let u = u.as_object()?;
    let n = |k: &str| u.get(k).map(numero).unwrap_or(0);
    let mut entrada = n("input_tokens") + n("cache_creation_input_tokens");
    let cache = n("cache_read_input_tokens") + n("cached_input_tokens");
    if u.contains_key("cached_input_tokens") {
        entrada = entrada.saturating_sub(n("cached_input_tokens")); // en Codex, input_tokens ya incluye lo de la caché
    }
    let salida = n("output_tokens");
    (entrada > 0 || cache > 0 || salida > 0).then_some(Evento::Uso { entrada, cache, salida })
}

fn corto(s: &str, n: usize) -> String {
    s.chars().take(n).collect()
}

/// Una línea de `claude -p --output-format stream-json --verbose`. Devuelve Some((texto, es_error)) si es la final.
pub fn evento_claude(linea: &str, al_evento: &mut dyn FnMut(Evento)) -> Option<(String, bool)> {
    let x: Value = serde_json::from_str(linea).ok()?;
    let x = x.as_object()?;
    match x.get("type").and_then(Value::as_str) {
        Some("result") => {
            if let Some(e) = x.get("usage").and_then(uso) {
                al_evento(e);
            }
            let texto = match x.get("result") {
                Some(Value::String(s)) => s.clone(),
                Some(Value::Null) | None => String::new(),
                Some(v) => v.to_string(),
            };
            Some((texto, x.get("is_error").and_then(Value::as_bool).unwrap_or(false)))
        }
        Some("assistant") => {
            for c in x.get("message").and_then(|m| m.get("content")).and_then(Value::as_array).into_iter().flatten() {
                if c.get("type").and_then(Value::as_str) != Some("tool_use") {
                    continue;
                }
                let (Some(h), Some(e)) = (c.get("name").and_then(Value::as_str), c.get("input").and_then(Value::as_object)) else { continue };
                let txt = |k: &str| e.get(k).and_then(Value::as_str);
                match h {
                    "Read" => {
                        if let Some(r) = txt("file_path") {
                            al_evento(Evento::Lee { ruta: corto(r, 1000) });
                        }
                    }
                    "Edit" | "Write" | "MultiEdit" => {
                        if let Some(r) = txt("file_path") {
                            al_evento(Evento::Escribe { ruta: corto(r, 1000) });
                        }
                    }
                    "Glob" | "Grep" => {
                        if let Some(p) = txt("pattern") {
                            al_evento(Evento::Busca { patron: corto(p, 200), ruta: txt("path").map(|r| corto(r, 1000)) });
                        }
                    }
                    _ => {}
                }
            }
            None
        }
        _ => None,
    }
}

/// Una línea de `codex exec --json` (JSONL). Los formatos cambian entre versiones: se busca un comando en lo que venga.
pub fn evento_codex(linea: &str, al_evento: &mut dyn FnMut(Evento)) {
    let Ok(x) = serde_json::from_str::<Value>(linea) else { return };
    let Some(xo) = x.as_object() else { return };
    let tipo = xo.get("type").and_then(Value::as_str).unwrap_or("");
    if tipo == "turn.completed" {
        if let Some(e) = xo.get("usage").and_then(uso) {
            al_evento(e);
        }
        return;
    }
    let item = xo.get("item").filter(|v| v.is_object()).or_else(|| xo.get("msg").filter(|v| v.is_object())).unwrap_or(&x);
    let tipo_item = item.get("type").and_then(Value::as_str).unwrap_or("");
    if matches!(if tipo.is_empty() { tipo_item } else { tipo }, "item.completed" | "exec_command_end") {
        return;
    }
    match item.get("changes") {
        Some(Value::Array(cs)) => {
            for ch in cs.iter().take(50) {
                if let Some(r) = ch.get("path").and_then(Value::as_str) {
                    al_evento(Evento::Escribe { ruta: corto(r, 1000) });
                }
            }
            return;
        }
        Some(Value::Object(cs)) => {
            for r in cs.keys().take(50) {
                al_evento(Evento::Escribe { ruta: corto(r, 1000) });
            }
            return;
        }
        _ => {}
    }
    let mut partes: Vec<String> = match item.get("command") {
        Some(Value::Array(a)) => a.iter().map(|p| p.as_str().map(String::from).unwrap_or_else(|| p.to_string())).collect(),
        Some(Value::String(s)) => s.split_whitespace().map(String::from).collect(),
        _ => return,
    };
    let base = |p: &str| Path::new(p).file_name().and_then(|n| n.to_str()).unwrap_or(p).to_string();
    if partes.len() >= 3 && matches!(base(&partes[0]).as_str(), "bash" | "sh" | "zsh") && matches!(partes[1].as_str(), "-lc" | "-c") {
        partes = partes[2..].join(" ").trim_matches(|c| c == '\'' || c == '"').split_whitespace().map(String::from).collect();
    }
    let Some(primero) = partes.first() else { return };
    let prog = base(primero);
    let rutas: Vec<String> = partes[1..]
        .iter()
        .filter(|p| !p.starts_with('-') && (p.contains('/') || p.contains('.')))
        .map(|p| p.trim_matches(|c| c == '\'' || c == '"').to_string())
        .collect();
    if LEE_CODEX.contains(&prog.as_str()) && !rutas.is_empty() {
        al_evento(Evento::Lee { ruta: corto(rutas.last().unwrap(), 1000) });
    } else if BUSCA_CODEX.contains(&prog.as_str()) {
        al_evento(Evento::Busca { patron: corto(&partes[1..].join(" "), 200), ruta: None });
    }
}

/// Una carpeta temporal privada que se borra sola.
struct Temporal(PathBuf);

impl Temporal {
    fn nueva(prefijo: &str) -> std::io::Result<Self> {
        let semilla = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0);
        for k in 0..20u32 {
            let h = {
                use std::hash::{BuildHasher, Hasher};
                let mut x = std::collections::hash_map::RandomState::new().build_hasher();
                x.write_u128(semilla);
                x.write_u32(k);
                x.finish()
            };
            let p = std::env::temp_dir().join(format!("{prefijo}-ia-{h:016x}"));
            #[cfg(unix)]
            let b = {
                use std::os::unix::fs::DirBuilderExt;
                let mut b = fs::DirBuilder::new();
                b.mode(0o700);
                b
            };
            #[cfg(not(unix))]
            let b = fs::DirBuilder::new();
            match b.create(&p) {
                Ok(()) => return Ok(Temporal(p)),
                Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => continue,
                Err(e) => return Err(e),
            }
        }
        Err(std::io::Error::other("sin carpeta temporal"))
    }
}

impl Drop for Temporal {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn sin_avisos(texto: &str) -> Vec<String> {
    texto.lines().map(str::trim).filter(|l| !l.is_empty() && !l.contains("Permission deny rule")).map(String::from).collect()
}

fn regex_opcion(opcion: &str) -> Regex {
    // Sin «lookbehind» en `regex`: la opción no puede venir pegada a letras, números o guiones a ningún lado.
    Regex::new(&format!(r"(?:^|[^\w-]){}(?:$|[^\w-])", regex::escape(opcion))).expect("regex")
}

impl Ia {
    pub fn nueva(ctx: Contexto) -> Self {
        preparar_path();
        Ia { ctx, ayudas: Mutex::default(), versiones: Mutex::default(), desconocidas: Mutex::default() }
    }

    pub fn contexto(&self) -> &Contexto {
        &self.ctx
    }

    /// La IA no recibe las variables de la app (rutas, credenciales, modos de prueba): solo lo necesario para correr.
    fn entorno(&self) -> Vec<(OsString, OsString)> {
        let p = format!("{}_", self.ctx.prefijo.to_uppercase());
        std::env::vars_os().filter(|(k, _)| !k.to_string_lossy().to_uppercase().starts_with(&p)).collect()
    }

    fn texto_de(&self, cmd: &Path, args: &[&str]) -> String {
        let clave = (cmd.to_path_buf(), format!("{}|{}", args.join(" "), huella(cmd)));
        if let Some(t) = self.ayudas.lock().unwrap_or_else(|e| e.into_inner()).get(&clave) {
            return t.clone();
        }
        let t = correr_corto(cmd, args, &self.entorno(), Duration::from_secs(20));
        self.ayudas.lock().unwrap_or_else(|e| e.into_inner()).insert(clave, t.clone());
        t
    }

    /// Si el CLI conoce una opción (se pregunta una vez por versión del comando; nunca se reintenta quitando protecciones).
    pub fn soporta(&self, cmd: &Path, opcion: &str) -> bool {
        regex_opcion(opcion).is_match(&self.texto_de(cmd, &["--help"]))
    }

    fn conoce_ayuda(&self, cmd: &Path) -> bool {
        !self.texto_de(cmd, &["--help"]).is_empty()
    }

    fn codex_json(&self, cmd: &Path) -> bool {
        regex_opcion("--json").is_match(&self.texto_de(cmd, &["exec", "--help"]))
    }

    fn version(&self, cmd: &Path) -> Option<(u32, u32, u32)> {
        if let Some(v) = self.versiones.lock().unwrap_or_else(|e| e.into_inner()).get(cmd) {
            return *v;
        }
        static RE: OnceLock<Regex> = OnceLock::new();
        let re = RE.get_or_init(|| Regex::new(r"(\d+)\.(\d+)\.(\d+)").expect("regex"));
        let t = correr_corto(cmd, &["--version"], &self.entorno(), Duration::from_secs(20));
        let v = re.captures(&t).and_then(|c| Some((c[1].parse().ok()?, c[2].parse().ok()?, c[3].parse().ok()?)));
        self.versiones.lock().unwrap_or_else(|e| e.into_inner()).insert(cmd.to_path_buf(), v);
        v
    }

    fn archivo_desconocidas(&self) -> PathBuf {
        self.ctx.datos.join("ia-herramientas.json")
    }

    fn clave_version(&self, cmd: &Path, v: Option<(u32, u32, u32)>) -> String {
        let n = cmd.file_name().and_then(|n| n.to_str()).unwrap_or("?");
        match v {
            Some((a, b, c)) => format!("{n}@{a}.{b}.{c}"),
            None => format!("{n}@?"),
        }
    }

    /// Lo que nunca puede hacer Claude, sin las herramientas que su versión no conoce (solo si el CLI conoce --tools).
    fn prohibido(&self, cmd: &Path) -> Vec<&'static str> {
        if !self.soporta(cmd, "--tools") {
            return PROHIBIDO.to_vec();
        }
        let v = self.version(cmd);
        let mut fuera: HashSet<String> = RETIRADAS.iter().filter(|(_, desde)| v.is_some_and(|v| v >= *desde)).map(|(h, _)| h.to_string()).collect();
        if let Some(Value::Array(a)) = leer_json(&self.archivo_desconocidas(), 64 * 1024).and_then(|d| d.get(self.clave_version(cmd, v)).cloned()) {
            fuera.extend(a.iter().filter_map(Value::as_str).filter(|h| PROHIBIDO.contains(h)).map(String::from));
        }
        if let Some(s) = self.desconocidas.lock().unwrap_or_else(|e| e.into_inner()).get(cmd) {
            fuera.extend(s.iter().cloned());
        }
        PROHIBIDO.iter().copied().filter(|h| !fuera.contains(*h)).collect()
    }

    /// Si Claude avisó que no conoce una herramienta prohibida, la próxima vez no se le pide.
    fn aprender(&self, cmd: &Path, stderr: &str) {
        static RE: OnceLock<Regex> = OnceLock::new();
        let re = RE.get_or_init(|| Regex::new(r#"Permission deny rule "([A-Za-z]+)" matches no known tool"#).expect("regex"));
        let nuevas: HashSet<String> = re.captures_iter(stderr).map(|c| c[1].to_string()).filter(|h| PROHIBIDO.contains(&h.as_str())).collect();
        if nuevas.is_empty() {
            return;
        }
        self.desconocidas.lock().unwrap_or_else(|e| e.into_inner()).entry(cmd.to_path_buf()).or_default().extend(nuevas.iter().cloned());
        if !self.soporta(cmd, "--tools") {
            return;
        }
        let Some(v) = self.version(cmd) else { return };
        let clave = self.clave_version(cmd, Some(v));
        let ruta = self.archivo_desconocidas();
        let mut d = leer_json(&ruta, 64 * 1024).and_then(|d| d.as_object().cloned()).unwrap_or_default();
        let mut todas: Vec<String> = d.get(&clave).and_then(Value::as_array).into_iter().flatten().filter_map(Value::as_str).map(String::from).collect();
        todas.extend(nuevas);
        todas.sort();
        todas.dedup();
        d.insert(clave, json!(todas));
        let n = d.len();
        let d: Map<String, Value> = d.into_iter().skip(n.saturating_sub(20)).collect();
        let _ = escribir_privado(&ruta, &serde_json::to_vec_pretty(&Value::Object(d)).unwrap_or_default());
    }

    fn error(&self, ia: &str, codigo: &str, detalle: &str) -> ErrorIa {
        let mut valores = Map::new();
        valores.insert("ia".into(), json!(nombre(ia)));
        valores.insert("detalle".into(), json!(detalle));
        valores.insert("app".into(), json!(self.ctx.app_nombre));
        let ayuda = self.ayuda();
        ErrorIa {
            codigo: codigo.into(),
            plantilla: plantilla(codigo).into(),
            valores,
            ayuda: (CON_AYUDA.contains(&codigo) && !ayuda.is_empty()).then_some(ayuda),
        }
    }

    fn ayuda(&self) -> String {
        let a = self.ctx.ayuda.trim();
        if a.is_empty() || a.chars().count() > 200 || a.contains(['<', '>', '{', '}']) {
            String::new()
        } else {
            a.to_string()
        }
    }

    /// Cómo correr la IA en la carpeta temporal `tmp`. Las protecciones se arman SOLO aquí.
    fn armar(&self, prompt: &str, o: &Opciones, tmp: &Path, vivo: bool) -> Result<Armado, Falla> {
        let ia = o.ia.as_str();
        let cmd0 = comando(ia).ok_or(Falla::NoInstalada)?;
        let mut leer = o.leer.clone().filter(|l| l.is_dir() && puede_leer(ia));
        let escribir = o.escribir.clone();
        if let Some(e) = &escribir {
            if !(e.is_dir() && puede_escribir(ia)) {
                return Err(Falla::Otra("Esta IA no sabe editar una carpeta: usa puede_escribir() antes.".into()));
            }
            leer = None;
        }
        let entorno = self.entorno();
        let mut copias: Vec<PathBuf> = vec![];
        for (k, a) in o.archivos.iter().enumerate() {
            let ext = a.extension().and_then(|e| e.to_str()).map(|e| format!(".{}", e.to_lowercase())).unwrap_or_default();
            let destino = tmp.join(format!("material-{}{ext}", k + 1));
            if fs::copy(a, &destino).is_ok() {
                copias.push(destino);
            }
        }
        if !copias.is_empty() && !puede_leer(ia) {
            copias.clear();
        }
        // La IA SIEMPRE corre en la carpeta temporal: dentro de la carpeta que revisa, su CLI cargaría la configuración de ese repo.
        let mut prompt = prompt.to_string();
        if let Some(l) = &leer {
            prompt = format!("La carpeta que puedes leer (solo leer) está en: {}\n\n{prompt}", l.display());
        }
        if let Some(e) = &escribir {
            prompt = format!("La carpeta donde trabajas está en: {}\nPuedes leer y editar archivos SOLO ahí. No tienes terminal.\n\n{prompt}", e.display());
        }
        let os = |s: &str| OsString::from(s);
        let mut r = Armado { cmd: vec![], entrada: Some(prompt.clone()), env: entorno, salida: None, formato: "texto", comando: cmd0.clone() };

        if ia == "codex" {
            let salida = tmp.join("respuesta.txt");
            let json_ = vivo && self.codex_json(&cmd0);
            let (modo, donde) = match &escribir {
                Some(e) => ("workspace-write", e.clone()),
                None => ("read-only", tmp.to_path_buf()),
            };
            let mut cmd = vec![cmd0.clone().into_os_string(), os("exec"), os("--skip-git-repo-check"), os("-s"), os(modo), os("-C"),
                donde.into_os_string(), os("-o"), salida.clone().into_os_string()];
            if json_ {
                cmd.push(os("--json"));
            }
            for c in &copias {
                let n = c.to_string_lossy().to_lowercase();
                if IMAGENES.iter().any(|e| n.ends_with(e)) {
                    cmd.extend([os("-i"), c.clone().into_os_string()]);
                }
            }
            if let Some(m) = &o.modelo {
                cmd.extend([os("-m"), os(m)]);
            }
            cmd.push(os("-"));
            r.cmd = cmd;
            r.salida = Some(salida);
            r.formato = if json_ { "codex-json" } else { "texto" };
            return Ok(r);
        }

        if ia == "gemini" && es_agy(&cmd0) {
            // Antigravity no lee la entrada estándar: el pedido va SIEMPRE en un archivo; en -p solo va una frase fija.
            fs::write(tmp.join("instrucciones.md"), &prompt).map_err(|e| Falla::Otra(e.to_string()))?;
            let mut cmd = vec![cmd0.into_os_string(), os("--output-format"), os("text"), os("--sandbox"), os("--add-dir"), tmp.as_os_str().into()];
            if let Some(l) = &leer {
                cmd.extend([os("--add-dir"), l.clone().into_os_string()]);
            }
            if let Some(m) = &o.modelo {
                cmd.extend([os("--model"), os(m)]);
            }
            cmd.extend([os("-p"), os(INSTRUCCION_ARCHIVO)]);
            r.cmd = cmd;
            r.entrada = None;
            return Ok(r);
        }

        if ia == "gemini" {
            let mut cmd = vec![cmd0.into_os_string(), os("-p"), os("Responde a las instrucciones de arriba. Entrega solo el resultado pedido."),
                os("-o"), os("text")];
            if let Some(m) = &o.modelo {
                cmd.extend([os("-m"), os(m)]);
            }
            r.cmd = cmd;
            return Ok(r);
        }

        // Claude Code: sin servidores MCP de la persona y sin su memoria. Las protecciones obligatorias: si el CLI dice que no las
        // conoce, no se corre (se pide actualizarlo).
        for obligatoria in ["--strict-mcp-config", "--disallowedTools"] {
            if !self.soporta(&cmd0, obligatoria) && self.conoce_ayuda(&cmd0) {
                return Err(Falla::VersionVieja);
            }
        }
        let flujo = vivo && self.soporta(&cmd0, "stream-json");
        let mut cmd = vec![cmd0.clone().into_os_string(), os("-p"), os("--output-format")];
        if flujo {
            cmd.extend([os("stream-json"), os("--verbose")]);
        } else {
            cmd.push(os("text"));
        }
        cmd.push(os("--strict-mcp-config"));
        let secretos = sin_secretos(&o.no_leer);
        let prohibido = self.prohibido(&cmd0);
        if let Some(e) = &escribir {
            let permitidas: Vec<&str> =
                ESCRIBE_CLAUDE.iter().copied().filter(|h| prohibido.contains(h) || matches!(*h, "Read" | "Glob" | "Grep")).collect();
            let mut prohibidas: Vec<String> = prohibido.iter().filter(|h| !ESCRIBE_CLAUDE.contains(h)).map(|h| h.to_string()).collect();
            prohibidas.extend(secretos);
            cmd.extend([os("--add-dir"), e.clone().into_os_string(), os("--allowedTools"), os(&permitidas.join(",")),
                os("--disallowedTools"), os(&prohibidas.join(","))]);
            if self.soporta(&cmd0, "--permission-mode") {
                cmd.extend([os("--permission-mode"), os("acceptEdits")]);
            }
            if self.soporta(&cmd0, "--tools") {
                cmd.extend([os("--tools"), os(&permitidas.join(","))]);
            }
        } else if leer.is_some() || !copias.is_empty() {
            if let Some(l) = &leer {
                cmd.extend([os("--add-dir"), l.clone().into_os_string()]);
            }
            let mut prohibidas: Vec<String> = prohibido.iter().map(|h| h.to_string()).collect();
            prohibidas.extend(secretos);
            cmd.extend([os("--allowedTools"), os("Read,Glob,Grep"), os("--disallowedTools"), os(&prohibidas.join(","))]);
            if self.soporta(&cmd0, "--tools") {
                cmd.extend([os("--tools"), os("Read,Glob,Grep")]);
            }
        } else {
            cmd.extend([os("--disallowedTools"), os("*")]);
            if self.soporta(&cmd0, "--tools") {
                cmd.extend([os("--tools"), os("")]);
            }
        }
        if let Some(m) = &o.modelo {
            cmd.extend([os("--model"), os(m)]);
        }
        if self.soporta(&cmd0, "--safe-mode") {
            cmd.push(os("--safe-mode"));
        }
        if self.soporta(&cmd0, "--setting-sources") {
            cmd.extend([os("--setting-sources"), os("user")]); // nunca la configuración (ni los hooks) de un proyecto
        }
        r.env.extend(SIN_MEMORIA_CLAUDE.iter().map(|(k, v)| (os(k), os(v))));
        r.cmd = cmd;
        r.formato = if flujo { "claude-json" } else { "texto" };
        Ok(r)
    }

    /// Para pruebas y para mostrar qué se correría: el comando armado (sin correrlo).
    pub fn armado(&self, prompt: &str, o: &Opciones, tmp: &Path, vivo: bool) -> Result<Armado, String> {
        self.armar(prompt, o, tmp, vivo).map_err(|f| format!("{f:?}"))
    }

    /// Pregunta y espera la respuesta. Ok(texto) o Err(ErrorIa).
    pub fn preguntar(&self, prompt: &str, o: &Opciones) -> Result<String, ErrorIa> {
        self.preguntar_vivo(prompt, o, &mut |_| {}, &|| false)
    }

    /// Como `preguntar`, pero cuenta lo que la IA va haciendo (`al_evento`) y se corta si `detener()` devuelve true
    /// (el error queda con código «detenido»).
    pub fn preguntar_vivo(&self, prompt: &str, o: &Opciones, al_evento: &mut dyn FnMut(Evento), detener: &dyn Fn() -> bool)
        -> Result<String, ErrorIa> {
        let ia = o.ia.as_str();
        if info(ia).is_none() {
            return Err(self.error(ia, "desconocida", ""));
        }
        let tmp = Temporal::nueva(&self.ctx.app_id).map_err(|e| self.error(ia, "sin_respuesta", &corto(&e.to_string(), 300)))?;
        let c = match self.armar(prompt, o, &tmp.0, true) {
            Ok(c) => c,
            Err(Falla::NoInstalada) => return Err(self.error(ia, "no_instalada", "")),
            Err(Falla::VersionVieja) => return Err(self.error(ia, "actualizar", "")),
            Err(Falla::Otra(e)) => return Err(self.error(ia, "sin_respuesta", &corto(&e, 300))),
        };
        let mut proceso = Command::new(&c.cmd[0]);
        proceso.args(&c.cmd[1..]).current_dir(&tmp.0).env_clear().envs(c.env.iter().map(|(k, v)| (k, v)))
            .stdin(if c.entrada.is_some() { Stdio::piped() } else { Stdio::null() }).stdout(Stdio::piped()).stderr(Stdio::piped());
        let mut p = match proceso.spawn() {
            Ok(p) => p,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Err(self.error(ia, "no_instalada", "")),
            Err(e) => return Err(self.error(ia, "sin_respuesta", &corto(&e.to_string(), 300))),
        };
        if let (Some(mut stdin), Some(texto)) = (p.stdin.take(), c.entrada.clone()) {
            thread::spawn(move || {
                let _ = stdin.write_all(texto.as_bytes());
            });
        }
        let (tx, rx) = mpsc::channel::<String>();
        let salida = p.stdout.take().expect("stdout");
        let lector = thread::spawn(move || {
            for linea in BufReader::new(salida).lines().map_while(Result::ok) {
                if tx.send(linea).is_err() {
                    break;
                }
            }
        });
        let errores = p.stderr.take().expect("stderr");
        let (tx_err, rx_err) = mpsc::channel::<String>();
        thread::spawn(move || {
            let mut t = String::new();
            let _ = BufReader::new(errores).take(400 * 1024).read_to_string(&mut t);
            let _ = tx_err.send(t);
        });
        let limite = Instant::now() + o.timeout;
        let mut lineas: Vec<String> = vec![];
        let mut final_: Option<(String, bool)> = None;
        let mut motivo: Option<&str> = None;
        let mut tratar = |linea: String, final_: &mut Option<(String, bool)>, lineas: &mut Vec<String>| match c.formato {
            "claude-json" => {
                if let Some(f) = evento_claude(&linea, al_evento) {
                    *final_ = Some(f);
                }
            }
            "codex-json" => evento_codex(&linea, al_evento),
            _ => {
                if lineas.len() < 200_000 {
                    lineas.push(linea);
                }
            }
        };
        loop {
            match rx.recv_timeout(Duration::from_millis(250)) {
                Ok(linea) => tratar(linea, &mut final_, &mut lineas),
                Err(mpsc::RecvTimeoutError::Disconnected) => break,
                Err(mpsc::RecvTimeoutError::Timeout) => {}
            }
            if detener() {
                motivo = Some("detenido");
            } else if Instant::now() > limite {
                motivo = Some("demora");
            }
            if motivo.is_some() {
                matar(&mut p);
                break;
            }
        }
        let estado = p.wait();
        // Lo que quedó por leer. Si algo que lanzó la IA sigue con la salida abierta, no se espera más de 5 s.
        let fin = Instant::now() + Duration::from_secs(5);
        while let Ok(l) = rx.recv_timeout(fin.saturating_duration_since(Instant::now())) {
            tratar(l, &mut final_, &mut lineas);
        }
        drop(lector);
        let err = rx_err.recv_timeout(fin.saturating_duration_since(Instant::now()).max(Duration::from_millis(200))).unwrap_or_default();
        if ia == "claude" {
            self.aprender(&c.comando, &err);
        }
        if let Some(m) = motivo {
            return Err(self.error(ia, m, ""));
        }
        let (texto, es_error) = match (c.formato, &c.salida) {
            ("claude-json", _) => final_.unwrap_or((String::new(), true)),
            (_, Some(s)) => (fs::read_to_string(s).unwrap_or_default(), false),
            _ => (lineas.join("\n"), false),
        };
        let ok = estado.map(|s| s.success()).unwrap_or(false);
        if !ok || es_error || texto.trim().is_empty() {
            let utiles = sin_avisos(&err);
            let detalle = if es_error && !texto.trim().is_empty() { corto(texto.trim(), 300) }
                else { utiles.last().map(|l| corto(l, 300)).unwrap_or_default() };
            return Err(self.error(ia, if detalle.is_empty() { "sin_respuesta_corta" } else { "sin_respuesta" }, &detalle));
        }
        Ok(texto)
    }

    /// «Probar» desde «Tu IA»: {ia, ok, codigo?, plantilla?, valores?, error?}. Sin la «ayuda» (ya se está en «Tu IA»).
    pub fn probar(&self, ia: &str) -> Value {
        if info(ia).is_none() {
            let p = plantilla("desconocida");
            return json!({"ia": ia, "ok": false, "codigo": "desconocida", "plantilla": p, "valores": {}, "error": p});
        }
        let mut o = Opciones::de(ia);
        o.timeout = Duration::from_secs(120);
        match self.preguntar("Responde solo con la palabra: listo", &o) {
            Ok(_) => json!({"ia": ia, "ok": true}),
            Err(mut e) => {
                e.ayuda = None;
                let mut v = e.json();
                v["ia"] = json!(ia);
                v["ok"] = json!(false);
                v["error"] = json!(e.frase());
                v
            }
        }
    }
}

/// Corta la IA como `ia.py`: primero le pide terminar (así el CLI cierra lo que lanzó) y, si en 5 s no terminó, la mata.
fn matar(p: &mut std::process::Child) {
    #[cfg(unix)]
    {
        let _ = Command::new("kill").args(["-TERM", &p.id().to_string()]).stdout(Stdio::null()).stderr(Stdio::null()).status();
        let fin = Instant::now() + Duration::from_secs(5);
        while Instant::now() < fin {
            if matches!(p.try_wait(), Ok(Some(_))) {
                return;
            }
            thread::sleep(Duration::from_millis(50));
        }
    }
    let _ = p.kill();
}

fn sin_secretos(no_leer: &[String]) -> Vec<String> {
    no_leer
        .iter()
        .flat_map(|patron| {
            let p = format!("{}{}", patron.trim_end_matches('/'), if patron.ends_with('/') { "/**" } else { "" });
            [format!("Read(**/{p})"), format!("Read(./{p})")]
        })
        .collect()
}

/// (ruta, fecha, tamaño) del comando: si el CLI se actualiza, se vuelve a preguntar.
fn huella(cmd: &Path) -> String {
    fs::metadata(cmd)
        .map(|m| format!("{}:{}", m.len(), m.modified().ok().and_then(|t| t.duration_since(UNIX_EPOCH).ok()).map(|d| d.as_nanos()).unwrap_or(0)))
        .unwrap_or_default()
}

/// Corre `cmd args` sin entrada y con límite de tiempo; devuelve stdout + stderr ("" si no se pudo).
fn correr_corto(cmd: &Path, args: &[&str], env: &[(OsString, OsString)], limite: Duration) -> String {
    let Ok(mut p) = Command::new(cmd).args(args).env_clear().envs(env.iter().map(|(k, v)| (k, v))).stdin(Stdio::null())
        .stdout(Stdio::piped()).stderr(Stdio::piped()).spawn() else { return String::new() };
    let (mut o, mut e) = (p.stdout.take().expect("stdout"), p.stderr.take().expect("stderr"));
    let ho = thread::spawn(move || {
        let mut t = String::new();
        let _ = (&mut o).take(1 << 20).read_to_string(&mut t);
        t
    });
    let he = thread::spawn(move || {
        let mut t = String::new();
        let _ = (&mut e).take(1 << 20).read_to_string(&mut t);
        t
    });
    let fin = Instant::now() + limite;
    loop {
        match p.try_wait() {
            Ok(Some(_)) => break,
            Ok(None) if Instant::now() < fin => thread::sleep(Duration::from_millis(50)),
            _ => {
                let _ = p.kill();
                let _ = p.wait();
                return String::new();
            }
        }
    }
    format!("{}{}", ho.join().unwrap_or_default(), he.join().unwrap_or_default())
}

fn leer_json(ruta: &Path, maximo: u64) -> Option<Value> {
    if fs::metadata(ruta).ok()?.len() > maximo {
        return None;
    }
    serde_json::from_slice(&fs::read(ruta).ok()?).ok()
}

fn escribir_privado(ruta: &Path, datos: &[u8]) -> std::io::Result<()> {
    if let Some(d) = ruta.parent() {
        fs::create_dir_all(d)?;
    }
    let tmp = ruta.with_extension("tmp");
    let mut o = fs::OpenOptions::new();
    o.write(true).create(true).truncate(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        o.mode(0o600);
    }
    o.open(&tmp)?.write_all(datos)?;
    fs::rename(tmp, ruta)
}

#[cfg(test)]
mod pruebas {
    use super::*;

    fn eventos_claude(lineas: &[&str]) -> (Vec<Evento>, Option<(String, bool)>) {
        let mut v = vec![];
        let mut fin = None;
        for l in lineas {
            if let Some(f) = evento_claude(l, &mut |e| v.push(e)) {
                fin = Some(f);
            }
        }
        (v, fin)
    }

    #[test]
    fn claude_cuenta_lo_que_lee_escribe_y_gasta() {
        let (v, fin) = eventos_claude(&[
            r#"{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read","input":{"file_path":"/a/b.py"}}]}}"#,
            r#"{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Grep","input":{"pattern":"atr","path":"/a"}}]}}"#,
            r#"{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Edit","input":{"file_path":"/a/c.py"}}]}}"#,
            "no es json",
            r#"{"type":"result","result":"Listo.","is_error":false,"usage":{"input_tokens":10,"cache_creation_input_tokens":5,"cache_read_input_tokens":100,"output_tokens":7}}"#,
        ]);
        assert_eq!(v, vec![
            Evento::Lee { ruta: "/a/b.py".into() },
            Evento::Busca { patron: "atr".into(), ruta: Some("/a".into()) },
            Evento::Escribe { ruta: "/a/c.py".into() },
            Evento::Uso { entrada: 15, cache: 100, salida: 7 },
        ]);
        assert_eq!(fin, Some(("Listo.".into(), false)));
    }

    #[test]
    fn codex_lee_busca_y_cuenta() {
        let mut v = vec![];
        for l in [
            r#"{"type":"item.started","item":{"command":["bash","-lc","'cat src/a.py'"]}}"#,
            r#"{"item":{"command":"rg spread bin"}}"#,
            r#"{"item":{"changes":[{"path":"ui/app.js"}]}}"#,
            r#"{"type":"item.completed","item":{"command":"cat x.py"}}"#,
            r#"{"type":"turn.completed","usage":{"input_tokens":120,"cached_input_tokens":100,"output_tokens":9}}"#,
        ] {
            evento_codex(l, &mut |e| v.push(e));
        }
        assert_eq!(v, vec![
            Evento::Lee { ruta: "src/a.py".into() },
            Evento::Busca { patron: "spread bin".into(), ruta: None },
            Evento::Escribe { ruta: "ui/app.js".into() },
            Evento::Uso { entrada: 20, cache: 100, salida: 9 },
        ]);
    }

    #[test]
    fn opcion_no_calza_dentro_de_otra() {
        let re = regex_opcion("--tools");
        assert!(re.is_match("  --tools <list>  Herramientas"));
        assert!(!re.is_match("  --allowedTools x  --tools-extra"));
        assert!(re.is_match("--tools"));
    }

    #[test]
    fn errores_con_plantilla_y_ayuda() {
        let ia = Ia::nueva(Contexto { app_id: "x".into(), app_nombre: "Recetas".into(), prefijo: "RECETAS".into(),
            datos: std::env::temp_dir(), ayuda: "Revisa en Ajustes → Tu IA.".into() });
        let e = ia.error("claude", "no_instalada", "");
        assert_eq!(e.frase(), "No encontré Claude en este computador. Revisa en Ajustes → Tu IA.");
        let e = ia.error("codex", "actualizar", "");
        assert!(e.frase().starts_with("Actualiza ChatGPT (Codex) para usarla con Recetas"));
        assert_eq!(ia.error("claude", "demora", "").ayuda, None);
    }

    #[test]
    fn secretos_por_patron() {
        assert_eq!(sin_secretos(&[".env".into(), "llaves/".into()]),
            vec!["Read(**/.env)", "Read(./.env)", "Read(**/llaves/**)", "Read(./llaves/**)"]);
    }

    #[cfg(unix)]
    #[test]
    fn claude_falso_de_punta_a_punta() {
        use std::os::unix::fs::PermissionsExt;
        let _g = BLOQUEO.lock().unwrap_or_else(|e| e.into_inner());
        let dir = Temporal::nueva("prueba").unwrap();
        let cmd = dir.0.join("claude");
        // Un «claude» falso: conoce las protecciones, cuenta lo que lee y responde lo que recibió por la entrada estándar.
        fs::write(&cmd, "#!/bin/sh\n\
            case \"$1\" in --help) echo '--strict-mcp-config --disallowedTools --tools --output-format stream-json --safe-mode'; exit 0;; \
            --version) echo '2.3.4 (Claude Code)'; exit 0;; esac\n\
            entrada=$(cat)\n\
            [ -n \"$PRUEBA_SECRETO\" ] && echo fuga\n\
            echo '{\"type\":\"assistant\",\"message\":{\"content\":[{\"type\":\"tool_use\",\"name\":\"Read\",\"input\":{\"file_path\":\"a.md\"}}]}}'\n\
            printf '{\"type\":\"result\",\"result\":\"%s\",\"is_error\":false,\"usage\":{\"input_tokens\":3,\"output_tokens\":2}}\\n' \"$entrada\"\n").unwrap();
        fs::set_permissions(&cmd, fs::Permissions::from_mode(0o755)).unwrap();
        let antes = std::env::var_os("PATH").unwrap_or_default();
        let mut rutas = vec![dir.0.clone()];
        rutas.extend(std::env::split_paths(&antes));
        std::env::set_var("PATH", std::env::join_paths(rutas).unwrap());
        std::env::set_var("PRUEBA_SECRETO", "1");
        let ia = Ia::nueva(Contexto { app_id: "prueba".into(), app_nombre: "Prueba".into(), prefijo: "PRUEBA".into(),
            datos: dir.0.clone(), ayuda: String::new() });
        let tmp = Temporal::nueva("prueba").unwrap();
        let a = ia.armado("hola", &Opciones::de("claude"), &tmp.0, true).unwrap();
        let args: Vec<String> = a.cmd.iter().map(|x| x.to_string_lossy().into()).collect();
        assert!(args.contains(&"--strict-mcp-config".to_string()));
        assert!(args.windows(2).any(|w| w == ["--disallowedTools", "*"]));
        assert!(args.contains(&"--safe-mode".to_string()));
        assert!(!args.iter().any(|x| x.contains("hola")), "el pedido nunca va como argumento");
        assert!(!a.env.iter().any(|(k, _)| k == "PRUEBA_SECRETO"), "la IA no recibe las variables de la app");
        let mut v = vec![];
        let r = ia.preguntar_vivo("hola", &Opciones::de("claude"), &mut |e| v.push(e), &|| false);
        std::env::set_var("PATH", antes);
        std::env::remove_var("PRUEBA_SECRETO");
        assert_eq!(r, Ok("hola".to_string()));
        assert_eq!(v, vec![Evento::Lee { ruta: "a.md".into() }, Evento::Uso { entrada: 3, cache: 0, salida: 2 }]);
    }

    #[cfg(unix)]
    #[test]
    fn detener_corta_la_ia() {
        use std::os::unix::fs::PermissionsExt;
        let _g = BLOQUEO.lock().unwrap_or_else(|e| e.into_inner());
        let dir = Temporal::nueva("prueba").unwrap();
        let cmd = dir.0.join("claude");
        fs::write(&cmd, "#!/bin/sh\ncase \"$1\" in --help) echo '--strict-mcp-config --disallowedTools'; exit 0;; esac\ncat >/dev/null\nsleep 30\n").unwrap();
        fs::set_permissions(&cmd, fs::Permissions::from_mode(0o755)).unwrap();
        let antes = std::env::var_os("PATH").unwrap_or_default();
        let mut rutas = vec![dir.0.clone()];
        rutas.extend(std::env::split_paths(&antes));
        std::env::set_var("PATH", std::env::join_paths(rutas).unwrap());
        let ia = Ia::nueva(Contexto { app_id: "prueba".into(), app_nombre: "Prueba".into(), prefijo: "PRUEBA".into(),
            datos: dir.0.clone(), ayuda: String::new() });
        let inicio = Instant::now();
        let r = ia.preguntar_vivo("hola", &Opciones::de("claude"), &mut |_| {}, &|| inicio.elapsed() > Duration::from_millis(300));
        std::env::set_var("PATH", antes);
        assert!(r.as_ref().unwrap_err().detenido(), "{r:?}");
        assert!(inicio.elapsed() < Duration::from_secs(10));
    }

    static BLOQUEO: Mutex<()> = Mutex::new(());
}
