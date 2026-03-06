use crate::deployment::config::Configuration;
use crate::deployment::errors::ConfigError;
use std::fs;
use std::path::Path;
use tokio::fs as async_fs;

pub async fn save_configuration(
    configuration: &Configuration,
    path: &Path,
) -> Result<(), ConfigError> {
    configuration.validate()?;

    let toml_string = toml::to_string_pretty(configuration).map_err(|error| {
        ConfigError::SerializationFailed(format!(
            "Failed to serialize configuration: {}",
            error
        ))
    })?;

    let temp_path = path.with_extension("tmp");

    async_fs::write(&temp_path, toml_string.as_bytes())
        .await
        .map_err(|error| {
            ConfigError::FileIoError(format!(
                "Failed to write temporary file: {}",
                error
            ))
        })?;

    async_fs::rename(&temp_path, path).await.map_err(|error| {
        ConfigError::FileIoError(format!("Failed to rename file: {}", error))
    })?;

    Ok(())
}

pub async fn load_configuration(
    path: &Path,
) -> Result<Configuration, ConfigError> {
    if !path.exists() {
        return Ok(Configuration::default());
    }

    let content = async_fs::read_to_string(path).await.map_err(|error| {
        ConfigError::FileIoError(format!("Failed to read file: {}", error))
    })?;

    let configuration: Configuration =
        toml::from_str(&content).map_err(|error| {
            ConfigError::DeserializationFailed(format!(
                "Failed to deserialize configuration: {}",
                error
            ))
        })?;

    configuration.validate().map_err(|_| ConfigError::CorruptedFile)?;

    Ok(configuration)
}

pub fn save_configuration_sync(
    configuration: &Configuration,
    path: &Path,
) -> Result<(), ConfigError> {
    configuration.validate()?;

    let toml_string = toml::to_string_pretty(configuration).map_err(|error| {
        ConfigError::SerializationFailed(format!(
            "Failed to serialize configuration: {}",
            error
        ))
    })?;

    let temp_path = path.with_extension("tmp");

    fs::write(&temp_path, toml_string.as_bytes()).map_err(|error| {
        ConfigError::FileIoError(format!(
            "Failed to write temporary file: {}",
            error
        ))
    })?;

    fs::rename(&temp_path, path).map_err(|error| {
        ConfigError::FileIoError(format!("Failed to rename file: {}", error))
    })?;

    Ok(())
}

pub fn load_configuration_sync(path: &Path) -> Result<Configuration, ConfigError> {
    if !path.exists() {
        return Ok(Configuration::default());
    }

    let content = fs::read_to_string(path).map_err(|error| {
        ConfigError::FileIoError(format!("Failed to read file: {}", error))
    })?;

    let configuration: Configuration =
        toml::from_str(&content).map_err(|error| {
            ConfigError::DeserializationFailed(format!(
                "Failed to deserialize configuration: {}",
                error
            ))
        })?;

    configuration.validate().map_err(|_| ConfigError::CorruptedFile)?;

    Ok(configuration)
}
