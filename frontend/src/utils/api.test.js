import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { resolveMediaUrl } from './api';
import api from './api';

describe('resolveMediaUrl', () => {
  it('prefixes a relative media path with the server base', () => {
    expect(resolveMediaUrl('/media/timetables/x.pdf')).toBe('http://localhost:8000/media/timetables/x.pdf');
  });

  it('leaves absolute http(s) URLs untouched', () => {
    expect(resolveMediaUrl('https://cdn.example.com/x.pdf')).toBe('https://cdn.example.com/x.pdf');
    expect(resolveMediaUrl('http://example.com/x.pdf')).toBe('http://example.com/x.pdf');
  });

  it('returns falsy input as-is', () => {
    expect(resolveMediaUrl(null)).toBeNull();
    expect(resolveMediaUrl('')).toBe('');
  });
});

describe('api request wrapper', () => {
  beforeEach(() => {
    document.cookie = 'csrftoken=test-token';
    global.fetch = vi.fn();
  });

  afterEach(() => {
    document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 UTC';
    vi.restoreAllMocks();
  });

  function mockResponse({ ok = true, status = 200, body = {} }) {
    return {
      ok,
      status,
      json: () => Promise.resolve(body),
    };
  }

  it('sends the CSRF token and JSON content type for a GET', async () => {
    global.fetch.mockResolvedValue(mockResponse({ body: { hello: 'world' } }));

    const result = await api.get('/students/');

    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/students/', expect.objectContaining({
      credentials: 'include',
      headers: expect.objectContaining({
        'X-CSRFToken': 'test-token',
        'Content-Type': 'application/json',
      }),
    }));
    expect(result).toEqual({ hello: 'world' });
  });

  it('JSON-encodes a plain object body for POST', async () => {
    global.fetch.mockResolvedValue(mockResponse({ body: { id: 1 } }));

    await api.post('/students/', { name: 'Alice' });

    const [, config] = global.fetch.mock.calls[0];
    expect(config.method).toBe('POST');
    expect(config.body).toBe(JSON.stringify({ name: 'Alice' }));
  });

  it('does not set Content-Type or JSON-encode a FormData body', async () => {
    global.fetch.mockResolvedValue(mockResponse({ body: {} }));
    const formData = new FormData();
    formData.append('file', 'x');

    await api.post('/timetables/', formData);

    const [, config] = global.fetch.mock.calls[0];
    expect(config.body).toBe(formData);
    expect(config.headers['Content-Type']).toBeUndefined();
  });

  it('returns null for a 204 No Content response', async () => {
    global.fetch.mockResolvedValue(mockResponse({ status: 204, ok: true }));

    const result = await api.delete('/students/1/');

    expect(result).toBeNull();
  });

  it('throws using the error message from the response body', async () => {
    global.fetch.mockResolvedValue(mockResponse({ ok: false, status: 400, body: { error: 'Bad input' } }));

    await expect(api.get('/students/')).rejects.toThrow('Bad input');
  });

  it('falls back to detail then a generic message when the response has no error field', async () => {
    global.fetch.mockResolvedValue(mockResponse({ ok: false, status: 404, body: { detail: 'Not found' } }));
    await expect(api.get('/students/1/')).rejects.toThrow('Not found');

    global.fetch.mockResolvedValue(mockResponse({ ok: false, status: 500, body: null }));
    await expect(api.get('/students/1/')).rejects.toThrow('Request failed');
  });
});
