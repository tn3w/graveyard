ALTER TABLE messages ADD COLUMN routing_token TEXT;
ALTER TABLE messages ADD COLUMN sealed_sender_version INTEGER DEFAULT 1;

UPDATE messages SET routing_token = id WHERE routing_token IS NULL;

CREATE INDEX idx_messages_routing_token ON messages(routing_token);

PRAGMA foreign_keys=off;

CREATE TABLE messages_new (
  id TEXT PRIMARY KEY,
  recipient_device_id TEXT,
  encrypted_content BLOB NOT NULL,
  created_at INTEGER NOT NULL,
  edited_at INTEGER,
  conversation_id TEXT,
  group_id TEXT,
  routing_token TEXT,
  sealed_sender_version INTEGER DEFAULT 1,
  FOREIGN KEY (recipient_device_id) REFERENCES devices(id) ON DELETE CASCADE,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
  FOREIGN KEY (group_id) REFERENCES group_chats(id) ON DELETE CASCADE
);

INSERT INTO messages_new SELECT 
  id, recipient_device_id, encrypted_content, created_at, edited_at, 
  conversation_id, group_id, routing_token, sealed_sender_version
FROM messages;

DROP TABLE messages;

ALTER TABLE messages_new RENAME TO messages;

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_group ON messages(group_id);
CREATE INDEX idx_messages_recipient ON messages(recipient_device_id);
CREATE INDEX idx_messages_recipient_created ON messages(recipient_device_id, created_at DESC);
CREATE INDEX idx_messages_created ON messages(created_at DESC);
CREATE INDEX idx_messages_routing_token ON messages(routing_token);

PRAGMA foreign_keys=on;

