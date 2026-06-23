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

  // --- AI graders (import-evals via eval-server) ---
  getAiStatus: () => req('/api/ai-grades/status'),
  getAiGrades: (slug, variant) =>
    req(`/api/ai-grades/${encodeURIComponent(slug)}/${variant}`),
  runAiPair: (slug, variant, index, { modes = null, force = false } = {}) =>
    req(`/api/ai-grades/${encodeURIComponent(slug)}/${variant}/pairs/${index}/run`, {
      method: 'POST',
      body: JSON.stringify({ modes, force }),
    }),

  // Bulk background runs (deck-wide or all decks for a variant).
  runAiBulk: ({ scope, variant, slug = null, force = false }) =>
    req('/api/ai-grades/run', {
      method: 'POST',
      body: JSON.stringify({ scope, variant, slug, force }),
    }),
  getAiJobs: () => req('/api/ai-grades/jobs'),
  getAiJob: (jobId) => req(`/api/ai-grades/jobs/${encodeURIComponent(jobId)}`),
  cancelAiJob: (jobId) =>
    req(`/api/ai-grades/jobs/${encodeURIComponent(jobId)}/cancel`, { method: 'POST' }),
}
