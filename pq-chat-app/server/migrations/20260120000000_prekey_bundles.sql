CREATE TABLE IF NOT EXISTS prekey_bundles (
  device_id TEXT PRIMARY KEY,
  identity_key BLOB NOT NULL,
  signed_prekey BLOB NOT NULL,
  signed_prekey_signature BLOB NOT NULL,
  signed_prekey_timestamp INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS one_time_prekeys (
  id TEXT PRIMARY KEY,
  device_id TEXT NOT NULL,
  prekey BLOB NOT NULL,
  created_at INTEGER NOT NULL,
  consumed_at INTEGER,
  FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

CREATE INDEX idx_one_time_prekeys_device 
  ON one_time_prekeys(device_id);
CREATE INDEX idx_one_time_prekeys_consumed 
  ON one_time_prekeys(consumed_at);
CREATE INDEX idx_one_time_prekeys_available 
  ON one_time_prekeys(device_id, consumed_at) 
  WHERE consumed_at IS NULL;
