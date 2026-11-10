// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.
//! Pieza «red» en Rust: pedidos HTTPS seguros desde la app. Usa `ureq`, `url` y `serde_json` (ya vienen con host-tauri).
//!
//! La misma pieza que `python/red.py`, con las mismas reglas:
//! - **Solo https y solo los dominios permitidos** (exactos, sin puerto raro, sin usuario:clave en la URL). Otro se rechaza
//!   antes de salir.
//! - **Nunca se siguen redirecciones**: se llevarían la llave de la cabecera a otro dominio.
//! - **Límites**: tamaño máximo de la respuesta (se corta al leer, no se confía en Content-Length) y tiempo del pedido entero.
//! - **Subidas grandes por partes** (`subir`): `Content-Range` por parte, se retoma desde lo que el servicio dice tener (308).
//! - **El User-Agent** es «<Nombre> (<repo>)», siempre en ASCII.
//! - **Las credenciales** viajan solo en las cabeceras: nunca en disco ni en los mensajes de error.
//!
//! ```ignore
//! let r = Red::nueva(&["api.ejemplo.com"], "Banco Ejemplo", &agente("Alcancía", Some("alcancia-app/alcancia")))?;
//! let datos = r.get("https://api.ejemplo.com/v1/saldo", &[("Authorization", &format!("Bearer {llave}"))])?;
//! // Err(ErrorRed): e.codigo, e.plantilla, e.valores (para traducir), e.frase(), e.estado, e.cuerpo
//! ```
//!
//! Para las pruebas, `con_prueba("http://127.0.0.1:<puerto>")` manda todo a un servidor local (solo 127.0.0.1). El pedido llega
//! a `/<dominio>/<ruta>`. La app nunca lo usa.

use regex::Regex;
use serde_json::{json, Map, Value};
use std::collections::HashSet;
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::Path;
use std::sync::OnceLock;
use std::time::Duration;

pub const MAXIMO: u64 = 10 * 1024 * 1024;
pub const TIEMPO: Duration = Duration::from_secs(60);
const MAXIMO_TOPE: u64 = 200 * 1024 * 1024;
const TIEMPO_TOPE: Duration = Duration::from_secs(600);

/// Frases en español con marcadores (claves de traducción): la interfaz hace `Tp(plantilla, valores)`.
pub fn plantilla(codigo: &str) -> &'static str {
    match codigo {
        "no_permitida" => "Dirección no permitida para {servicio}.",
        "redireccion" => "{servicio} quiso mandarme a otra dirección y no la seguí (por seguridad).",
        "llave" => "{servicio} no aceptó la llave (puede estar vencida o sin permiso de lectura).",
        "esperar" => "{servicio} pidió esperar un rato antes de volver a consultar.",
        "error" => "{servicio} respondió con un error ({estado}).",
        "sin_conexion" => "No pude conectarme con {servicio}. ¿Hay internet?",
        "demora" => "{servicio} se demoró demasiado en responder.",
        "grande" => "{servicio} mandó una respuesta demasiado grande.",
        _ => "{servicio} respondió algo que no entendí.",
    }
}

/// Algo falló al hablar con el servicio. `frase()` nunca incluye la credencial.
#[derive(Clone, Debug, PartialEq)]
pub struct ErrorRed {
    pub codigo: String,
    pub plantilla: String,
    pub valores: Map<String, Value>,
    pub estado: u16,
    pub cuerpo: String,
}

impl ErrorRed {
    pub fn frase(&self) -> String {
        let mut t = self.plantilla.clone();
        for (k, v) in &self.valores {
            t = t.replace(&format!("{{{k}}}"), v.as_str().unwrap_or(""));
        }
        t
    }
    /// Lo que se responde a la interfaz: {ok: false, codigo, plantilla, valores, error}.
    pub fn json(&self) -> Value {
        json!({"ok": false, "codigo": self.codigo, "plantilla": self.plantilla, "valores": self.valores, "error": self.frase()})
    }
}

impl std::fmt::Display for ErrorRed {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.frase())
    }
}

/// El cuerpo de un pedido.
#[derive(Clone, Debug, Default)]
pub enum Cuerpo {
    #[default]
    Nada,
    Json(Value),
    Formulario(Vec<(String, String)>),
    /// Bytes tal cual, con su Content-Type.
    Datos(Vec<u8>, String),
}

/// Un pedido. `Pedido::get(url)` y se ajusta lo que haga falta.
#[derive(Clone, Debug)]
pub struct Pedido {
    pub metodo: &'static str,
    pub url: String,
    pub cabeceras: Vec<(String, String)>,
    pub cuerpo: Cuerpo,
    pub tiempo: Option<Duration>,
    pub maximo: Option<u64>,
}

impl Pedido {
    pub fn nuevo(metodo: &'static str, url: &str) -> Self {
        Pedido { metodo, url: url.into(), cabeceras: vec![], cuerpo: Cuerpo::Nada, tiempo: None, maximo: None }
    }
    pub fn cabecera(mut self, k: &str, v: &str) -> Self {
        self.cabeceras.push((k.into(), v.into()));
        self
    }
    pub fn cuerpo(mut self, c: Cuerpo) -> Self {
        self.cuerpo = c;
        self
    }
}

/// La respuesta: estado, cabeceras que importan y los bytes (ya cortados al máximo).
#[derive(Clone, Debug)]
pub struct Respuesta {
    pub estado: u16,
    pub rango: Option<String>,
    pub datos: Vec<u8>,
}

fn dominio_valido(h: &str) -> bool {
    static RE: OnceLock<Regex> = OnceLock::new();
    h.len() <= 253 && RE.get_or_init(|| Regex::new(r"^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$").expect("regex")).is_match(h)
}

/// Un texto seguro para una cabecera HTTP: sin tildes ni símbolos raros. «Señal» → «Senal».
pub fn ascii(texto: &str) -> String {
    let mut t = String::new();
    for c in texto.chars() {
        let b = match c {
            'á' | 'à' | 'ä' | 'â' | 'ã' | 'å' => 'a',
            'Á' | 'À' | 'Ä' | 'Â' | 'Ã' | 'Å' => 'A',
            'é' | 'è' | 'ë' | 'ê' => 'e',
            'É' | 'È' | 'Ë' | 'Ê' => 'E',
            'í' | 'ì' | 'ï' | 'î' => 'i',
            'Í' | 'Ì' | 'Ï' | 'Î' => 'I',
            'ó' | 'ò' | 'ö' | 'ô' | 'õ' => 'o',
            'Ó' | 'Ò' | 'Ö' | 'Ô' | 'Õ' => 'O',
            'ú' | 'ù' | 'ü' | 'û' => 'u',
            'Ú' | 'Ù' | 'Ü' | 'Û' => 'U',
            'ñ' => 'n',
            'Ñ' => 'N',
            'ç' => 'c',
            'Ç' => 'C',
            c if (' '..='~').contains(&c) && c != '"' && c != '\\' => c,
            _ => continue,
        };
        t.push(b);
    }
    t.split_whitespace().collect::<Vec<_>>().join(" ").chars().take(80).collect()
}

/// User-Agent: «<Nombre> (<repo>)» con `repo` («dueño/repo») si es válido; siempre ASCII.
pub fn agente(nombre: &str, repo: Option<&str>) -> String {
    static RE: OnceLock<Regex> = OnceLock::new();
    let n = Some(ascii(nombre)).filter(|n| !n.is_empty()).unwrap_or_else(|| "app".into());
    match repo.filter(|r| RE.get_or_init(|| Regex::new(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$").expect("regex")).is_match(r)) {
        Some(r) => format!("{n} ({r})"),
        None => n,
    }
}

pub struct Red {
    hosts: HashSet<String>,
    servicio: String,
    agente: String,
    pub maximo: u64,
    pub tiempo: Duration,
    prueba: Option<String>,
}

impl Red {
    /// `hosts`: los únicos dominios a los que puede hablar este servicio. Err si alguno no es un dominio.
    pub fn nueva(hosts: &[&str], servicio: &str, agente: &str) -> Result<Self, String> {
        let hosts: HashSet<String> = hosts.iter().map(|h| h.to_lowercase()).collect();
        if hosts.is_empty() || hosts.iter().any(|h| !dominio_valido(h)) {
            return Err("Red: los dominios permitidos son nombres como «api.ejemplo.com».".into());
        }
        Ok(Red { hosts, servicio: servicio.into(), agente: ascii(agente), maximo: MAXIMO, tiempo: TIEMPO, prueba: None })
    }

    /// Solo para pruebas: todo va a un servidor local (`http://127.0.0.1:<puerto>`), a `/<dominio>/<ruta>`.
    pub fn con_prueba(mut self, base: &str) -> Self {
        static RE: OnceLock<Regex> = OnceLock::new();
        if RE.get_or_init(|| Regex::new(r"^http://127\.0\.0\.1:\d{1,5}$").expect("regex")).is_match(base) {
            self.prueba = Some(base.into());
        }
        self
    }

    fn error(&self, codigo: &str, estado: u16, cuerpo: String) -> ErrorRed {
        let mut valores = Map::new();
        valores.insert("servicio".into(), json!(self.servicio));
        valores.insert("estado".into(), json!(estado.to_string()));
        ErrorRed { codigo: codigo.into(), plantilla: plantilla(codigo).into(), valores, estado, cuerpo }
    }

    /// True si la URL es https a uno de los dominios permitidos (puerto 443 o ninguno, sin usuario ni clave).
    pub fn permitida(&self, url: &str) -> bool {
        if url.contains('\\') || url.chars().any(|c| (c as u32) <= 0x20) {
            return false;
        }
        let Ok(u) = url::Url::parse(url) else { return false };
        u.scheme() == "https"
            && u.host_str().is_some_and(|h| self.hosts.contains(&h.to_lowercase()))
            && matches!(u.port(), None | Some(443))
            && u.username().is_empty()
            && u.password().is_none()
    }

    fn destino(&self, url: &str) -> Result<String, ErrorRed> {
        if !self.permitida(url) {
            return Err(self.error("no_permitida", 0, String::new()));
        }
        Ok(match &self.prueba {
            Some(base) => {
                let u = url::Url::parse(url).map_err(|_| self.error("no_permitida", 0, String::new()))?;
                format!("{base}/{}{}{}", u.host_str().unwrap_or(""), u.path(), u.query().map(|q| format!("?{q}")).unwrap_or_default())
            }
            None => url.into(),
        })
    }

    /// El pedido entero, sin interpretar el estado (lo usa `subir` para el 308). Los errores de red ya vienen como ErrorRed.
    pub fn enviar(&self, p: &Pedido) -> Result<Respuesta, ErrorRed> {
        let destino = self.destino(&p.url)?;
        let tiempo = p.tiempo.unwrap_or(self.tiempo).min(TIEMPO_TOPE);
        let maximo = p.maximo.unwrap_or(self.maximo).min(MAXIMO_TOPE);
        let agente: ureq::Agent = ureq::Agent::config_builder()
            .max_redirects(0) // nunca: la llave iría a otro dominio
            .https_only(self.prueba.is_none())
            .http_status_as_error(false)
            .timeout_global(Some(tiempo))
            .user_agent(self.agente.as_str())
            .accept("application/json")
            .build()
            .into();
        let cab = |mut b: ureq::RequestBuilder<ureq::typestate::WithBody>| {
            for (k, v) in &p.cabeceras {
                b = b.header(k.as_str(), v.as_str());
            }
            b
        };
        let cab_sin = |mut b: ureq::RequestBuilder<ureq::typestate::WithoutBody>| {
            for (k, v) in &p.cabeceras {
                b = b.header(k.as_str(), v.as_str());
            }
            b
        };
        let con_cuerpo = |b: ureq::RequestBuilder<ureq::typestate::WithBody>| match &p.cuerpo {
            Cuerpo::Nada => cab(b).send_empty(),
            Cuerpo::Json(v) => cab(b).header("Content-Type", "application/json").send(serde_json::to_vec(v).unwrap_or_default().as_slice()),
            Cuerpo::Formulario(f) => {
                let txt = url::form_urlencoded::Serializer::new(String::new()).extend_pairs(f.iter()).finish();
                cab(b).header("Content-Type", "application/x-www-form-urlencoded").send(txt.as_bytes())
            }
            Cuerpo::Datos(d, tipo) => cab(b).header("Content-Type", tipo.as_str()).send(d.as_slice()),
        };
        let r = match p.metodo {
            "GET" => cab_sin(agente.get(&destino)).call(),
            "HEAD" => cab_sin(agente.head(&destino)).call(),
            "DELETE" => cab_sin(agente.delete(&destino)).call(),
            "POST" => con_cuerpo(agente.post(&destino)),
            "PUT" => con_cuerpo(agente.put(&destino)),
            "PATCH" => con_cuerpo(agente.patch(&destino)),
            _ => return Err(self.error("no_permitida", 0, String::new())),
        };
        let r = r.map_err(|e| match e {
            ureq::Error::Timeout(_) => self.error("demora", 0, String::new()),
            ureq::Error::TooManyRedirects | ureq::Error::RedirectFailed => self.error("redireccion", 0, String::new()),
            _ => self.error("sin_conexion", 0, String::new()),
        })?;
        let estado = r.status().as_u16();
        let cabecera = |k: &str| r.headers().get(k).and_then(|x| x.to_str().ok()).map(String::from);
        let rango = cabecera("range");
        if cabecera("content-length").and_then(|x| x.parse::<u64>().ok()).is_some_and(|n| n > maximo) {
            return Err(self.error("grande", estado, String::new()));
        }
        let mut datos = Vec::new();
        r.into_body().into_reader().take(maximo + 1).read_to_end(&mut datos).map_err(|e| {
            if e.kind() == std::io::ErrorKind::TimedOut || e.to_string().to_lowercase().contains("timeout") {
                self.error("demora", estado, String::new())
            } else {
                self.error("sin_conexion", estado, String::new())
            }
        })?;
        if datos.len() as u64 > maximo {
            return Err(self.error("grande", estado, String::new()));
        }
        Ok(Respuesta { estado, rango, datos })
    }

    /// El pedido con el estado ya revisado: Ok con los bytes de un 2xx, o el ErrorRed que corresponde.
    pub fn pedir(&self, p: &Pedido) -> Result<Vec<u8>, ErrorRed> {
        let r = self.enviar(p)?;
        let texto = || String::from_utf8_lossy(&r.datos[..r.datos.len().min(2000)]).into_owned();
        match r.estado {
            200..=299 => Ok(r.datos),
            300..=399 => Err(self.error("redireccion", r.estado, String::new())),
            401 | 403 => Err(self.error("llave", r.estado, texto())),
            429 => Err(self.error("esperar", r.estado, texto())),
            e => Err(self.error("error", e, texto())),
        }
    }

    /// El JSON de la respuesta (vacía = null).
    pub fn json(&self, p: &Pedido) -> Result<Value, ErrorRed> {
        let datos = self.pedir(p)?;
        if datos.is_empty() {
            return Ok(Value::Null);
        }
        serde_json::from_slice(&datos).map_err(|_| self.error("no_entendi", 200, String::new()))
    }

    /// GET con cabeceras → JSON.
    pub fn get(&self, url: &str, cabeceras: &[(&str, &str)]) -> Result<Value, ErrorRed> {
        let mut p = Pedido::nuevo("GET", url);
        for (k, v) in cabeceras {
            p = p.cabecera(k, v);
        }
        self.json(&p)
    }

    /// Sube un archivo grande por partes (`Content-Range: bytes a-b/total`). El servicio responde 308 (sin Location) mientras
    /// falta, con `Range: bytes=0-n` (se sigue desde ahí), y 2xx al final (su JSON es lo que se devuelve). `avance(enviados,
    /// total)` después de cada parte; `desde` retoma una subida cortada.
    #[allow(clippy::too_many_arguments)]
    pub fn subir(&self, metodo: &'static str, url: &str, archivo: &Path, parte: usize, cabeceras: &[(&str, &str)], tipo: &str,
                 desde: u64, avance: &mut dyn FnMut(u64, u64)) -> Result<Value, ErrorRed> {
        if !(256 * 1024..=256 * 1024 * 1024).contains(&parte) {
            return Err(self.error("no_entendi", 0, "Red: «parte» va entre 256 KB y 256 MB.".into()));
        }
        let mut f = File::open(archivo).map_err(|_| self.error("no_entendi", 0, String::new()))?;
        let total = f.metadata().map(|m| m.len()).unwrap_or(0);
        let mut pos = desde.min(total);
        static RE: OnceLock<Regex> = OnceLock::new();
        let re = RE.get_or_init(|| Regex::new(r"^bytes=0-(\d+)$").expect("regex"));
        loop {
            f.seek(SeekFrom::Start(pos)).map_err(|_| self.error("no_entendi", 0, String::new()))?;
            let mut trozo = Vec::with_capacity(parte);
            (&mut f).take(parte as u64).read_to_end(&mut trozo).map_err(|_| self.error("no_entendi", 0, String::new()))?;
            let rango = if trozo.is_empty() { format!("bytes */{total}") } else { format!("bytes {pos}-{}/{total}", pos + trozo.len() as u64 - 1) };
            let largo = trozo.len() as u64;
            let mut p = Pedido::nuevo(metodo, url).cabecera("Content-Range", &rango).cuerpo(Cuerpo::Datos(trozo, tipo.into()));
            for (k, v) in cabeceras {
                p = p.cabecera(k, v);
            }
            let r = self.enviar(&p)?;
            if r.estado != 308 {
                if !(200..300).contains(&r.estado) {
                    // Mismo trato que pedir(): llave, esperar, error.
                    return Err(match r.estado {
                        300..=399 => self.error("redireccion", r.estado, String::new()),
                        401 | 403 => self.error("llave", r.estado, String::new()),
                        429 => self.error("esperar", r.estado, String::new()),
                        e => self.error("error", e, String::new()),
                    });
                }
                avance(total, total);
                return if r.datos.is_empty() { Ok(Value::Null) } else { serde_json::from_slice(&r.datos).map_err(|_| self.error("no_entendi", r.estado, String::new())) };
            }
            let siguiente = r.rango.as_deref().and_then(|x| re.captures(x)).and_then(|c| c[1].parse::<u64>().ok()).map(|n| n + 1).unwrap_or(pos + largo);
            if largo == 0 || siguiente <= pos {
                return Err(self.error("no_entendi", 308, String::new())); // el servicio no avanza: no se sube lo mismo para siempre
            }
            pos = siguiente.min(total);
            avance(pos, total);
        }
    }
}

#[cfg(test)]
mod pruebas {
    use super::*;
    use std::io::{BufRead, BufReader, Write};
    use std::net::TcpListener;
    use std::sync::{Arc, Mutex};
    use std::thread;

    /// Un servidor falso: responde según la ruta y guarda lo que recibió (ruta, cabeceras).
    fn servidor() -> (String, Arc<Mutex<Vec<String>>>) {
        let l = TcpListener::bind("127.0.0.1:0").unwrap();
        let base = format!("http://127.0.0.1:{}", l.local_addr().unwrap().port());
        let vistos = Arc::new(Mutex::new(vec![]));
        let v = vistos.clone();
        thread::spawn(move || {
            let mut subido: u64 = 0;
            for c in l.incoming().flatten() {
                let mut r = BufReader::new(c.try_clone().unwrap());
                let mut linea = String::new();
                if r.read_line(&mut linea).is_err() {
                    continue;
                }
                let ruta = linea.split_whitespace().nth(1).unwrap_or("").to_string();
                let mut cabeceras = String::new();
                let mut largo = 0usize;
                loop {
                    let mut h = String::new();
                    if r.read_line(&mut h).is_err() || h == "\r\n" || h.is_empty() {
                        break;
                    }
                    if let Some(n) = h.to_lowercase().strip_prefix("content-length:") {
                        largo = n.trim().parse().unwrap_or(0);
                    }
                    cabeceras.push_str(&h);
                }
                let mut cuerpo = vec![0; largo];
                let _ = r.read_exact(&mut cuerpo);
                v.lock().unwrap().push(format!("{ruta}\n{cabeceras}"));
                let (estado, extra, cuerpo_r): (&str, String, Vec<u8>) = match ruta.as_str() {
                    "/api.ejemplo.com/ok" => ("200 OK", String::new(), br#"{"saldo": 1500}"#.to_vec()),
                    "/api.ejemplo.com/vuelta" => ("302 Found", "Location: https://malo.example/robar\r\n".into(), vec![]),
                    "/api.ejemplo.com/llave" => ("401 Unauthorized", String::new(), b"no".to_vec()),
                    "/api.ejemplo.com/espera" => ("429 Too Many Requests", String::new(), vec![]),
                    "/api.ejemplo.com/grande" => ("200 OK", String::new(), vec![b'x'; 5000]),
                    "/api.ejemplo.com/subir" => {
                        subido += largo as u64;
                        if subido < 600 * 1024 { ("308 Resume Incomplete", format!("Range: bytes=0-{}\r\n", subido - 1), vec![]) }
                        else { ("201 Created", String::new(), br#"{"id": "abc"}"#.to_vec()) }
                    }
                    _ => ("404 Not Found", String::new(), vec![]),
                };
                let mut c = c;
                let _ = write!(c, "HTTP/1.1 {estado}\r\n{extra}Content-Length: {}\r\nConnection: close\r\n\r\n", cuerpo_r.len());
                let _ = c.write_all(&cuerpo_r);
            }
        });
        (base, vistos)
    }

    fn red(base: &str) -> Red {
        Red::nueva(&["api.ejemplo.com"], "Banco Ejemplo", &agente("Señal Ñandú", Some("ana-perez/senal"))).unwrap().con_prueba(base)
    }

    #[test]
    fn solo_https_a_los_dominios_permitidos() {
        let r = Red::nueva(&["api.ejemplo.com"], "X", "x").unwrap();
        assert!(r.permitida("https://api.ejemplo.com/v1?a=1"));
        assert!(r.permitida("https://API.ejemplo.com:443/v1"));
        for malo in ["http://api.ejemplo.com/", "https://api.ejemplo.com:8443/", "https://ana:clave@api.ejemplo.com/",
            "https://otro.com/", "https://api.ejemplo.com.otro.com/", "https://api.ejemplo.com\\@otro.com/", "https://api.ejemplo.com/ a"] {
            assert!(!r.permitida(malo), "{malo}");
        }
        assert!(Red::nueva(&["no es un dominio"], "X", "x").is_err());
        assert!(Red::nueva(&[], "X", "x").is_err());
    }

    #[test]
    fn agente_en_ascii() {
        assert_eq!(agente("Señal Ñandú", Some("ana-perez/senal")), "Senal Nandu (ana-perez/senal)");
        assert_eq!(agente("Alcancía 💰", Some("no válido/x y")), "Alcancia");
        assert_eq!(agente("💰", None), "app");
    }

    #[test]
    fn pide_y_lee_json_con_su_agente() {
        let (base, vistos) = servidor();
        let r = red(&base);
        assert_eq!(r.get("https://api.ejemplo.com/ok", &[("Authorization", "Bearer secreta")]).unwrap(), json!({"saldo": 1500}));
        let v = vistos.lock().unwrap().join("\n").to_lowercase();
        assert!(v.contains("user-agent: senal nandu (ana-perez/senal)"), "{v}");
        assert!(v.contains("authorization: bearer secreta"));
    }

    #[test]
    fn nunca_sigue_redirecciones_y_explica_cada_error() {
        let (base, vistos) = servidor();
        let r = red(&base);
        let e = r.get("https://api.ejemplo.com/vuelta", &[("Authorization", "Bearer secreta")]).unwrap_err();
        assert_eq!(e.codigo, "redireccion");
        assert_eq!(vistos.lock().unwrap().len(), 1, "no fue a la otra dirección");
        assert!(!e.frase().contains("secreta"));
        assert_eq!(r.get("https://api.ejemplo.com/llave", &[]).unwrap_err().codigo, "llave");
        assert_eq!(r.get("https://api.ejemplo.com/espera", &[]).unwrap_err().codigo, "esperar");
        let e = r.get("https://api.ejemplo.com/nada", &[]).unwrap_err();
        assert_eq!((e.codigo.as_str(), e.frase().as_str()), ("error", "Banco Ejemplo respondió con un error (404)."));
        assert_eq!(r.get("https://otro.com/ok", &[]).unwrap_err().codigo, "no_permitida");
    }

    #[test]
    fn corta_lo_grande() {
        let (base, _) = servidor();
        let mut r = red(&base);
        r.maximo = 1000;
        assert_eq!(r.get("https://api.ejemplo.com/grande", &[]).unwrap_err().codigo, "grande");
    }

    #[test]
    fn sin_conexion() {
        let r = red("http://127.0.0.1:9");
        assert_eq!(r.get("https://api.ejemplo.com/ok", &[]).unwrap_err().codigo, "sin_conexion");
    }

    #[test]
    fn sube_por_partes_y_retoma() {
        let (base, _) = servidor();
        let r = red(&base);
        let archivo = std::env::temp_dir().join(format!("red-subir-{}.bin", std::process::id()));
        std::fs::write(&archivo, vec![7u8; 700 * 1024]).unwrap();
        let mut avances = vec![];
        let v = r.subir("PUT", "https://api.ejemplo.com/subir", &archivo, 256 * 1024, &[], "video/mp4", 0, &mut |a, t| avances.push((a, t))).unwrap();
        let _ = std::fs::remove_file(&archivo);
        assert_eq!(v, json!({"id": "abc"}));
        assert_eq!(avances.last(), Some(&(700 * 1024, 700 * 1024)));
        assert!(avances.len() >= 3);
    }
}
