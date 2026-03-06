import { describe, it, expect, beforeEach } from 'vitest';
import { ratchetStorage } from './ratchet-storage.js';

describe('RatchetStorage', () => {
  beforeEach(async () => {
    await ratchetStorage.clearAll();
  });

  it('saves and loads ratchet state', async () => {
    const conversationId = 'conv-123';
    const stateJson = JSON.stringify({ test: 'data', value: 42 });

    await ratchetStorage.saveState(conversationId, stateJson);
    const loaded = await ratchetStorage.loadState(conversationId);

    expect(loaded).toBe(stateJson);
  });

  it('returns null for nonexistent state', async () => {
    const loaded = await ratchetStorage.loadState('nonexistent');
    expect(loaded).toBeNull();
  });

  it('overwrites existing state', async () => {
    const conversationId = 'conv-123';
    const state1 = JSON.stringify({ version: 1 });
    const state2 = JSON.stringify({ version: 2 });

    await ratchetStorage.saveState(conversationId, state1);
    await ratchetStorage.saveState(conversationId, state2);

    const loaded = await ratchetStorage.loadState(conversationId);
    expect(loaded).toBe(state2);
  });

  it('deletes state', async () => {
    const conversationId = 'conv-123';
    const stateJson = JSON.stringify({ test: 'data' });

    await ratchetStorage.saveState(conversationId, stateJson);
    await ratchetStorage.deleteState(conversationId);

    const loaded = await ratchetStorage.loadState(conversationId);
    expect(loaded).toBeNull();
  });

  it('lists all conversation IDs', async () => {
    await ratchetStorage.saveState('conv-1', '{"a":1}');
    await ratchetStorage.saveState('conv-2', '{"b":2}');
    await ratchetStorage.saveState('conv-3', '{"c":3}');

    const ids = await ratchetStorage.getAllConversationIds();
    expect(ids).toHaveLength(3);
    expect(ids).toContain('conv-1');
    expect(ids).toContain('conv-2');
    expect(ids).toContain('conv-3');
  });

  it('clears all states', async () => {
    await ratchetStorage.saveState('conv-1', '{"a":1}');
    await ratchetStorage.saveState('conv-2', '{"b":2}');

    await ratchetStorage.clearAll();

    const ids = await ratchetStorage.getAllConversationIds();
    expect(ids).toHaveLength(0);
  });
});
