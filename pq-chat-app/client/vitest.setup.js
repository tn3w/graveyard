import 'fake-indexeddb/auto';
import { vi } from 'vitest';

vi.mock('./src/wasm/chat_client_wasm.js', () => {
  return import('./vitest.wasm-mock.js');
});
