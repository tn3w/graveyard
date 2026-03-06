use actix_web::{web, App, HttpServer, middleware};
use actix_cors::Cors;
use std::sync::Arc;
use clouded::{AppState, captcha, database};

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let db = database::init_database().await.expect("Failed to init database");
    
    let jwt_secret = std::env::var("JWT_SECRET")
        .unwrap_or_else(|_| uuid::Uuid::new_v4().to_string());
    
    let rp_id = "clouded.tn3w.dev";
    let rp_origin = url::Url::parse("https://clouded.tn3w.dev")
        .expect("Invalid origin URL");
    
    let builder = webauthn_rs::WebauthnBuilder::new(rp_id, &rp_origin)
        .expect("Invalid WebAuthn configuration");
    let webauthn = Arc::new(builder.build().expect("Failed to build WebAuthn"));
    
    let captcha_generator = captcha::CaptchaGenerator::new();
    let mut captcha_generator_mut = captcha_generator;
    if !captcha_generator_mut.setup() {
        eprintln!("Warning: Failed to initialize captcha icon cache");
    }
    
    let state = AppState {
        db: db.clone(),
        jwt_secret: jwt_secret.clone(),
        webauthn,
        captcha: Arc::new(captcha::CaptchaCrypto::new(&jwt_secret)),
        captcha_generator: Arc::new(captcha_generator_mut),
    };
    
    let registration_token = database::ensure_registration_token(&db)
        .await
        .expect("Failed to create registration token");
    
    if let Some(token) = registration_token {
        println!("Registration URL: http://localhost:8080/register.html?token={}", token);
    }
    
    println!("Server running at http://localhost:8080");
    
    HttpServer::new(move || {
        let cors = Cors::permissive();
        
        App::new()
            .app_data(web::Data::new(state.clone()))
            .wrap(middleware::Logger::default())
            .wrap(cors)
            .service(actix_files::Files::new("/static", "static"))
            .service(clouded::handlers::serve_captcha_js)
            .service(clouded::handlers::serve_captcha_css)
            .service(clouded::handlers::captcha_challenge)
            .service(clouded::handlers::captcha_submit)
            .service(clouded::handlers::health_check)
            .service(clouded::handlers::register_user)
            .service(clouded::handlers::verify_totp_code)
            .service(clouded::handlers::login_step1)
            .service(clouded::handlers::login_step2_totp)
            .service(clouded::handlers::login_step2_webauthn_start)
            .service(clouded::handlers::login_step2_webauthn_finish)
            .service(clouded::handlers::refresh_token)
            .service(clouded::handlers::protected_route)
            .service(clouded::handlers::index)
            .service(clouded::handlers::login_page)
            .service(clouded::handlers::register_page)
            .service(clouded::handlers::dashboard_page)
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}
