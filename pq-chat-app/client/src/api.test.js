import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('API Client', () => {
  let originalFetch;
  let api;

  beforeEach(async () => {
    originalFetch = global.fetch;
    global.fetch = vi.fn();
    api = await import('./api.js');
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('should handle successful response', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ data: 'value' }),
    });

    const result = await api.getCurrentUser('token123');

    expect(result).toEqual({ data: 'value' });
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/users/me',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          'Authorization': 'Bearer token123',
        }),
      })
    );
  });

  it('should handle error response', async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 401,
      text: async () => 'Unauthorized',
    });

    await expect(api.getCurrentUser('token123')).rejects.toThrow('Unauthorized');
  });

  it('should handle JSON error response', async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 400,
      text: async () => JSON.stringify({ error: 'Invalid request' }),
    });

    await expect(api.getCurrentUser('token123')).rejects.toThrow('Invalid request');
  });

  it('should handle 204 no content', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      status: 204,
      text: async () => '',
    });

    const result = await api.deleteDevice('token123', 'device1');

    expect(result).toBeNull();
  });
});
