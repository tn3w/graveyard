use actix_web::{get, post, web, HttpResponse, HttpRequest};
use actix_files::NamedFile;
use crate::{AppState, models::*, auth, database};

#[get("/")]
pub async fn index() -> actix_web::Result<NamedFile> {
    Ok(NamedFile::open("static/index.html")?)
}

#[get("/login.html")]
pub async fn login_page() -> actix_web::Result<NamedFile> {
    Ok(NamedFile::open("static/login.html")?)
}

#[get("/register.html")]
pub async fn register_page() -> actix_web::Result<NamedFile> {
    Ok(NamedFile::open("static/register.html")?)
}

#[get("/dashboard.html")]
pub async fn dashboard_page() -> actix_web::Result<NamedFile> {
    Ok(NamedFile::open("static/dashboard.html")?)
}

#[get("/iam-captcha.js")]
pub async fn serve_captcha_js() -> actix_web::Result<NamedFile> {
    Ok(NamedFile::open("static/js/iam-captcha.js")?)
}

#[get("/iam-captcha.css")]
pub async fn serve_captcha_css() -> actix_web::Result<NamedFile> {
    Ok(NamedFile::open("static/css/iam-captcha.css")?)
}

#[post("/captcha/challenge")]
pub async fn captcha_challenge(
    state: web::Data<AppState>,
    body: web::Json<serde_json::Value>,
) -> HttpResponse {
    let site_key = body.get("site_key")
        .and_then(|v| v.as_str())
        .unwrap_or("HtFBvvSKHpWEIh1JmOHnwQ4l5hTsGcvu");
    
    let response = crate::captcha::generate_challenge_with_generator(
        &state.captcha,
        &state.captcha_generator,
        site_key
    );
    HttpResponse::Ok().json(response)
}

#[post("/captcha/submit")]
pub async fn captcha_submit(
    state: web::Data<AppState>,
    body: web::Json<crate::captcha::SubmitRequest>,
) -> HttpResponse {
    match crate::captcha::verify_submission(
        &state.captcha,
        &body.token,
        &body.site_key,
        &body.answers,
    ) {
        Ok(verified_token) => HttpResponse::Ok().json(crate::captcha::SubmitResponse {
            success: true,
            verified_token: Some(verified_token),
            error: None,
        }),
        Err(e) => HttpResponse::Ok().json(crate::captcha::SubmitResponse {
            success: false,
            verified_token: None,
            error: Some(e),
        }),
    }
}

#[get("/health")]
pub async fn health_check() -> HttpResponse {
    HttpResponse::Ok().json(serde_json::json!({"status": "ok"}))
}

#[post("/register")]
pub async fn register_user(
    state: web::Data<AppState>,
    req: web::Json<RegisterRequest>
) -> HttpResponse {
    if let Some(captcha_token) = &req.captcha_token {
        match state.captcha.verify_completed(
            captcha_token,
            "HtFBvvSKHpWEIh1JmOHnwQ4l5hTsGcvu",
            120
        ) {
            Ok(true) => {},
            _ => {
                return HttpResponse::BadRequest().json(
                    serde_json::json!({"error": "Invalid captcha"})
                );
            }
        }
    }

    if let Err(e) = auth::validate_username(&req.username) {
        return HttpResponse::BadRequest().json(
            serde_json::json!({"error": e})
        );
    }
    
    if let Err(e) = auth::validate_password_strength(&req.password) {
        return HttpResponse::BadRequest().json(
            serde_json::json!({"error": e})
        );
    }
    
    let is_valid = match database::verify_registration_token(&state.db, &req.token)
        .await
    {
        Ok(valid) => valid,
        Err(_) => {
            return HttpResponse::InternalServerError().json(
                serde_json::json!({"error": "Database error"})
            );
        }
    };
    
    if !is_valid {
        return HttpResponse::Unauthorized().json(
            serde_json::json!({"error": "Invalid registration token"})
        );
    }
    
    let existing = match database::get_user_by_username(&state.db, &req.username)
        .await
    {
        Ok(user) => user,
        Err(_) => {
            return HttpResponse::InternalServerError().json(
                serde_json::json!({"error": "Database error"})
            );
        }
    };
    
    if existing.is_some() {
        return HttpResponse::Conflict().json(
            serde_json::json!({"error": "Username already exists"})
        );
    }
    
    let password_hash = match auth::hash_password(&req.password) {
        Ok(hash) => hash,
        Err(_) => {
            return HttpResponse::InternalServerError().json(
                serde_json::json!({"error": "Failed to hash password"})
            );
        }
    };
    
    let totp_secret = auth::generate_totp_secret();
    
    let _user_id = match database::create_user(
        &state.db,
        &req.username,
        &password_hash,
        &totp_secret
    ).await {
        Ok(id) => id,
        Err(_) => {
            return HttpResponse::InternalServerError().json(
                serde_json::json!({"error": "Failed to create user"})
            );
        }
    };
    
    if let Err(_) = database::mark_token_used(&state.db, &req.token).await {
        return HttpResponse::InternalServerError().json(
            serde_json::json!({"error": "Failed to mark token as used"})
        );
    }
    
    let totp_uri = auth::generate_totp_uri(
        &totp_secret,
        &req.username,
        "clouded.tn3w.dev"
    );
    
    let response = RegisterResponse {
        totp_secret: totp_secret.clone(),
        totp_uri,
        webauthn_options: serde_json::json!({}),
    };
    
    HttpResponse::Ok().json(response)
}

#[post("/verify-totp-code")]
pub async fn verify_totp_code(
    req: web::Json<serde_json::Value>
) -> HttpResponse {
    let totp_secret = match req.get("totp_secret").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => {
            return HttpResponse::BadRequest().json(
                serde_json::json!({"error": "Missing totp_secret"})
            );
        }
    };
    
    let totp_code = match req.get("totp_code").and_then(|v| v.as_str()) {
        Some(c) => c,
        None => {
            return HttpResponse::BadRequest().json(
                serde_json::json!({"error": "Missing totp_code"})
            );
        }
    };
    
    let is_valid = auth::verify_totp(totp_secret, totp_code);
    
    HttpResponse::Ok().json(serde_json::json!({
        "valid": is_valid
    }))
}

#[post("/login/step1")]
pub async fn login_step1(
    state: web::Data<AppState>,
    req: web::Json<LoginStep1Request>
) -> HttpResponse {
    if let Some(captcha_token) = &req.captcha_token {
        match state.captcha.verify_completed(
            captcha_token,
            "HtFBvvSKHpWEIh1JmOHnwQ4l5hTsGcvu",
            120
        ) {
            Ok(true) => {},
            _ => {
                return HttpResponse::Unauthorized().json(
                    serde_json::json!({"error": "Invalid captcha"})
                );
            }
        }
    }

    let user = match database::get_user_by_username(&state.db, &req.username).await {
        Ok(Some(u)) => u,
        Ok(None) => {
            return HttpResponse::Unauthorized().json(
                serde_json::json!({"error": "Invalid credentials"})
            );
        }
        Err(_) => {
            return HttpResponse::InternalServerError().json(
                serde_json::json!({"error": "Database error"})
            );
        }
    };
    
    let is_valid = match auth::verify_password(&req.password, &user.password_hash) {
        Ok(valid) => valid,
        Err(_) => {
            return HttpResponse::InternalServerError().json(
                serde_json::json!({"error": "Password verification failed"})
            );
        }
    };
    
    if !is_valid {
        return HttpResponse::Unauthorized().json(
            serde_json::json!({"error": "Invalid credentials"})
        );
    }
    
    let session_token = match auth::create_session_token(
        user.id,
        &user.username,
        &state.jwt_secret
    ) {
        Ok(token) => token,
        Err(_) => {
            return HttpResponse::InternalServerError().json(
                serde_json::json!({"error": "Failed to create session token"})
            );
        }
    };
    
    let response = LoginStep1Response {
        session_token,
        requires_totp: true,
        requires_webauthn: true,
    };
    
    HttpResponse::Ok().json(response)
}

#[post("/login/step2/totp")]
pub async fn login_step2_totp(
    state: web::Data<AppState>,
    req: web::Json<LoginStep2TotpRequest>
) -> HttpResponse {
    let session_claims = match auth::verify_session_token(
        &req.session_token,
        &state.jwt_secret
    ) {
        Ok(claims) => claims,
        Err(_) => {
            return HttpResponse::Unauthorized().json(
                serde_json::json!({"error": "Invalid session token"})
            );
        }
    };
    
    let user = match database::get_user_by_id(&state.db, session_claims.user_id).await {
        Ok(Some(u)) => u,
        Ok(None) => {
            return HttpResponse::Unauthorized().json(
                serde_json::json!({"error": "User not found"})
            );
        }
        Err(_) => {
            return HttpResponse::InternalServerError().json(
                serde_json::json!({"error": "Database error"})
            );
        }
    };
    
    if !auth::verify_totp(&user.totp_secret, &req.totp_code) {
        return HttpResponse::Unauthorized().json(
            serde_json::json!({"error": "Invalid TOTP code"})
        );
    }
    
    let access_token = match auth::create_access_token(
        user.id,
        &user.username,
        &state.jwt_secret
    ) {
        Ok(token) => token,
        Err(_) => {
            return HttpResponse::InternalServerError().json(
                serde_json::json!({"error": "Failed to create access token"})
            );
        }
    };
    
    let new_refresh_token = auth::create_refresh_token();
    let expires_at = chrono::Utc::now().timestamp() + 604800;
    
    if let Err(_) = database::store_refresh_token(
        &state.db,
        &new_refresh_token,
        user.id,
        expires_at
    ).await {
        return HttpResponse::InternalServerError().json(
            serde_json::json!({"error": "Failed to store refresh token"})
        );
    }
    
    let response = TokenResponse {
        access_token,
        refresh_token: new_refresh_token,
        token_type: "Bearer".to_string(),
        expires_in: 900,
    };
    
    HttpResponse::Ok().json(response)
}

#[post("/login/step2/webauthn/start")]
pub async fn login_step2_webauthn_start(
    state: web::Data<AppState>,
    req: web::Json<LoginStep2WebauthnStartRequest>
) -> HttpResponse {
    let _session_claims = match auth::verify_session_token(
        &req.session_token,
        &state.jwt_secret
    ) {
        Ok(claims) => claims,
        Err(_) => {
            return HttpResponse::Unauthorized().json(
                serde_json::json!({"error": "Invalid session token"})
            );
        }
    };
    
    let response = LoginStep2WebauthnStartResponse {
        options: serde_json::json!({}),
    };
    
    HttpResponse::Ok().json(response)
}

#[post("/login/step2/webauthn/finish")]
pub async fn login_step2_webauthn_finish(
    state: web::Data<AppState>,
    req: web::Json<LoginStep2WebauthnFinishRequest>
) -> HttpResponse {
    let session_claims = match auth::verify_session_token(
        &req.session_token,
        &state.jwt_secret
    ) {
        Ok(claims) => claims,
        Err(_) => {
            return HttpResponse::Unauthorized().json(
                serde_json::json!({"error": "Invalid session token"})
            );
        }
    };
    
    let user = match database::get_user_by_id(&state.db, session_claims.user_id).await {
        Ok(Some(u)) => u,
        Ok(None) => {
            return HttpResponse::Unauthorized().json(
                serde_json::json!({"error": "User not found"})
            );
        }
        Err(_) => {
            return HttpResponse::InternalServerError().json(
                serde_json::json!({"error": "Database error"})
            );
        }
    };
    
    let access_token = match auth::create_access_token(
        user.id,
        &user.username,
        &state.jwt_secret
    ) {
        Ok(token) => token,
        Err(_) => {
            return HttpResponse::InternalServerError().json(
                serde_json::json!({"error": "Failed to create access token"})
            );
        }
    };
    
    let new_refresh_token = auth::create_refresh_token();
    let expires_at = chrono::Utc::now().timestamp() + 604800;
    
    if let Err(_) = database::store_refresh_token(
        &state.db,
        &new_refresh_token,
        user.id,
        expires_at
    ).await {
        return HttpResponse::InternalServerError().json(
            serde_json::json!({"error": "Failed to store refresh token"})
            );
    }
    
    let response = TokenResponse {
        access_token,
        refresh_token: new_refresh_token,
        token_type: "Bearer".to_string(),
        expires_in: 900,
    };
    
    HttpResponse::Ok().json(response)
}

#[post("/refresh")]
pub async fn refresh_token(
    state: web::Data<AppState>,
    req: web::Json<RefreshTokenRequest>
) -> HttpResponse {
    let stored_token = match database::get_refresh_token(
        &state.db,
        &req.refresh_token
    ).await {
        Ok(Some(token)) => token,
        Ok(None) => {
            return HttpResponse::Unauthorized().json(
                serde_json::json!({"error": "Invalid refresh token"})
            );
        }
        Err(_) => {
            return HttpResponse::InternalServerError().json(
                serde_json::json!({"error": "Database error"})
            );
        }
    };
    
    let now = chrono::Utc::now().timestamp();
    if stored_token.expires_at < now {
        let _ = database::delete_refresh_token(&state.db, &req.refresh_token).await;
        return HttpResponse::Unauthorized().json(
            serde_json::json!({"error": "Refresh token expired"})
        );
    }
    
    let user = match database::get_user_by_id(&state.db, stored_token.user_id).await {
        Ok(Some(u)) => u,
        Ok(None) => {
            return HttpResponse::Unauthorized().json(
                serde_json::json!({"error": "User not found"})
            );
        }
        Err(_) => {
            return HttpResponse::InternalServerError().json(
                serde_json::json!({"error": "Database error"})
            );
        }
    };
    
    let access_token = match auth::create_access_token(
        user.id,
        &user.username,
        &state.jwt_secret
    ) {
        Ok(token) => token,
        Err(_) => {
            return HttpResponse::InternalServerError().json(
                serde_json::json!({"error": "Failed to create access token"})
            );
        }
    };
    
    let response = TokenResponse {
        access_token,
        refresh_token: req.refresh_token.clone(),
        token_type: "Bearer".to_string(),
        expires_in: 900,
    };
    
    HttpResponse::Ok().json(response)
}

#[get("/protected")]
pub async fn protected_route(
    state: web::Data<AppState>,
    req: HttpRequest
) -> HttpResponse {
    let auth_header = match req.headers().get("Authorization") {
        Some(header) => header,
        None => {
            return HttpResponse::Unauthorized().json(
                serde_json::json!({"error": "Missing authorization header"})
            );
        }
    };
    
    let auth_str = match auth_header.to_str() {
        Ok(s) => s,
        Err(_) => {
            return HttpResponse::Unauthorized().json(
                serde_json::json!({"error": "Invalid authorization header"})
            );
        }
    };
    
    if !auth_str.starts_with("Bearer ") {
        return HttpResponse::Unauthorized().json(
            serde_json::json!({"error": "Invalid authorization format"})
        );
    }
    
    let token = &auth_str[7..];
    
    let claims = match auth::verify_access_token(token, &state.jwt_secret) {
        Ok(c) => c,
        Err(_) => {
            return HttpResponse::Unauthorized().json(
                serde_json::json!({"error": "Invalid or expired token"})
            );
        }
    };
    
    HttpResponse::Ok().json(serde_json::json!({
        "message": "Access granted",
        "username": claims.sub
    }))
}
