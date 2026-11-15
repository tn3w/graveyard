use std::io::{BufRead, BufReader, Read, Write};
use std::net::TcpStream;
use std::sync::Arc;

use rustls::pki_types::ServerName;

use crate::url::{Scheme, Url};
use crate::Error;

type TlsStream =
    rustls::StreamOwned<rustls::ClientConnection, TcpStream>;

enum Connection {
    Plain(TcpStream),
    Tls(TlsStream),
}

impl Read for Connection {
    fn read(
        &mut self,
        buffer: &mut [u8],
    ) -> std::io::Result<usize> {
        match self {
            Self::Plain(stream) => stream.read(buffer),
            Self::Tls(stream) => stream.read(buffer),
        }
    }
}

impl Write for Connection {
    fn write(
        &mut self,
        buffer: &[u8],
    ) -> std::io::Result<usize> {
        match self {
            Self::Plain(stream) => stream.write(buffer),
            Self::Tls(stream) => stream.write(buffer),
        }
    }

    fn flush(&mut self) -> std::io::Result<()> {
        match self {
            Self::Plain(stream) => stream.flush(),
            Self::Tls(stream) => stream.flush(),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Method {
    Get,
    Head,
    Post,
    Put,
}

impl Method {
    pub fn as_str(&self) -> &str {
        match self {
            Self::Get => "GET",
            Self::Head => "HEAD",
            Self::Post => "POST",
            Self::Put => "PUT",
        }
    }
}

#[derive(Debug, Clone)]
pub struct Request {
    pub url: Url,
    pub method: Method,
    pub headers: Vec<(String, String)>,
    pub body: Option<Vec<u8>>,
    pub user_agent: String,
}

impl Request {
    pub fn new(url: Url) -> Self {
        Self {
            url,
            method: Method::Get,
            headers: Vec::new(),
            body: None,
            user_agent: "wurl/0.1".into(),
        }
    }
}

#[derive(Debug)]
pub struct Response {
    pub status: u16,
    pub status_line: String,
    pub headers: Vec<(String, String)>,
    pub body: Vec<u8>,
}

impl Response {
    pub fn body_string(&self) -> String {
        String::from_utf8_lossy(&self.body).into_owned()
    }

    pub fn format_headers(&self) -> String {
        let mut output = format!("{}\r\n", self.status_line);
        for (name, value) in &self.headers {
            output.push_str(&format!("{name}: {value}\r\n"));
        }
        output.push_str("\r\n");
        output
    }
}

const MAX_REDIRECTS: u8 = 10;

pub fn send(request: &Request) -> Result<Response, Error> {
    let mut current_request = request.clone();

    for _ in 0..MAX_REDIRECTS {
        let response = single_request(&current_request)?;

        if !is_redirect(response.status) {
            return Ok(response);
        }

        let location = response
            .headers
            .iter()
            .find(|(name, _)| name == "location")
            .map(|(_, value)| value.clone())
            .ok_or_else(|| {
                Error::InvalidResponse(
                    "redirect without location header".into(),
                )
            })?;

        let new_url = resolve_redirect(
            &current_request.url,
            &location,
        )?;

        current_request.url = new_url;
        if matches!(response.status, 301 | 302 | 303) {
            current_request.method = Method::Get;
            current_request.body = None;
        }
    }

    Err(Error::InvalidResponse("too many redirects".into()))
}

fn is_redirect(status: u16) -> bool {
    matches!(status, 301 | 302 | 303 | 307 | 308)
}

fn resolve_redirect(
    base: &Url,
    location: &str,
) -> Result<Url, Error> {
    if location.starts_with("http://")
        || location.starts_with("https://")
    {
        return Url::parse(location);
    }

    Ok(Url {
        scheme: base.scheme,
        host: base.host.clone(),
        port: base.port,
        path: if location.starts_with('/') {
            location.to_string()
        } else {
            format!("/{location}")
        },
    })
}

fn single_request(
    request: &Request,
) -> Result<Response, Error> {
    let url = &request.url;
    let address = format!("{}:{}", url.host, url.port);
    let tcp = TcpStream::connect(&address)?;

    let connection = match url.scheme {
        Scheme::Http => Connection::Plain(tcp),
        Scheme::Https => {
            Connection::Tls(tls_connect(tcp, &url.host)?)
        }
    };

    execute(connection, request)
}

fn build_raw_request(request: &Request) -> Vec<u8> {
    let url = &request.url;
    let mut raw = format!(
        "{} {} HTTP/1.1\r\n\
         Host: {}\r\n",
        request.method.as_str(),
        url.path,
        url.host_header(),
    );

    let has_user_agent = request
        .headers
        .iter()
        .any(|(n, _)| n.eq_ignore_ascii_case("user-agent"));

    if !has_user_agent {
        raw.push_str(&format!(
            "User-Agent: {}\r\n",
            request.user_agent
        ));
    }

    let has_accept = request
        .headers
        .iter()
        .any(|(n, _)| n.eq_ignore_ascii_case("accept"));

    if !has_accept {
        raw.push_str("Accept: */*\r\n");
    }

    for (name, value) in &request.headers {
        raw.push_str(&format!("{name}: {value}\r\n"));
    }

    if let Some(body) = &request.body {
        let has_content_length = request
            .headers
            .iter()
            .any(|(n, _)| {
                n.eq_ignore_ascii_case("content-length")
            });

        if !has_content_length {
            raw.push_str(&format!(
                "Content-Length: {}\r\n",
                body.len()
            ));
        }
    }

    raw.push_str("Connection: close\r\n\r\n");

    let mut bytes = raw.into_bytes();
    if let Some(body) = &request.body {
        bytes.extend_from_slice(body);
    }
    bytes
}

fn execute(
    mut connection: Connection,
    request: &Request,
) -> Result<Response, Error> {
    connection.write_all(&build_raw_request(request))?;

    let skip_body = request.method == Method::Head;
    parse_response(&mut BufReader::new(connection), skip_body)
}

fn tls_config() -> Arc<rustls::ClientConfig> {
    let root_store = rustls::RootCertStore::from_iter(
        webpki_roots::TLS_SERVER_ROOTS.iter().cloned(),
    );

    Arc::new(
        rustls::ClientConfig::builder()
            .with_root_certificates(root_store)
            .with_no_client_auth(),
    )
}

fn tls_connect(
    tcp: TcpStream,
    host: &str,
) -> Result<TlsStream, Error> {
    let config = tls_config();

    let server_name = ServerName::try_from(host.to_string())
        .map_err(|error| Error::Tls(error.to_string()))?;

    let connection =
        rustls::ClientConnection::new(config, server_name)
            .map_err(|error| Error::Tls(error.to_string()))?;

    Ok(rustls::StreamOwned::new(connection, tcp))
}

fn parse_response<R: BufRead>(
    reader: &mut R,
    skip_body: bool,
) -> Result<Response, Error> {
    let (status, status_line) = parse_status_line(reader)?;
    let headers = parse_headers(reader)?;

    let body = if skip_body {
        Vec::new()
    } else {
        read_body(reader, &headers)?
    };

    Ok(Response {
        status,
        status_line,
        headers,
        body,
    })
}

fn parse_status_line<R: BufRead>(
    reader: &mut R,
) -> Result<(u16, String), Error> {
    let mut line = String::new();
    reader.read_line(&mut line)?;

    let trimmed = line
        .trim_end_matches(['\r', '\n'])
        .to_string();
    let parts: Vec<&str> = trimmed.splitn(3, ' ').collect();
    if parts.len() < 2 {
        return Err(Error::InvalidResponse(
            "malformed status line".into(),
        ));
    }

    let status = parts[1].parse::<u16>().map_err(|_| {
        Error::InvalidResponse("invalid status code".into())
    })?;

    Ok((status, trimmed))
}

fn parse_headers<R: BufRead>(
    reader: &mut R,
) -> Result<Vec<(String, String)>, Error> {
    let mut headers = Vec::new();

    loop {
        let mut line = String::new();
        reader.read_line(&mut line)?;

        let trimmed = line.trim_end_matches(['\r', '\n']);
        if trimmed.is_empty() {
            break;
        }

        if let Some((name, value)) = trimmed.split_once(':') {
            headers.push((
                name.trim().to_lowercase(),
                value.trim().to_string(),
            ));
        }
    }

    Ok(headers)
}

fn read_body<R: BufRead>(
    reader: &mut R,
    headers: &[(String, String)],
) -> Result<Vec<u8>, Error> {
    let is_chunked = headers.iter().any(|(name, value)| {
        name == "transfer-encoding"
            && value.contains("chunked")
    });

    if is_chunked {
        return read_chunked_body(reader);
    }

    let content_length = headers
        .iter()
        .find(|(name, _)| name == "content-length")
        .and_then(|(_, value)| value.parse::<usize>().ok());

    match content_length {
        Some(length) => {
            let mut body = vec![0u8; length];
            reader.read_exact(&mut body)?;
            Ok(body)
        }
        None => {
            let mut body = Vec::new();
            reader.read_to_end(&mut body)?;
            Ok(body)
        }
    }
}

fn read_chunked_body<R: BufRead>(
    reader: &mut R,
) -> Result<Vec<u8>, Error> {
    let mut body = Vec::new();

    loop {
        let mut size_line = String::new();
        reader.read_line(&mut size_line)?;

        let size =
            usize::from_str_radix(size_line.trim(), 16).map_err(
                |_| {
                    Error::InvalidResponse(
                        "invalid chunk size".into(),
                    )
                },
            )?;

        if size == 0 {
            let mut trailer = String::new();
            reader.read_line(&mut trailer)?;
            break;
        }

        let mut chunk = vec![0u8; size];
        reader.read_exact(&mut chunk)?;
        body.extend_from_slice(&chunk);

        let mut crlf = [0u8; 2];
        reader.read_exact(&mut crlf)?;
    }

    Ok(body)
}
