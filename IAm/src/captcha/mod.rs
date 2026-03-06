//! CAPTCHA Widget Service - IAm Captcha
//!
//! A self-hosted captcha service similar to hCaptcha where users must identify
//! which scene contains the target icon above the fullest cup.
//!
//! Supports passive mode (99.9% invisible) which analyzes browser fingerprints
//! and user behavior to verify humans without visual challenges.

pub mod crypto;
pub mod generator;
pub mod handlers;
pub mod passive;

pub use handlers::{configure_captcha_routes, CaptchaState};
pub use passive::{configure_passive_routes, PassiveModeConfig, PassiveState};
