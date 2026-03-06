use reqwest::Client;
use std::time::Duration;

pub struct TlsClient {
    client: Client,
}

impl TlsClient {
    pub fn new() -> Result<Self, reqwest::Error> {
        let client = Client::builder()
            .use_rustls_tls()
            .timeout(Duration::from_secs(30))
            .build()?;

        Ok(Self { client })
    }

    pub fn client(&self) -> &Client {
        &self.client
    }
}

impl Default for TlsClient {
    fn default() -> Self {
        Self::new().expect("Failed to create TLS client")
    }
}

pub struct GitHubApiClient {
    tls_client: TlsClient,
    base_url: String,
}

impl GitHubApiClient {
    pub fn new() -> Result<Self, reqwest::Error> {
        Ok(Self {
            tls_client: TlsClient::new()?,
            base_url: "https://api.github.com".to_string(),
        })
    }

    pub fn client(&self) -> &Client {
        self.tls_client.client()
    }

    pub fn base_url(&self) -> &str {
        &self.base_url
    }
}

impl Default for GitHubApiClient {
    fn default() -> Self {
        Self::new().expect("Failed to create GitHub API client")
    }
}

pub struct CloudflareApiClient {
    tls_client: TlsClient,
    base_url: String,
}

impl CloudflareApiClient {
    pub fn new() -> Result<Self, reqwest::Error> {
        Ok(Self {
            tls_client: TlsClient::new()?,
            base_url: "https://api.cloudflare.com/client/v4".to_string(),
        })
    }

    pub fn client(&self) -> &Client {
        self.tls_client.client()
    }

    pub fn base_url(&self) -> &str {
        &self.base_url
    }
}

impl Default for CloudflareApiClient {
    fn default() -> Self {
        Self::new().expect("Failed to create Cloudflare API client")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_tls_client() {
        let client = TlsClient::new();
        assert!(client.is_ok());
    }

    #[test]
    fn test_create_github_api_client() {
        let client = GitHubApiClient::new();
        assert!(client.is_ok());
    }

    #[test]
    fn test_create_cloudflare_api_client() {
        let client = CloudflareApiClient::new();
        assert!(client.is_ok());
    }

    #[test]
    fn test_github_api_client_base_url() {
        let client = GitHubApiClient::new().unwrap();
        assert_eq!(client.base_url(), "https://api.github.com");
    }

    #[test]
    fn test_cloudflare_api_client_base_url() {
        let client = CloudflareApiClient::new().unwrap();
        assert_eq!(
            client.base_url(),
            "https://api.cloudflare.com/client/v4"
        );
    }
}
