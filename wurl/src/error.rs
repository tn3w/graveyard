use std::fmt;

#[derive(Debug)]
pub enum Error {
    InvalidUrl(String),
    DnsResolution(String),
    Connection(std::io::Error),
    Tls(String),
    InvalidResponse(String),
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidUrl(message) => {
                write!(f, "invalid url: {message}")
            }
            Self::DnsResolution(host) => {
                write!(f, "could not resolve host: {host}")
            }
            Self::Connection(error) => {
                write!(f, "connection failed: {error}")
            }
            Self::Tls(message) => {
                write!(f, "tls error: {message}")
            }
            Self::InvalidResponse(message) => {
                write!(f, "invalid response: {message}")
            }
        }
    }
}

impl std::error::Error for Error {}

impl From<std::io::Error> for Error {
    fn from(error: std::io::Error) -> Self {
        Self::Connection(error)
    }
}
