// Thin wrapper around the backend REST API. Vite proxies /api to FastAPI.

async function req(path, options) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  return res.json()
}

export const api = {
  getModes: () => req('/api/modes'),
  getDecks: () => req('/api/decks'),
  getDeck: (slug, variant) => req(`/api/decks/${encodeURIComponent(slug)}/${variant}`),
  rescan: () => req('/api/rescan', { method: 'POST' }),
  putPair: (slug, variant, index, modes) =>
    req(`/api/decks/${encodeURIComponent(slug)}/${variant}/pairs/${index}`, {
      method: 'PUT',
      body: JSON.stringify({ modes }),
    }),
  putDeckLevel: (slug, variant, modes) =>
    req(`/api/decks/${encodeURIComponent(slug)}/${variant}/deck-level`, {
      method: 'PUT',
      body: JSON.stringify({ modes }),
    }),
  runExport: () => req('/api/export', { method: 'POST' }),
}
