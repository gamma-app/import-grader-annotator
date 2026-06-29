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

  // Drop extra output pages (1-based) so a misaligned variant lines up 1:1 with
  // input, unlocking it for grading. Destructive PDF edit (backed up once; see
  // resetAlignment to undo).
  alignDeck: (slug, variant, dropPages) =>
    req(`/api/decks/${encodeURIComponent(slug)}/${variant}/align`, {
      method: 'POST',
      body: JSON.stringify({ drop_pages: dropPages }),
    }),

  // Undo a prior align: restore the one-time backup, re-render, re-lock the deck.
  resetAlignment: (slug, variant) =>
    req(`/api/decks/${encodeURIComponent(slug)}/${variant}/align/reset`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  runExport: () => req('/api/export', { method: 'POST' }),

  // Human-vs-AI agreement report for one pair-level mode + variant.
  getModeReport: (modeId, variant) =>
    req(`/api/reports/mode/${modeId}?variant=${variant}`),

  // Failure Mode Directory: registry + grader prompts + editable descriptions.
  getModeDirectory: () => req('/api/mode-directory'),
  saveModeDescription: (modeId, text) =>
    req(`/api/modes/${modeId}/description`, {
      method: 'PUT',
      body: JSON.stringify({ text }),
    }),
  // Registry CRUD: add a custom mode, edit fields / enable-disable, hard-delete.
  createMode: (fields) => req('/api/modes', { method: 'POST', body: JSON.stringify(fields) }),
  updateMode: (modeId, fields) =>
    req(`/api/modes/${modeId}`, { method: 'PATCH', body: JSON.stringify(fields) }),
  deleteMode: (modeId) => req(`/api/modes/${modeId}`, { method: 'DELETE' }),
  getGraderScoreCount: (modeId) => req(`/api/modes/${modeId}/grader-score-count`),
  reinitializeGrader: (modeId) =>
    req(`/api/modes/${modeId}/reinitialize-grader`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  commitGrader: (modeId, message) =>
    req(`/api/modes/${modeId}/commit-grader`, {
      method: 'POST',
      body: JSON.stringify(message ? { message } : {}),
    }),
  getGitStatus: () => req('/api/git/status'),

  // --- AI graders (in-process Anthropic VLM grading) ---
  getAiStatus: () => req('/api/ai-grades/status'),
  getAiGrades: (slug, variant) =>
    req(`/api/ai-grades/${encodeURIComponent(slug)}/${variant}`),
  runAiPair: (slug, variant, index, { modes = null, force = false } = {}) =>
    req(`/api/ai-grades/${encodeURIComponent(slug)}/${variant}/pairs/${index}/run`, {
      method: 'POST',
      body: JSON.stringify({ modes, force }),
    }),

  // Bulk background runs (deck-wide or all decks for a variant).
  runAiBulk: ({ scope, variant, slug = null, force = false, modes = null }) =>
    req('/api/ai-grades/run', {
      method: 'POST',
      body: JSON.stringify({ scope, variant, slug, force, modes }),
    }),
  getAiJobs: () => req('/api/ai-grades/jobs'),
  getAiJob: (jobId) => req(`/api/ai-grades/jobs/${encodeURIComponent(jobId)}`),
  cancelAiJob: (jobId) =>
    req(`/api/ai-grades/jobs/${encodeURIComponent(jobId)}/cancel`, { method: 'POST' }),

  // --- Grader recalibration (optimize a grader prompt from human labels) ---
  // Cheap pre-run estimate (dataset/split sizes + model-call count) for the dialog.
  getRecalibrationPreview: (modeId) => req(`/api/modes/${modeId}/recalibration/preview`),
  // Restore state for a mode: the active job (if any) + the latest run summary.
  getRecalibrationState: (modeId) => req(`/api/modes/${modeId}/recalibration`),
  startRecalibration: (modeId) =>
    req(`/api/modes/${modeId}/recalibration/run`, { method: 'POST', body: JSON.stringify({}) }),
  getRecalibrationJob: (jobId) =>
    req(`/api/recalibration/jobs/${encodeURIComponent(jobId)}`),
  cancelRecalibrationJob: (jobId) =>
    req(`/api/recalibration/jobs/${encodeURIComponent(jobId)}/cancel`, { method: 'POST' }),
  // Full run record (scores, confusion matrices, flips, themes, prompt diff).
  getRecalibrationRun: (runId) =>
    req(`/api/recalibration/runs/${encodeURIComponent(runId)}`),
  adoptRecalibration: (runId) =>
    req(`/api/recalibration/runs/${encodeURIComponent(runId)}/adopt`, { method: 'POST' }),
  rejectRecalibration: (runId) =>
    req(`/api/recalibration/runs/${encodeURIComponent(runId)}/reject`, { method: 'POST' }),

  // --- PPTX import (browser-drives gamma.app to produce a 'current' pair) ---
  // Readiness for the importer (playwright + LibreOffice + a saved gamma session).
  getImportStatus: () => req('/api/imports/status'),
  // Upload a .pptx (multipart, NOT JSON) to kick off a background import job.
  startImport: ({ file, title = '', slug = '' }) => {
    const form = new FormData()
    form.append('file', file)
    if (title) form.append('title', title)
    if (slug) form.append('slug', slug)
    // Don't set Content-Type: the browser adds the multipart boundary itself.
    return fetch('/api/imports', { method: 'POST', body: form }).then(async (res) => {
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(`${res.status} ${res.statusText}: ${text}`)
      }
      return res.json()
    })
  },
  getImportJobs: () => req('/api/imports/jobs'),
  getImportJob: (jobId) => req(`/api/imports/jobs/${encodeURIComponent(jobId)}`),
  cancelImportJob: (jobId) =>
    req(`/api/imports/jobs/${encodeURIComponent(jobId)}/cancel`, { method: 'POST' }),
}
