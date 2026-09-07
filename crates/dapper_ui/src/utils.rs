use egui::Id;
use std::sync::atomic::{AtomicU64, Ordering};

/// A thread-safe utility generator for creating unique widget IDs and salts across UI panes.
#[derive(Debug, Default)]
pub struct WidgetIdGenerator {
    counter: AtomicU64,
}

impl WidgetIdGenerator {
    pub fn new() -> Self {
        Self {
            counter: AtomicU64::new(0),
        }
    }

    /// Generates a unique string salt given a namespace scope tag.
    pub fn next_salt(&self, scope: &str) -> String {
        let count = self.counter.fetch_add(1, Ordering::Relaxed);
        format!("{}_{}", scope, count)
    }

    /// Generates a unique egui::Id given a namespace scope tag.
    pub fn next_id(&self, scope: &str) -> Id {
        Id::new(self.next_salt(scope))
    }
}

/// Creates a deterministic, unique string salt combining a domain scope tag and item ID/key.
pub fn make_unique_salt(scope: &str, key: impl std::fmt::Display) -> String {
    format!("{}_{}", scope, key)
}

/// Creates a deterministic, unique egui::Id combining a domain scope tag and item ID/key.
pub fn make_unique_id(scope: &str, key: impl std::fmt::Display) -> Id {
    Id::new(make_unique_salt(scope, key))
}
