import { useEffect, useState, useRef } from 'react'
import { AlertTriangle, RefreshCw, Loader2, ChevronRight, ChevronDown, Sparkles, Scissors } from 'lucide-react'
import { api } from '../api'
import AiStatusDot from './AiStatusDot.jsx'
import ImportPanel from './ImportPanel.jsx'

function ProgressBar({ done, total }) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0
  return (
    <div>
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>{done}/{total} pairs reviewed</span>
        <span>{pct}%</span>
      </div>
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${pct === 100 ? 'bg-emerald-500' : 'bg-indigo-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

function DeckCard({ d, stats, onOpen, onAlign, aiReady, jobActive, activeSlug, onRunDeck }) {
  const openable = stats.available && stats.pair_count > 0
  const canAlign = stats.misaligned && stats.output_count > stats.input_count
  const aiPct = stats.ai_total > 0 ? Math.round((stats.ai_graded / stats.ai_total) * 100) : 0
  const grading = activeSlug === d.slug
  return (
    <div
      onClick={() => openable && onOpen(d.slug)}
      role={openable ? 'button' : undefined}
      tabIndex={openable ? 0 : undefined}
      onKeyDown={(e) => {
        if (openable && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          onOpen(d.slug)
        }
      }}
      className={`text-left bg-slate-900 border rounded-lg p-4 transition group w-full ${
        openable ? 'cursor-pointer border-slate-800 hover:border-indigo-600' : 'border-slate-800 opacity-60'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0">
          <h2 className="font-medium text-slate-100 leading-tight truncate">{d.title}</h2>
          <p className="text-xs text-slate-500 mt-0.5 truncate">{d.slug}</p>
        </div>
        {openable && (
          <ChevronRight size={18} className="text-slate-600 group-hover:text-indigo-400 shrink-0" />
        )}
      </div>

      <ProgressBar done={stats.reviewed_count} total={stats.pair_count} />

      {canAlign && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            onAlign(d.slug)
          }}
          className="mt-3 w-full flex items-center justify-center gap-1.5 text-xs px-2 py-1.5 rounded border border-amber-500/60 text-amber-200 hover:bg-amber-500/10"
        >
          <Scissors size={13} /> Align deck
        </button>
      )}

      {openable && !stats.misaligned && (
        <div className="mt-3 flex items-end gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex justify-between text-[11px] text-slate-500 mb-1">
              <span className="flex items-center gap-1">
                <Sparkles size={11} className="text-indigo-400" /> AI {stats.ai_graded}/{stats.ai_total}
                {stats.ai_errors > 0 && <span className="text-rose-400"> · {stats.ai_errors} err</span>}
              </span>
              <span>{aiPct}%</span>
            </div>
            <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full rounded-full bg-indigo-400/70" style={{ width: `${aiPct}%` }} />
            </div>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onRunDeck(d.slug)
            }}
            disabled={!aiReady || jobActive}
            title={aiReady ? 'Grade this whole deck with AI' : 'AI grader unavailable — set ANTHROPIC_API_KEY in .env'}
            className="shrink-0 flex items-center gap-1 whitespace-nowrap text-[11px] px-2 py-1 rounded border border-indigo-600/60 text-indigo-200 hover:bg-indigo-600/15 disabled:opacity-40"
          >
            {grading ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
            {grading ? 'Grading' : 'Run AI'}
          </button>
        </div>
      )}

      <div className="flex flex-wrap gap-1.5 mt-3">
        {stats.misaligned && (
          <span className="flex items-center gap-1 text-xs px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30">
            <AlertTriangle size={12} /> {stats.input_count}≠{stats.output_count}
          </span>
        )}
        {!stats.rendered && stats.available && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-slate-700/40 text-slate-300 border border-slate-600/40">
            opens on first view
          </span>
        )}
      </div>
    </div>
  )
}

export default function Dashboard({ variant, onOpen, onAlign, showToast }) {
  const [decks, setDecks] = useState(null)
  const [busy, setBusy] = useState(false)
  const [showMisaligned, setShowMisaligned] = useState(false)
  const [aiStatus, setAiStatus] = useState(null)
  const [job, setJob] = useState(null)
  const pollRef = useRef(null)

  const aiReady = !!(aiStatus && aiStatus.llm_configured && aiStatus.graders_dir_ok)
  const jobActive = !!(job && (job.status === 'running' || job.status === 'cancelling'))

  const load = () =>
    api.getDecks().then((r) => setDecks(r.decks)).catch((e) => showToast({ type: 'error', msg: String(e) }))

  useEffect(() => {
    load()
    api.getAiStatus().then(setAiStatus).catch(() => {})
    api
      .getAiJobs()
      .then((r) => {
        if (r.active) {
          setJob(r.active)
          startPoll(r.active.id)
        }
      })
      .catch(() => {})
    return () => stopPoll()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const onRescan = async () => {
    setBusy(true)
    try {
      const r = await api.rescan()
      setDecks(r.decks)
      showToast({ type: 'success', msg: `Rescanned ${r.rescanned} decks` })
    } catch (e) {
      showToast({ type: 'error', msg: String(e) })
    } finally {
      setBusy(false)
    }
  }

  // ----- AI bulk runs (background jobs)
  const stopPoll = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  const startPoll = (jobId) => {
    stopPoll()
    pollRef.current = setInterval(async () => {
      try {
        const j = await api.getAiJob(jobId)
        setJob(j)
        if (j.status !== 'running' && j.status !== 'cancelling') {
          stopPoll()
          load()
          showToast({
            type: j.status === 'error' ? 'error' : 'success',
            msg: `AI run ${j.status} — ${j.cells} cells graded${j.errors ? `, ${j.errors} errors` : ''}`,
          })
        }
      } catch {
        stopPoll()
      }
    }, 1500)
  }

  const startRun = async (scope, slug = null) => {
    const inScope = (decks || []).filter(
      (d) => d.variants[variant]?.available && (scope === 'all' || d.slug === slug),
    )
    const pairs = inScope.reduce((n, d) => n + (d.variants[variant].pair_count || 0), 0)
    const remaining = inScope.reduce(
      (n, d) => n + Math.max(0, (d.variants[variant].ai_total || 0) - (d.variants[variant].ai_graded || 0)),
      0,
    )
    if (!pairs) {
      showToast({ type: 'error', msg: 'Nothing to grade for this scope/variant.' })
      return
    }
    const label = scope === 'all' ? `all ${inScope.length} available deck(s)` : inScope[0]?.title || slug
    const ok = window.confirm(
      `Run AI graders on ${label} · variant "${variant}".\n\n` +
        `${pairs} pairs · ~${remaining} grader runs to do (already-graded slides are skipped).\n\n` +
        `Runs in the background — you can keep grading. Continue?`,
    )
    if (!ok) return
    try {
      const j = await api.runAiBulk({ scope, variant, slug })
      setJob(j)
      if (j.status === 'running' || j.status === 'cancelling') startPoll(j.id)
      else load()
    } catch (e) {
      showToast({ type: 'error', msg: String(e) })
    }
  }

  const cancelRun = async () => {
    if (!job) return
    try {
      setJob(await api.cancelAiJob(job.id))
    } catch (e) {
      showToast({ type: 'error', msg: String(e) })
    }
  }

  if (!decks) {
    return (
      <div className="h-full flex items-center justify-center text-slate-400">
        <Loader2 className="animate-spin mr-2" size={20} /> Loading decks…
      </div>
    )
  }

  const withStats = decks.map((d) => ({ d, stats: d.variants[variant] }))
  const available = withStats.filter((x) => x.stats.available)
  const aligned = available.filter((x) => !x.stats.misaligned)
  const misaligned = available.filter((x) => x.stats.misaligned)

  return (
    <div className="h-full overflow-auto thin-scroll p-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-lg font-semibold text-slate-100">Decks</h1>
            <p className="text-sm text-slate-400">
              {aligned.length} aligned
              {misaligned.length > 0 ? ` · ${misaligned.length} misaligned` : ''}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 text-xs text-slate-400 mr-1">
              <AiStatusDot status={aiStatus} /> AI
            </span>
            <button
              onClick={() => startRun('all')}
              disabled={!aiReady || jobActive}
              title={aiReady ? 'Grade every available deck for this variant' : 'AI grader unavailable — set ANTHROPIC_API_KEY in .env'}
              className="flex items-center gap-2 text-sm border border-indigo-600 text-indigo-200 hover:bg-indigo-600/15 disabled:opacity-40 px-3 py-1.5 rounded"
            >
              {jobActive && job?.scope === 'all' ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Sparkles size={16} />
              )}
              Run AI · all
            </button>
            <ImportPanel onImported={load} showToast={showToast} />
            <button
              onClick={onRescan}
              disabled={busy}
              className="flex items-center gap-2 text-sm border border-slate-700 hover:bg-slate-800 disabled:opacity-50 px-3 py-1.5 rounded text-slate-200"
            >
              {busy ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
              Rescan / re-render
            </button>
          </div>
        </div>

        {job && jobActive && (
          <div className="mb-5 rounded-lg border border-indigo-700/50 bg-indigo-950/30 p-3">
            <div className="flex items-center justify-between gap-3 mb-2">
              <div className="flex items-center gap-2 text-sm text-slate-200 min-w-0">
                <Loader2 size={15} className="animate-spin text-indigo-300 shrink-0" />
                <span className="font-medium shrink-0">
                  {job.scope === 'all' ? 'Grading all decks' : `Grading ${job.slug}`}
                </span>
                <span className="text-xs text-slate-400 truncate">· {job.current || 'starting…'}</span>
              </div>
              <button
                onClick={cancelRun}
                disabled={job.status === 'cancelling'}
                className="shrink-0 text-xs px-2 py-1 rounded border border-slate-600 text-slate-300 hover:bg-slate-800 disabled:opacity-50"
              >
                {job.status === 'cancelling' ? 'Cancelling…' : 'Cancel'}
              </button>
            </div>
            <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-indigo-500 transition-all"
                style={{ width: `${job.total > 0 ? Math.round((job.done / job.total) * 100) : 0}%` }}
              />
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {job.done}/{job.total} pairs · {job.cells} cells graded{job.errors ? ` · ${job.errors} errors` : ''}
            </div>
          </div>
        )}

        {decks.length === 0 ? (
          <div className="border border-dashed border-slate-700 rounded-lg p-10 text-center text-slate-400">
            <p className="font-medium text-slate-300 mb-1">No decks found</p>
            <p className="text-sm">
              Add a folder under <code className="text-indigo-300">data/decks/&lt;slug&gt;/</code> containing
              <code className="text-indigo-300"> input.pdf</code>, <code className="text-indigo-300">ideal_output.pdf</code>, and <code className="text-indigo-300">current_output.pdf</code>, then Rescan.
            </p>
            <p className="text-sm mt-2">
              Or click <span className="text-indigo-300">Import PPTX</span> to upload a PowerPoint and auto-generate the
              <code className="text-indigo-300"> current</code> pair.
            </p>
          </div>
        ) : (
          <>
            {aligned.length === 0 ? (
              <p className="text-sm text-slate-500">No aligned decks for this view.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {aligned.map(({ d, stats }) => (
                  <DeckCard
                  key={d.slug}
                  d={d}
                  stats={stats}
                  onOpen={onOpen}
                  onAlign={onAlign}
                  aiReady={aiReady}
                  jobActive={jobActive}
                  activeSlug={job?.current_slug}
                  onRunDeck={(slug) => startRun('deck', slug)}
                />
                ))}
              </div>
            )}

            {misaligned.length > 0 && (
              <div className="mt-8">
                <button
                  onClick={() => setShowMisaligned((s) => !s)}
                  className="flex items-center gap-2 w-full text-left mb-3"
                >
                  {showMisaligned ? (
                    <ChevronDown size={16} className="text-amber-400" />
                  ) : (
                    <ChevronRight size={16} className="text-amber-400" />
                  )}
                  <span className="flex items-center gap-1.5 text-sm font-semibold text-amber-300">
                    <AlertTriangle size={15} /> Misaligned decks ({misaligned.length})
                  </span>
                  <span className="text-xs text-slate-500 hidden sm:inline">
                    input ≠ output page count — drop extra output slides to align
                  </span>
                </button>
                {showMisaligned && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 border-l-2 border-amber-500/30 pl-4">
                    {misaligned.map(({ d, stats }) => (
                      <DeckCard
                  key={d.slug}
                  d={d}
                  stats={stats}
                  onOpen={onOpen}
                  onAlign={onAlign}
                  aiReady={aiReady}
                  jobActive={jobActive}
                  activeSlug={job?.current_slug}
                  onRunDeck={(slug) => startRun('deck', slug)}
                />
                    ))}
                  </div>
                )}
              </div>
            )}

          </>
        )}
      </div>
    </div>
  )
}
