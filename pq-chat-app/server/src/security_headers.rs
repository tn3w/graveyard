use axum::{
    body::Body,
    http::{Request, Response, header},
    middleware::Next,
};

pub async fn add_security_headers(
    request: Request<Body>,
    next: Next,
) -> Response<Body> {
    let mut response = next.run(request).await;
    
    let headers = response.headers_mut();
    
    headers.insert(
        header::CONTENT_SECURITY_POLICY,
        "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; \
         style-src 'self' 'unsafe-inline'; img-src 'self' data:; \
         connect-src 'self' ws: wss:; font-src 'self'; \
         object-src 'none'; base-uri 'self'; form-action 'self'; \
         frame-ancestors 'none'; upgrade-insecure-requests"
            .parse()
            .unwrap(),
    );
    
    headers.insert(
        header::X_FRAME_OPTIONS,
        "DENY".parse().unwrap(),
    );
    
    headers.insert(
        header::X_CONTENT_TYPE_OPTIONS,
        "nosniff".parse().unwrap(),
    );
    
    headers.insert(
        header::STRICT_TRANSPORT_SECURITY,
        "max-age=31536000; includeSubDomains; preload"
            .parse()
            .unwrap(),
    );
    
    headers.insert(
        "X-XSS-Protection",
        "1; mode=block".parse().unwrap(),
    );
    
    headers.insert(
        "Referrer-Policy",
        "strict-origin-when-cross-origin".parse().unwrap(),
    );
    
    headers.insert(
        "Permissions-Policy",
        "geolocation=(), microphone=(), camera=()"
            .parse()
            .unwrap(),
    );
    
    response
}
