//! macOS keychain integration for the BYOK LLMConfig.
//!
//! The desktop side is the single owner of the user's LLM config. It stores
//! the full config as a single opaque JSON string in the macOS keychain and
//! exposes three Tauri commands:
//!   - `save_llm_config(config_json)`
//!   - `load_llm_config() -> Option<String>`
//!   - `delete_llm_config()`
//!
//! The keychain entry is pinned to (service = "com.eatit.desktop",
//! account = "llm-config"). The backend never sees the raw secret; it only
//! receives a base64-encoded copy in the `X-LLM-Config` HTTP header on each
//! request.

use keyring::Entry;
use thiserror::Error;

const SERVICE: &str = "com.eatit.desktop";
const ACCOUNT: &str = "llm-config";

#[derive(Debug, Error)]
pub enum KeychainError {
    #[error("keychain access failed: {0}")]
    Backend(#[from] keyring::Error),
}

impl serde::Serialize for KeychainError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(&self.to_string())
    }
}

fn entry() -> Result<Entry, KeychainError> {
    Ok(Entry::new(SERVICE, ACCOUNT)?)
}

#[tauri::command]
pub fn save_llm_config(config: String) -> Result<(), KeychainError> {
    entry()?.set_password(&config)?;
    Ok(())
}

#[tauri::command]
pub fn load_llm_config() -> Result<Option<String>, KeychainError> {
    match entry()?.get_password() {
        Ok(value) => Ok(Some(value)),
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(other) => Err(KeychainError::Backend(other)),
    }
}

#[tauri::command]
pub fn delete_llm_config() -> Result<(), KeychainError> {
    match entry()?.delete_credential() {
        Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
        Err(other) => Err(KeychainError::Backend(other)),
    }
}
