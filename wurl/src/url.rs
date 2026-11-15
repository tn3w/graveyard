use crate::Error;

#[derive(Debug, Clone)]
pub struct Url {
    pub scheme: Scheme,
    pub host: String,
    pub port: u16,
    pub path: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Scheme {
    Http,
    Https,
}

impl Url {
    pub fn parse(input: &str) -> Result<Self, Error> {
        let (scheme, rest) = parse_scheme(input)?;

        let rest = rest
            .strip_prefix("://")
            .ok_or_else(|| invalid("missing ://"))?;

        let (authority, path) = match rest.find('/') {
            Some(index) => (&rest[..index], &rest[index..]),
            None => (rest, "/"),
        };

        let (host, port) = parse_authority(authority, scheme)?;

        Ok(Url {
            scheme,
            host,
            port,
            path: path.to_string(),
        })
    }

    pub fn host_header(&self) -> String {
        let default_port = match self.scheme {
            Scheme::Http => 80,
            Scheme::Https => 443,
        };

        if self.port == default_port {
            self.host.clone()
        } else {
            format!("{}:{}", self.host, self.port)
        }
    }
}

fn parse_scheme(input: &str) -> Result<(Scheme, &str), Error> {
    if let Some(rest) = input.strip_prefix("https") {
        return Ok((Scheme::Https, rest));
    }

    if let Some(rest) = input.strip_prefix("http") {
        return Ok((Scheme::Http, rest));
    }

    Err(invalid("unsupported scheme, use http or https"))
}

fn parse_authority(
    authority: &str,
    scheme: Scheme,
) -> Result<(String, u16), Error> {
    let (host, port_str) = match authority.rfind(':') {
        Some(index) => (&authority[..index], Some(&authority[index + 1..])),
        None => (authority, None),
    };

    if host.is_empty() {
        return Err(invalid("empty host"));
    }

    let default_port = match scheme {
        Scheme::Http => 80,
        Scheme::Https => 443,
    };

    let port = match port_str {
        Some(p) => p
            .parse::<u16>()
            .map_err(|_| invalid("invalid port number"))?,
        None => default_port,
    };

    Ok((host.to_string(), port))
}

fn invalid(message: &str) -> Error {
    Error::InvalidUrl(message.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_https_url() {
        let url = Url::parse("https://example.com/path").unwrap();
        assert_eq!(url.scheme, Scheme::Https);
        assert_eq!(url.host, "example.com");
        assert_eq!(url.port, 443);
        assert_eq!(url.path, "/path");
    }

    #[test]
    fn parse_http_with_port() {
        let url = Url::parse("http://localhost:8080/api").unwrap();
        assert_eq!(url.scheme, Scheme::Http);
        assert_eq!(url.host, "localhost");
        assert_eq!(url.port, 8080);
        assert_eq!(url.path, "/api");
    }

    #[test]
    fn parse_url_without_path() {
        let url = Url::parse("https://example.com").unwrap();
        assert_eq!(url.path, "/");
    }

    #[test]
    fn host_header_default_port() {
        let url = Url::parse("https://example.com/").unwrap();
        assert_eq!(url.host_header(), "example.com");
    }

    #[test]
    fn host_header_custom_port() {
        let url = Url::parse("https://example.com:8443/").unwrap();
        assert_eq!(url.host_header(), "example.com:8443");
    }
}
