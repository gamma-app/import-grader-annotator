import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, BookOpen, Loader2, Search, Copy, Check, AlertTriangle, Sparkles, RefreshCw, GitBranch, UploadCloud } from 'lucide-react'
import { api } from '../api'

const SEV = {
  P0: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  P1: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  P2: 'bg-slate-600/30 text-slate-300 border-slate-600/40',
}

function Badge({ children, className = '' }) {
  return <span className={`text-[11px] px-1.5 py-0.5 rounded border ${className}`}>{children}</span>
}

function SaveStatus({ status }) {
  if (status === 'saving')
    return (
      <span className="text-xs text-slate-400 flex items-center gap-1">
        <Loader2 size={12} className="animate-spin" /> Saving…
      </span>
    )
  if (status === 'saved') return <span className="text-xs text-emerald-400">Saved</span>
  if (status === 'error') return <span className="text-xs text-rose-400">Save failed</span>
  if (status === 'typing') return <span className="text-xs text-slate-500">Editing…</span>
  return null
}

function PromptBlock({ mode }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard?.writeText(mode.prompt || '').then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  if (mode.prompt_status === 'no_grader') {
    return (
      <div className="rounded-lg border border-slate-700/60 bg-slate-800/30 p-4 text-sm text-slate-400">
        <div className="flex items-center gap-2 text-slate-300 font-medium mb-1">
          <AlertTriangle size={14} className="text-amber-400" /> No VLM grader
        </div>
        {mode.prompt_message}
      </div>
    )
  }
  if (mode.prompt_status === 'unavailable') {
    return (
      <div className="rounded-lg border border-slate-700/60 bg-slate-800/30 p-4 text-sm text-slate-400">
        <div className="flex items-center gap-2 text-slate-300 font-medium mb-1">
          <AlertTriangle size={14} className="text-rose-400" /> Prompt unavailable
        </div>
        <p className="mb-1 break-words">{mode.prompt_message}</p>
        <p className="text-xs text-slate-500">
          Set <span className="font-mono">IMPORT_EVALS_GRADERS_DIR</span> in <span className="font-mono">.env</span> to your
          gamma checkout's <span className="font-mono">packages/import-evals/graders</span>, then restart.
        </p>
      </div>
    )
  }
  return (
    <div>
      <div className="flex items-center gap-2 mb-2 text-xs text-slate-400">
        <Sparkles size={13} className="text-indigo-400 shrink-0" />
        <span className="font-mono text-slate-300 truncate">{mode.grader_name}</span>
        {mode.model && <span className="text-slate-500 truncate">· {mode.model}</span>}
        <div className="flex-1" />
        <button
          onClick={copy}
          className="flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-slate-800 text-slate-400 shrink-0"
          title="Copy prompt"
        >
          {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="text-xs text-slate-300 bg-slate-950/60 border border-slate-800 rounded-lg p-3 overflow-auto thin-scroll whitespace-pre-wrap break-words max-h-[60vh] font-mono leading-relaxed">
        {mode.prompt}
      </pre>
    </div>
  )
}

export default function ModeDirectory({ onBack, showToast }) {
  const [data, setData] = useState(null)
  const [elementOrder, setElementOrder] = useState([])
  const [error, setError] = useState(null)
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [drafts, setDrafts] = useState({})
  const [status, setStatus] = useState('idle') // idle | typing | saving | saved | error
  const timer = useRef(null)
  const pending = useRef(null) // { id, text } awaiting save
  const [reinit, setReinit] = useState({ open: false, mode: null, count: 0 })
  const [reinitBusy, setReinitBusy] = useState(false)
  const [git, setGit] = useState(null)
  const [commitBusy, setCommitBusy] = useState(false)

  useEffect(() => {
    api
      .getModeDirectory()
      .then((r) => {
        setData(r.modes)
        setElementOrder(r.element_order || [])
        setGit(r.git || null)
        setSelectedId((prev) => prev ?? (r.modes[0] && r.modes[0].id))
      })
      .catch((e) => setError(String(e)))
  }, [])

  const flush = useCallback(() => {
    if (timer.current) {
      clearTimeout(timer.current)
      timer.current = null
    }
    const p = pending.current
    if (!p) return
    pending.current = null
    setStatus('saving')
    api
      .saveModeDescription(p.id, p.text)
      .then(() => {
        setStatus('saved')
        setData((d) => (d ? d.map((m) => (m.id === p.id ? { ...m, description: p.text } : m)) : d))
      })
      .catch((e) => {
        setStatus('error')
        showToast?.({ type: 'error', msg: String(e) })
      })
  }, [showToast])

  // Persist any pending edit when the page unmounts.
  useEffect(() => () => flush(), [flush])

  const onChange = (id, text) => {
    setDrafts((prev) => ({ ...prev, [id]: text }))
    pending.current = { id, text }
    setStatus('typing')
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(flush, 600)
  }

  const select = (id) => {
    flush() // save the previous mode's pending edit before switching
    setSelectedId(id)
    setStatus('idle')
  }

  // Like flush, but awaitable — used before reinitializing so generation reads
  // the latest saved description.
  const flushNow = async () => {
    if (timer.current) {
      clearTimeout(timer.current)
      timer.current = null
    }
    const p = pending.current
    if (!p) return
    pending.current = null
    setStatus('saving')
    try {
      await api.saveModeDescription(p.id, p.text)
      setStatus('saved')
      setData((d) => (d ? d.map((m) => (m.id === p.id ? { ...m, description: p.text } : m)) : d))
    } catch (e) {
      setStatus('error')
      showToast?.({ type: 'error', msg: String(e) })
    }
  }

  const openReinit = async (mode) => {
    await flushNow()
    let count = 0
    try {
      count = (await api.getGraderScoreCount(mode.id)).count
    } catch {
      /* non-fatal: fall back to 0 in the warning */
    }
    setReinit({ open: true, mode, count })
  }

  const doReinit = async () => {
    const mode = reinit.mode
    if (!mode) return
    setReinitBusy(true)
    try {
      const r = await api.reinitializeGrader(mode.id)
      setData((d) =>
        d
          ? d.map((m) =>
              m.id === mode.id
                ? { ...m, prompt: r.prompt, model: r.model, uncommitted: true, prompt_status: 'ok' }
                : m,
            )
          : d,
      )
      showToast?.({
        type: 'success',
        msg: `Regenerated #${mode.id} grader · cleared ${r.cleared} AI score${r.cleared === 1 ? '' : 's'}`,
      })
      setReinit({ open: false, mode: null, count: 0 })
    } catch (e) {
      showToast?.({ type: 'error', msg: String(e) })
    } finally {
      setReinitBusy(false)
    }
  }

  const doCommit = async (mode) => {
    if (!mode) return
    setCommitBusy(true)
    try {
      const r = await api.commitGrader(mode.id)
      if (r.committed && r.pushed) {
        showToast?.({ type: 'success', msg: `Committed ${r.commit_sha} & pushed to ${r.branch}` })
      } else if (r.committed && !r.pushed) {
        showToast?.({ type: 'error', msg: `Committed ${r.commit_sha} locally, but push failed: ${r.error || 'unknown error'}` })
      } else if (r.nothing_to_commit) {
        showToast?.({ type: 'success', msg: 'Already committed — nothing to push' })
      } else {
        showToast?.({ type: 'error', msg: r.error || 'Commit failed' })
      }
      if (r.committed || r.nothing_to_commit) {
        setData((d) => (d ? d.map((m) => (m.id === mode.id ? { ...m, uncommitted: false } : m)) : d))
      }
      try {
        setGit(await api.getGitStatus())
      } catch {
        /* non-fatal: leave the prior repo state */
      }
    } catch (e) {
      showToast?.({ type: 'error', msg: String(e) })
    } finally {
      setCommitBusy(false)
    }
  }

  const textFor = (m) => (drafts[m.id] !== undefined ? drafts[m.id] : m.description || '')

  const filtered = useMemo(() => {
    if (!data) return []
    const q = query.trim().toLowerCase()
    if (!q) return data
    return data.filter(
      (m) =>
        m.name.toLowerCase().includes(q) ||
        String(m.id).includes(q) ||
        (m.element || '').toLowerCase().includes(q),
    )
  }, [data, query])

  const groups = useMemo(() => {
    const order = elementOrder.length ? elementOrder : [...new Set(filtered.map((m) => m.element))]
    return order
      .map((el) => ({ element: el, items: filtered.filter((m) => m.element === el) }))
      .filter((g) => g.items.length)
  }, [filtered, elementOrder])

  const selected = data?.find((m) => m.id === selectedId) || null

  if (error) {
    return (
      <div className="h-full flex items-center justify-center p-8 text-center">
        <div className="max-w-md">
          <p className="text-rose-400 font-semibold mb-2">Couldn't load the directory</p>
          <p className="text-slate-400 text-sm">{error}</p>
        </div>
      </div>
    )
  }
  if (!data) {
    return (
      <div className="h-full flex items-center justify-center text-slate-400">
        <Loader2 className="animate-spin mr-2" size={20} /> Loading…
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-3 px-5 py-3 border-b border-slate-800">
        <button onClick={onBack} className="p-1.5 rounded hover:bg-slate-800 text-slate-300" title="Back to decks">
          <ArrowLeft size={18} />
        </button>
        <BookOpen size={18} className="text-indigo-400" />
        <h1 className="font-semibold text-slate-100">Failure Mode Directory</h1>
        <span className="text-xs text-slate-500">{data.length} modes</span>
        <div className="flex-1" />
        {git?.is_repo && (
          <div
            className="flex items-center gap-1.5 text-xs text-slate-400"
            title={
              git.has_upstream
                ? `Grader prompts are committed to ${git.branch}${git.ahead > 0 ? ` · ${git.ahead} commit(s) not yet pushed` : ' · up to date with remote'}`
                : `On ${git.branch} (no upstream tracking branch)`
            }
          >
            <GitBranch size={13} className="text-slate-500" />
            <span className="font-mono text-slate-300">{git.branch}</span>
            {git.ahead > 0 && <span className="text-amber-300">· {git.ahead} unpushed</span>}
          </div>
        )}
      </div>

      <div className="flex-1 flex min-h-0">
        {/* left: searchable list */}
        <aside className="w-72 shrink-0 border-r border-slate-800 flex flex-col min-h-0">
          <div className="p-3 border-b border-slate-800">
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search modes…"
                className="w-full bg-slate-800/80 border border-slate-700 rounded-md pl-8 pr-2 py-1.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
          <div className="flex-1 overflow-auto thin-scroll p-2">
            {groups.map((g) => (
              <div key={g.element} className="mb-3">
                <div className="text-[11px] uppercase tracking-wide text-slate-500 px-2 mb-1">{g.element}</div>
                {g.items.map((m) => {
                  const active = m.id === selectedId
                  const hasDesc = (textFor(m) || '').trim().length > 0
                  return (
                    <button
                      key={m.id}
                      onClick={() => select(m.id)}
                      className={`w-full text-left px-2 py-1.5 rounded-md mb-0.5 flex items-center gap-2 border ${
                        active ? 'bg-indigo-600/20 border-indigo-600/40' : 'border-transparent hover:bg-slate-800'
                      }`}
                    >
                      <span className="text-[11px] text-slate-500 w-5 shrink-0 text-right">{m.id}</span>
                      <span className="text-sm text-slate-200 truncate flex-1">{m.name}</span>
                      {hasDesc && (
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" title="Has a description" />
                      )}
                      {!m.grader_name && <span className="text-[10px] text-slate-500 shrink-0">no AI</span>}
                    </button>
                  )
                })}
              </div>
            ))}
            {groups.length === 0 && (
              <div className="text-sm text-slate-500 px-2 py-4 text-center">No matches</div>
            )}
          </div>
        </aside>

        {/* right: detail */}
        <section className="flex-1 overflow-auto thin-scroll min-h-0">
          {selected ? (
            <div className="max-w-3xl mx-auto p-6">
              <h2 className="text-lg font-semibold text-slate-100">
                <span className="text-slate-500 font-normal mr-2">#{selected.id}</span>
                {selected.name}
              </h2>
              <div className="flex flex-wrap items-center gap-1.5 mt-2 mb-6">
                <Badge className="bg-slate-700/40 text-slate-300 border-slate-600/40">{selected.element}</Badge>
                <Badge className="bg-slate-700/40 text-slate-300 border-slate-600/40">{selected.dimension}</Badge>
                <Badge className={SEV[selected.severity] || SEV.P2}>{selected.severity}</Badge>
                <Badge className="bg-slate-700/40 text-slate-400 border-slate-600/40">
                  {selected.level === 'deck' ? 'deck-level' : 'per-pair'}
                </Badge>
                {selected.aka && <span className="text-xs text-slate-500">· {selected.aka}</span>}
              </div>

              <div className="mb-6">
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-sm font-medium text-slate-300">Description</label>
                  <SaveStatus status={status} />
                </div>
                <textarea
                  key={selected.id}
                  value={textFor(selected)}
                  onChange={(e) => onChange(selected.id, e.target.value)}
                  onBlur={flush}
                  placeholder="Describe this failure mode… (saved automatically)"
                  rows={5}
                  className="w-full bg-slate-800/60 border border-slate-700 rounded-lg p-3 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 resize-y leading-relaxed"
                />
              </div>

              <div>
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="text-sm font-medium text-slate-300 flex items-center gap-2">
                    VLM grader prompt
                    {selected.uncommitted && (
                      <Badge className="bg-amber-500/15 text-amber-300 border-amber-500/30">uncommitted</Badge>
                    )}
                  </div>
                  {selected.grader_name && selected.prompt_status === 'ok' && (
                    <div className="flex items-center gap-2">
                      {selected.uncommitted && (
                        <button
                          onClick={() => doCommit(selected)}
                          disabled={commitBusy || reinitBusy}
                          title="Commit this prompt and push it to GitHub"
                          className="flex items-center gap-1.5 text-xs px-2 py-1 rounded border border-emerald-600/60 text-emerald-200 hover:bg-emerald-600/15 disabled:opacity-40"
                        >
                          {commitBusy ? <Loader2 size={13} className="animate-spin" /> : <UploadCloud size={13} />}
                          {commitBusy ? 'Pushing…' : 'Commit & push'}
                        </button>
                      )}
                      <button
                        onClick={() => openReinit(selected)}
                        disabled={!(textFor(selected) || '').trim() || reinitBusy || commitBusy}
                        title={
                          (textFor(selected) || '').trim()
                            ? 'Regenerate this grader prompt from the description'
                            : 'Write a description first'
                        }
                        className="flex items-center gap-1.5 text-xs px-2 py-1 rounded border border-indigo-600/60 text-indigo-200 hover:bg-indigo-600/15 disabled:opacity-40"
                      >
                        <RefreshCw size={13} /> Reinitialize from description
                      </button>
                    </div>
                  )}
                </div>
                <PromptBlock mode={selected} />
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-500 text-sm">Select a mode</div>
          )}
        </section>
      </div>

      {reinit.open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => !reinitBusy && setReinit({ open: false, mode: null, count: 0 })}
        >
          <div
            className="bg-slate-900 border border-slate-700 rounded-xl max-w-md w-full p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 mb-2 text-slate-100 font-semibold">
              <AlertTriangle size={16} className="text-amber-400" /> Reinitialize grader prompt
            </div>
            <p className="text-sm text-slate-300 mb-3">
              This rewrites the{' '}
              <span className="font-medium text-slate-100">
                #{reinit.mode?.id} {reinit.mode?.name}
              </span>{' '}
              grader prompt from its current description, and{' '}
              <span className="text-rose-300 font-medium">
                deletes all {reinit.count} AI score{reinit.count === 1 ? '' : 's'}
              </span>{' '}
              this grader has produced across all decks. They&rsquo;ll need to be re-run.
            </p>
            <p className="text-xs text-slate-500 mb-4">Human grades are not affected.</p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setReinit({ open: false, mode: null, count: 0 })}
                disabled={reinitBusy}
                className="text-sm px-3 py-1.5 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
              >
                Cancel
              </button>
              <button
                onClick={doReinit}
                disabled={reinitBusy}
                className="text-sm px-3 py-1.5 rounded border border-indigo-600 bg-indigo-600/20 text-indigo-100 hover:bg-indigo-600/30 disabled:opacity-40 flex items-center gap-1.5"
              >
                {reinitBusy ? (
                  <>
                    <Loader2 size={14} className="animate-spin" /> Generating…
                  </>
                ) : (
                  'Reinitialize'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
