use crate::auth;
use crate::templates::*;
use actix_web::{web, HttpResponse};
use askama::Template;

pub fn configure_routes(cfg: &mut web::ServiceConfig) {
    cfg.route("/", web::get().to(index))
        .route("/login", web::get().to(login_page))
        .route("/dashboard", web::get().to(dashboard))
        .configure(auth::configure_auth_routes);
}

async fn index() -> HttpResponse {
    let template = IndexTemplate;
    HttpResponse::Ok()
        .content_type("text/html")
        .body(template.render().unwrap())
}

async fn login_page() -> HttpResponse {
    let template = LoginTemplate;
    HttpResponse::Ok()
        .content_type("text/html")
        .body(template.render().unwrap())
}

async fn dashboard() -> HttpResponse {
    let template = DashboardTemplate;
    HttpResponse::Ok()
        .content_type("text/html")
        .body(template.render().unwrap())
}
