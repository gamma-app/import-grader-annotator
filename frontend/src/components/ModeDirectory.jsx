import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, BookOpen, Loader2, Search, Copy, Check, AlertTriangle, Sparkles, RefreshCw, GitBranch, UploadCloud, Wand2, PlayCircle, ClipboardCheck, Plus, Pencil, Trash2, Power, X } from 'lucide-react'
import { api } from '../api'
import RecalibratePanel from './RecalibratePanel.jsx'

const SEV = {
  P0: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
  P1: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  P2: 'bg-slate-600/30 text-slate-300 border-slate-600/40',
}

// Editable-mode form scaffolding (create + edit modals).
const EMPTY_FORM = { name: '', element: '', dimension: '', severity: 'P2', level: 'pair' }
const SEVERITIES = ['P0', 'P1', 'P2']
const LEVELS = [
  ['pair', 'Per-pair'],
  ['deck', 'Deck-level'],
]

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

// Textarea that grows to fit its content so the whole description is visible
// without an inner scrollbar or manual resizing.
function AutoGrowTextarea({ value, ...props }) {
  const ref = useRef(null)
  const fit = useCallback(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight + el.offsetHeight - el.clientHeight}px`
  }, [])
  useLayoutEffect(fit, [value, fit])
  useEffect(() => {
    window.addEventListener('resize', fit)
    return () => window.removeEventListener('resize', fit)
  }, [fit])
  return <textarea ref={ref} value={value} {...props} />
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

// Shared field inputs for the New-mode and Edit-mode modals.
function ModeFormFields({ form, setForm, elementOptions }) {
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const cls =
    'w-full bg-slate-800/60 border border-slate-700 rounded-md px-2.5 py-1.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500'
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-slate-400">Name</label>
        <input className={cls} value={form.name} onChange={set('name')} placeholder="e.g. Footnotes dropped" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-slate-400">Element group</label>
          <input className={cls} list="md-elements" value={form.element} onChange={set('element')} placeholder="e.g. Images" />
          <datalist id="md-elements">
            {(elementOptions || []).map((e) => (
              <option key={e} value={e} />
            ))}
          </datalist>
        </div>
        <div>
          <label className="text-xs text-slate-400">Dimension</label>
          <input className={cls} value={form.dimension} onChange={set('dimension')} placeholder="e.g. Presence" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-slate-400">Severity</label>
          <select className={cls} value={form.severity} onChange={set('severity')}>
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-slate-400">Level</label>
          <select className={cls} value={form.level} onChange={set('level')}>
            {LEVELS.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </div>
      </div>
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
  const [recalState, setRecalState] = useState(null) // { active_job, latest_run } for the selected mode
  const [recalJob, setRecalJob] = useState(null) // the single active recalibration job (any mode)
  const [recalConfirm, setRecalConfirm] = useState({ open: false, mode: null, preview: null, loading: false })
  const [recalRun, setRecalRun] = useState(null) // full run record for the review panel
  const [recalBusy, setRecalBusy] = useState(false) // starting / adopting / rejecting
  const recalPoll = useRef(null)
  const [aiJob, setAiJob] = useState(null) // active/last bulk AI grading job (global, single-slot)
  const aiPoll = useRef(null)
  const selectedIdRef = useRef(selectedId)
  // Registry editing (create / edit fields / enable-disable / delete).
  const [newOpen, setNewOpen] = useState(false)
  const [newForm, setNewForm] = useState(EMPTY_FORM)
  const [createBusy, setCreateBusy] = useState(false)
  const [edit, setEdit] = useState({ open: false, mode: null })
  const [editForm, setEditForm] = useState(EMPTY_FORM)
  const [editBusy, setEditBusy] = useState(false)
  const [toggleBusy, setToggleBusy] = useState(false)
  const [del, setDel] = useState({ open: false, mode: null })
  const [delBusy, setDelBusy] = useState(false)

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
                ? { ...m, grader_name: r.grader_name, prompt: r.prompt, model: r.model, uncommitted: true, prompt_status: 'ok' }
                : m,
            )
          : d,
      )
      showToast?.({
        type: 'success',
        msg: r.created
          ? `Created grader "${r.grader_name}" for #${mode.id} — review & push`
          : `Regenerated #${mode.id} grader · cleared ${r.cleared} AI score${r.cleared === 1 ? '' : 's'}`,
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

  // ----- recalibration (optimize a grader prompt from human labels)
  const stopRecalPoll = useCallback(() => {
    if (recalPoll.current) {
      clearInterval(recalPoll.current)
      recalPoll.current = null
    }
  }, [])

  const startRecalPoll = useCallback(
    (jobId) => {
      stopRecalPoll()
      recalPoll.current = setInterval(async () => {
        let j
        try {
          j = await api.getRecalibrationJob(jobId)
        } catch {
          stopRecalPoll()
          return
        }
        setRecalJob(j)
        if (j.status === 'running' || j.status === 'cancelling') return
        stopRecalPoll()
        if (j.status === 'done' && j.run_id) {
          try {
            setRecalRun(await api.getRecalibrationRun(j.run_id))
          } catch (e) {
            showToast?.({ type: 'error', msg: String(e) })
          }
          showToast?.({ type: 'success', msg: `Recalibration ready — review the proposal for #${j.mode_id}` })
        } else if (j.status === 'error') {
          showToast?.({ type: 'error', msg: `Recalibration failed: ${j.error || 'unknown error'}` })
        } else if (j.status === 'cancelled') {
          showToast?.({ type: 'success', msg: 'Recalibration cancelled' })
        }
        try {
          setRecalState(await api.getRecalibrationState(selectedIdRef.current))
        } catch {
          /* non-fatal */
        }
      }, 2000)
    },
    [stopRecalPoll, showToast],
  )

  // Keep a ref to the selected id so async poll callbacks read the latest value.
  useEffect(() => {
    selectedIdRef.current = selectedId
  }, [selectedId])

  // Load recalibration state (active job + latest run) when the mode changes.
  useEffect(() => {
    if (selectedId == null) return undefined
    let cancelled = false
    api
      .getRecalibrationState(selectedId)
      .then((r) => {
        if (cancelled) return
        setRecalState(r)
        const job = r.active_job
        if (job && (job.status === 'running' || job.status === 'cancelling')) {
          setRecalJob(job)
          startRecalPoll(job.id)
        }
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [selectedId, startRecalPoll])

  // Stop polling on unmount.
  useEffect(() => () => stopRecalPoll(), [stopRecalPoll])

  // ----- bulk AI grading (run one grader across all decks)
  const stopAiPoll = useCallback(() => {
    if (aiPoll.current) {
      clearInterval(aiPoll.current)
      aiPoll.current = null
    }
  }, [])

  const startAiPoll = useCallback(
    (jobId) => {
      stopAiPoll()
      aiPoll.current = setInterval(async () => {
        let j
        try {
          j = await api.getAiJob(jobId)
        } catch {
          stopAiPoll()
          return
        }
        setAiJob(j)
        if (j.status === 'running' || j.status === 'cancelling') return
        stopAiPoll()
        showToast?.({
          type: j.status === 'error' ? 'error' : 'success',
          msg: `AI run ${j.status} \u2014 ${j.cells} graded${j.errors ? `, ${j.errors} errors` : ''}`,
        })
      }, 1500)
    },
    [stopAiPoll, showToast],
  )

  // Resume an in-flight bulk run (e.g. started from the dashboard) on mount.
  useEffect(() => {
    api
      .getAiJobs()
      .then((r) => {
        const j = r.active
        if (j && (j.status === 'running' || j.status === 'cancelling')) {
          setAiJob(j)
          startAiPoll(j.id)
        }
      })
      .catch(() => {})
    return () => stopAiPoll()
  }, [startAiPoll, stopAiPoll])

  const openRecalConfirm = async (mode) => {
    await flushNow()
    setRecalConfirm({ open: true, mode, preview: null, loading: true })
    try {
      const preview = await api.getRecalibrationPreview(mode.id)
      setRecalConfirm({ open: true, mode, preview, loading: false })
    } catch (e) {
      setRecalConfirm({ open: false, mode: null, preview: null, loading: false })
      showToast?.({ type: 'error', msg: String(e) })
    }
  }

  const startRecal = async (mode) => {
    setRecalBusy(true)
    try {
      const j = await api.startRecalibration(mode.id)
      setRecalJob(j)
      setRecalConfirm({ open: false, mode: null, preview: null, loading: false })
      if (j.status === 'running' || j.status === 'cancelling') startRecalPoll(j.id)
    } catch (e) {
      showToast?.({ type: 'error', msg: String(e) })
    } finally {
      setRecalBusy(false)
    }
  }

  const cancelRecal = async () => {
    if (!recalJob) return
    try {
      setRecalJob(await api.cancelRecalibrationJob(recalJob.id))
    } catch (e) {
      showToast?.({ type: 'error', msg: String(e) })
    }
  }

  const openReview = async (runId) => {
    try {
      setRecalRun(await api.getRecalibrationRun(runId))
    } catch (e) {
      showToast?.({ type: 'error', msg: String(e) })
    }
  }

  const doAdopt = async () => {
    if (!recalRun) return
    setRecalBusy(true)
    try {
      const r = await api.adoptRecalibration(recalRun.id)
      setData((d) =>
        d
          ? d.map((m) =>
              m.id === r.mode_id
                ? { ...m, prompt: r.prompt, model: r.model || m.model, uncommitted: true, prompt_status: 'ok' }
                : m,
            )
          : d,
      )
      setRecalRun((run) => (run ? { ...run, status: 'approved' } : run))
      const cleared = r.cleared || 0
      showToast?.({
        type: 'success',
        msg: `Adopted new prompt for #${r.mode_id} · ${r.persisted} verdict${r.persisted === 1 ? '' : 's'} kept, ${cleared} stale score${cleared === 1 ? '' : 's'} cleared`,
      })
      try {
        setGit(await api.getGitStatus())
      } catch {
        /* non-fatal */
      }
      try {
        setRecalState(await api.getRecalibrationState(r.mode_id))
      } catch {
        /* non-fatal */
      }
    } catch (e) {
      showToast?.({ type: 'error', msg: String(e) })
    } finally {
      setRecalBusy(false)
    }
  }

  const doReject = async () => {
    if (!recalRun) return
    setRecalBusy(true)
    try {
      await api.rejectRecalibration(recalRun.id)
      showToast?.({ type: 'success', msg: 'Proposal rejected' })
      setRecalRun(null)
      try {
        setRecalState(await api.getRecalibrationState(selectedIdRef.current))
      } catch {
        /* non-fatal */
      }
    } catch (e) {
      showToast?.({ type: 'error', msg: String(e) })
    } finally {
      setRecalBusy(false)
    }
  }

  const gradeAllDecks = async (mode) => {
    if (!mode?.grader_name) return
    const ok = window.confirm(
      `Run the "${mode.name}" grader (#${mode.id}) on all decks across both splits ` +
        `(Deck Doctor + Current Import).\n\n` +
        `Grades every available, aligned deck for this one failure mode ` +
        `(already-graded slides are skipped). Runs in the background — you can keep working. Continue?`,
    )
    if (!ok) return
    try {
      const j = await api.runAiBulk({ scope: 'all', variant: 'both', modes: [mode.id] })
      setAiJob(j)
      if (j.status === 'running' || j.status === 'cancelling') startAiPoll(j.id)
    } catch (e) {
      showToast?.({ type: 'error', msg: String(e) })
    }
  }

  const cancelAiRun = async () => {
    if (!aiJob) return
    try {
      setAiJob(await api.cancelAiJob(aiJob.id))
    } catch (e) {
      showToast?.({ type: 'error', msg: String(e) })
    }
  }

  // ----- registry CRUD
  const doCreate = async () => {
    if (!newForm.name.trim() || !newForm.element.trim()) {
      showToast?.({ type: 'error', msg: 'Name and element are required' })
      return
    }
    setCreateBusy(true)
    try {
      const created = await api.createMode(newForm)
      // Re-fetch so the new row carries the directory-enriched fields (prompt_status, etc.).
      const r = await api.getModeDirectory()
      setData(r.modes)
      setElementOrder(r.element_order || [])
      setSelectedId(created.id)
      setNewOpen(false)
      setNewForm(EMPTY_FORM)
      showToast?.({ type: 'success', msg: `Added #${created.id} ${created.name}` })
    } catch (e) {
      showToast?.({ type: 'error', msg: String(e) })
    } finally {
      setCreateBusy(false)
    }
  }

  const openEdit = (mode) => {
    setEditForm({
      name: mode.name,
      element: mode.element,
      dimension: mode.dimension || '',
      severity: mode.severity || 'P2',
      level: mode.level || 'pair',
    })
    setEdit({ open: true, mode })
  }

  const saveEdit = async () => {
    const mode = edit.mode
    if (!mode) return
    if (!editForm.name.trim() || !editForm.element.trim()) {
      showToast?.({ type: 'error', msg: 'Name and element are required' })
      return
    }
    setEditBusy(true)
    try {
      const updated = await api.updateMode(mode.id, editForm)
      setData((d) => (d ? d.map((m) => (m.id === mode.id ? { ...m, ...updated } : m)) : d))
      if (updated.element && !elementOrder.includes(updated.element)) {
        setElementOrder((eo) => [...eo, updated.element])
      }
      setEdit({ open: false, mode: null })
      showToast?.({ type: 'success', msg: `Updated #${mode.id}` })
    } catch (e) {
      showToast?.({ type: 'error', msg: String(e) })
    } finally {
      setEditBusy(false)
    }
  }

  const toggleEnabled = async (mode) => {
    if (!mode) return
    setToggleBusy(true)
    try {
      const updated = await api.updateMode(mode.id, { enabled: !mode.enabled })
      setData((d) => (d ? d.map((m) => (m.id === mode.id ? { ...m, ...updated } : m)) : d))
      showToast?.({ type: 'success', msg: `${updated.enabled ? 'Enabled' : 'Disabled'} #${mode.id}` })
    } catch (e) {
      showToast?.({ type: 'error', msg: String(e) })
    } finally {
      setToggleBusy(false)
    }
  }

  const doDelete = async () => {
    const mode = del.mode
    if (!mode) return
    setDelBusy(true)
    try {
      await api.deleteMode(mode.id)
      const rest = (data || []).filter((m) => m.id !== mode.id)
      setData(rest)
      setSelectedId((cur) => (cur === mode.id ? (rest[0] ? rest[0].id : null) : cur))
      setDel({ open: false, mode: null })
      showToast?.({ type: 'success', msg: `Deleted #${mode.id} ${mode.name}` })
    } catch (e) {
      showToast?.({ type: 'error', msg: String(e) })
    } finally {
      setDelBusy(false)
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
  const recalActive = !!(recalJob && (recalJob.status === 'running' || recalJob.status === 'cancelling'))
  const aiJobActive = !!(aiJob && (aiJob.status === 'running' || aiJob.status === 'cancelling'))
  const recalForSelected = recalActive && recalJob.mode_id === selectedId
  const proposal = recalState?.latest_run?.status === 'proposed' ? recalState.latest_run : null

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
        <button
          onClick={() => {
            setNewForm(EMPTY_FORM)
            setNewOpen(true)
          }}
          className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded border border-indigo-600/60 text-indigo-200 hover:bg-indigo-600/15"
        >
          <Plus size={14} /> New mode
        </button>
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
                      } ${m.enabled ? '' : 'opacity-50'}`}
                    >
                      <span className="text-[11px] text-slate-500 w-5 shrink-0 text-right">{m.id}</span>
                      <span className="text-sm text-slate-200 truncate flex-1">{m.name}</span>
                      {hasDesc && (
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" title="Has a description" />
                      )}
                      {!m.enabled && <span className="text-[10px] text-rose-400 shrink-0">off</span>}
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
              <div className="flex flex-wrap items-center gap-1.5 mt-2 mb-3">
                <Badge className="bg-slate-700/40 text-slate-300 border-slate-600/40">{selected.element}</Badge>
                {selected.dimension && (
                  <Badge className="bg-slate-700/40 text-slate-300 border-slate-600/40">{selected.dimension}</Badge>
                )}
                <Badge className={SEV[selected.severity] || SEV.P2}>{selected.severity}</Badge>
                <Badge className="bg-slate-700/40 text-slate-400 border-slate-600/40">
                  {selected.level === 'deck' ? 'deck-level' : 'per-pair'}
                </Badge>
                {!selected.builtin && (
                  <Badge className="bg-indigo-500/15 text-indigo-300 border-indigo-500/30">custom</Badge>
                )}
                {!selected.enabled && (
                  <Badge className="bg-rose-500/15 text-rose-300 border-rose-500/30">disabled</Badge>
                )}
                {selected.aka && <span className="text-xs text-slate-500">· {selected.aka}</span>}
              </div>

              <div className="flex flex-wrap items-center gap-2 mb-6">
                <button
                  onClick={() => openEdit(selected)}
                  className="flex items-center gap-1.5 text-xs px-2 py-1 rounded border border-slate-700 text-slate-300 hover:bg-slate-800"
                >
                  <Pencil size={13} /> Edit fields
                </button>
                <button
                  onClick={() => toggleEnabled(selected)}
                  disabled={toggleBusy}
                  className="flex items-center gap-1.5 text-xs px-2 py-1 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
                >
                  {toggleBusy ? <Loader2 size={13} className="animate-spin" /> : <Power size={13} />}
                  {selected.enabled ? 'Disable' : 'Enable'}
                </button>
                <button
                  onClick={() => setDel({ open: true, mode: selected })}
                  className="flex items-center gap-1.5 text-xs px-2 py-1 rounded border border-rose-700/60 text-rose-300 hover:bg-rose-600/15"
                >
                  <Trash2 size={13} /> Delete
                </button>
              </div>

              <div className="mb-6">
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-sm font-medium text-slate-300">Description</label>
                  <SaveStatus status={status} />
                </div>
                <AutoGrowTextarea
                  key={selected.id}
                  value={textFor(selected)}
                  onChange={(e) => onChange(selected.id, e.target.value)}
                  onBlur={flush}
                  placeholder="Describe this failure mode… (saved automatically)"
                  className="w-full bg-slate-800/60 border border-slate-700 rounded-lg p-3 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 resize-none overflow-hidden leading-relaxed min-h-[6rem]"
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
                          disabled={commitBusy || reinitBusy || recalForSelected}
                          title="Commit this prompt and push it to GitHub"
                          className="flex items-center gap-1.5 text-xs px-2 py-1 rounded border border-emerald-600/60 text-emerald-200 hover:bg-emerald-600/15 disabled:opacity-40"
                        >
                          {commitBusy ? <Loader2 size={13} className="animate-spin" /> : <UploadCloud size={13} />}
                          {commitBusy ? 'Pushing…' : 'Commit & push'}
                        </button>
                      )}
                      <button
                        onClick={() => gradeAllDecks(selected)}
                        disabled={aiJobActive || recalForSelected || reinitBusy || commitBusy}
                        title={
                          aiJobActive
                            ? 'A bulk AI run is already in progress'
                            : 'Run this grader on every deck across both splits (Deck Doctor + Current Import)'
                        }
                        className="flex items-center gap-1.5 text-xs px-2 py-1 rounded border border-sky-600/60 text-sky-200 hover:bg-sky-600/15 disabled:opacity-40"
                      >
                        {aiJobActive ? <Loader2 size={13} className="animate-spin" /> : <PlayCircle size={13} />}
                        Grade all decks
                      </button>
                      <button
                        onClick={() => openRecalConfirm(selected)}
                        disabled={recalActive || reinitBusy || commitBusy || recalBusy}
                        title={
                          recalActive
                            ? 'A recalibration is already running'
                            : 'Optimize this grader prompt from human-labeled slides'
                        }
                        className="flex items-center gap-1.5 text-xs px-2 py-1 rounded border border-fuchsia-600/60 text-fuchsia-200 hover:bg-fuchsia-600/15 disabled:opacity-40"
                      >
                        {recalForSelected ? <Loader2 size={13} className="animate-spin" /> : <Wand2 size={13} />}
                        {recalForSelected ? 'Recalibrating…' : 'Recalibrate'}
                      </button>
                      {proposal && !recalForSelected && (
                        <button
                          onClick={() => openReview(proposal.id)}
                          className="flex items-center gap-1.5 text-xs px-2 py-1 rounded border border-amber-500/60 text-amber-200 hover:bg-amber-500/15"
                          title="Review the pending recalibration proposal"
                        >
                          <ClipboardCheck size={13} /> Review proposal
                        </button>
                      )}
                      <button
                        onClick={() => openReinit(selected)}
                        disabled={!(textFor(selected) || '').trim() || reinitBusy || commitBusy || recalForSelected}
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
                  {!selected.grader_name && selected.level === 'pair' && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => openReinit(selected)}
                        disabled={!(textFor(selected) || '').trim() || reinitBusy}
                        title={
                          (textFor(selected) || '').trim()
                            ? 'Author a VLM grader for this mode from its description'
                            : 'Write a description first'
                        }
                        className="flex items-center gap-1.5 text-xs px-2 py-1 rounded border border-indigo-600/60 text-indigo-200 hover:bg-indigo-600/15 disabled:opacity-40"
                      >
                        {reinitBusy ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                        Generate AI grader
                      </button>
                    </div>
                  )}
                </div>
                {recalForSelected && (
                  <div className="mb-2 rounded-lg border border-fuchsia-700/50 bg-fuchsia-950/20 p-2.5">
                    <div className="flex items-center justify-between gap-3 mb-1.5">
                      <div className="flex items-center gap-2 text-xs text-slate-200 min-w-0">
                        <Loader2 size={13} className="animate-spin text-fuchsia-300 shrink-0" />
                        <span className="font-medium shrink-0">Recalibrating</span>
                        <span className="text-slate-400 truncate">· {recalJob.stage || 'working…'}</span>
                      </div>
                      <button
                        onClick={cancelRecal}
                        disabled={recalJob.status === 'cancelling'}
                        className="shrink-0 text-[11px] px-2 py-0.5 rounded border border-slate-600 text-slate-300 hover:bg-slate-800 disabled:opacity-50"
                      >
                        {recalJob.status === 'cancelling' ? 'Cancelling…' : 'Cancel'}
                      </button>
                    </div>
                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-fuchsia-500 transition-all"
                        style={{ width: `${recalJob.total > 0 ? Math.round((recalJob.done / recalJob.total) * 100) : 0}%` }}
                      />
                    </div>
                    <div className="text-[11px] text-slate-400 mt-1">
                      {recalJob.done}/{recalJob.total} model calls · {recalJob.message || recalJob.stage}
                    </div>
                  </div>
                )}
                {aiJobActive && (
                  <div className="mb-2 rounded-lg border border-sky-700/50 bg-sky-950/20 p-2.5">
                    <div className="flex items-center justify-between gap-3 mb-1.5">
                      <div className="flex items-center gap-2 text-xs text-slate-200 min-w-0">
                        <Loader2 size={13} className="animate-spin text-sky-300 shrink-0" />
                        <span className="font-medium shrink-0">Grading all decks</span>
                        <span className="text-slate-400 truncate">· {aiJob.current || 'starting…'}</span>
                      </div>
                      <button
                        onClick={cancelAiRun}
                        disabled={aiJob.status === 'cancelling'}
                        className="shrink-0 text-[11px] px-2 py-0.5 rounded border border-slate-600 text-slate-300 hover:bg-slate-800 disabled:opacity-50"
                      >
                        {aiJob.status === 'cancelling' ? 'Cancelling…' : 'Cancel'}
                      </button>
                    </div>
                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-sky-500 transition-all"
                        style={{ width: `${aiJob.total > 0 ? Math.round((aiJob.done / aiJob.total) * 100) : 0}%` }}
                      />
                    </div>
                    <div className="text-[11px] text-slate-400 mt-1">
                      {aiJob.done}/{aiJob.total} pairs · {aiJob.cells} graded{aiJob.errors ? ` · ${aiJob.errors} errors` : ''}
                    </div>
                  </div>
                )}
                {!recalForSelected && proposal && (
                  <button
                    onClick={() => openReview(proposal.id)}
                    className="mb-2 w-full flex items-center justify-center gap-1.5 text-xs px-2 py-1.5 rounded border border-amber-500/50 bg-amber-500/10 text-amber-200 hover:bg-amber-500/15"
                  >
                    <ClipboardCheck size={13} /> A recalibration proposal is ready — review &amp; approve
                  </button>
                )}
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
              {reinit.mode?.grader_name ? (
                <>
                  <AlertTriangle size={16} className="text-amber-400" /> Reinitialize grader prompt
                </>
              ) : (
                <>
                  <Sparkles size={16} className="text-indigo-400" /> Generate VLM grader
                </>
              )}
            </div>
            {reinit.mode?.grader_name ? (
              <>
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
              </>
            ) : (
              <>
                <p className="text-sm text-slate-300 mb-3">
                  This authors a new VLM grader for{' '}
                  <span className="font-medium text-slate-100">
                    #{reinit.mode?.id} {reinit.mode?.name}
                  </span>{' '}
                  from its description and attaches it to the mode. The prompt is left{' '}
                  <span className="text-amber-300 font-medium">uncommitted</span> for you to review and push.
                </p>
                <p className="text-xs text-slate-500 mb-4">
                  You can grade with it right away; commit &amp; push to share it with the team.
                </p>
              </>
            )}
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
                ) : reinit.mode?.grader_name ? (
                  'Reinitialize'
                ) : (
                  'Generate grader'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {recalConfirm.open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => !recalBusy && setRecalConfirm({ open: false, mode: null, preview: null, loading: false })}
        >
          <div
            className="bg-slate-900 border border-slate-700 rounded-xl max-w-md w-full p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 mb-3 text-slate-100 font-semibold">
              <Wand2 size={16} className="text-fuchsia-400" /> Recalibrate grader prompt
            </div>
            {recalConfirm.loading ? (
              <div className="flex items-center gap-2 text-sm text-slate-400 py-6 justify-center">
                <Loader2 size={15} className="animate-spin" /> Checking labeled data…
              </div>
            ) : recalConfirm.preview && !recalConfirm.preview.eligible ? (
              <>
                <p className="text-sm text-slate-300 mb-2">
                  Not enough labeled data to recalibrate{' '}
                  <span className="font-medium text-slate-100">
                    #{recalConfirm.mode?.id} {recalConfirm.mode?.name}
                  </span>
                  .
                </p>
                <p className="text-xs text-slate-500 mb-4">{recalConfirm.preview.reason}</p>
                <div className="flex justify-end">
                  <button
                    onClick={() => setRecalConfirm({ open: false, mode: null, preview: null, loading: false })}
                    className="text-sm px-3 py-1.5 rounded border border-slate-700 text-slate-300 hover:bg-slate-800"
                  >
                    Close
                  </button>
                </div>
              </>
            ) : recalConfirm.preview ? (
              <>
                <p className="text-sm text-slate-300 mb-3">
                  Optimize the{' '}
                  <span className="font-medium text-slate-100">
                    #{recalConfirm.mode?.id} {recalConfirm.mode?.name}
                  </span>{' '}
                  grader from human-labeled slides. This runs in the background and proposes a new
                  prompt for your review — it does <span className="text-slate-100 font-medium">not</span>{' '}
                  change anything until you approve.
                </p>
                <div className="text-xs text-slate-400 bg-slate-950/40 border border-slate-800 rounded-lg p-3 mb-4 space-y-1">
                  <div className="flex justify-between">
                    <span>Labeled pairs</span>
                    <span className="text-slate-200">{recalConfirm.preview.dataset_size}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Split (train/val/test)</span>
                    <span className="text-slate-200">
                      {recalConfirm.preview.split?.train}/{recalConfirm.preview.split?.val}/{recalConfirm.preview.split?.test}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Candidates</span>
                    <span className="text-slate-200">{recalConfirm.preview.candidates}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>~ model calls</span>
                    <span className="text-slate-200">{recalConfirm.preview.estimated_calls}</span>
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => setRecalConfirm({ open: false, mode: null, preview: null, loading: false })}
                    disabled={recalBusy}
                    className="text-sm px-3 py-1.5 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => startRecal(recalConfirm.mode)}
                    disabled={recalBusy}
                    className="text-sm px-3 py-1.5 rounded border border-fuchsia-600 bg-fuchsia-600/20 text-fuchsia-100 hover:bg-fuchsia-600/30 disabled:opacity-40 flex items-center gap-1.5"
                  >
                    {recalBusy ? (
                      <>
                        <Loader2 size={14} className="animate-spin" /> Starting…
                      </>
                    ) : (
                      <>
                        <Wand2 size={14} /> Run recalibration
                      </>
                    )}
                  </button>
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}

      {recalRun && (
        <RecalibratePanel
          run={recalRun}
          busy={recalBusy}
          onClose={() => setRecalRun(null)}
          onAdopt={doAdopt}
          onReject={doReject}
        />
      )}

      {newOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => !createBusy && setNewOpen(false)}
        >
          <div
            className="bg-slate-900 border border-slate-700 rounded-xl max-w-md w-full p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 mb-3 text-slate-100 font-semibold">
              <Plus size={16} className="text-indigo-400" /> New failure mode
            </div>
            <ModeFormFields form={newForm} setForm={setNewForm} elementOptions={elementOrder} />
            <p className="text-xs text-slate-500 mt-3">
              A new mode starts with no VLM grader. Add a description, then generate one.
            </p>
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setNewOpen(false)}
                disabled={createBusy}
                className="text-sm px-3 py-1.5 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
              >
                Cancel
              </button>
              <button
                onClick={doCreate}
                disabled={createBusy || !newForm.name.trim() || !newForm.element.trim()}
                className="text-sm px-3 py-1.5 rounded border border-indigo-600 bg-indigo-600/20 text-indigo-100 hover:bg-indigo-600/30 disabled:opacity-40 flex items-center gap-1.5"
              >
                {createBusy ? (
                  <>
                    <Loader2 size={14} className="animate-spin" /> Adding…
                  </>
                ) : (
                  'Add mode'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {edit.open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => !editBusy && setEdit({ open: false, mode: null })}
        >
          <div
            className="bg-slate-900 border border-slate-700 rounded-xl max-w-md w-full p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 mb-3 text-slate-100 font-semibold">
              <Pencil size={16} className="text-indigo-400" /> Edit #{edit.mode?.id}
            </div>
            <ModeFormFields form={editForm} setForm={setEditForm} elementOptions={elementOrder} />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setEdit({ open: false, mode: null })}
                disabled={editBusy}
                className="text-sm px-3 py-1.5 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
              >
                Cancel
              </button>
              <button
                onClick={saveEdit}
                disabled={editBusy || !editForm.name.trim() || !editForm.element.trim()}
                className="text-sm px-3 py-1.5 rounded border border-indigo-600 bg-indigo-600/20 text-indigo-100 hover:bg-indigo-600/30 disabled:opacity-40 flex items-center gap-1.5"
              >
                {editBusy ? (
                  <>
                    <Loader2 size={14} className="animate-spin" /> Saving…
                  </>
                ) : (
                  'Save changes'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {del.open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => !delBusy && setDel({ open: false, mode: null })}
        >
          <div
            className="bg-slate-900 border border-slate-700 rounded-xl max-w-md w-full p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 mb-2 text-slate-100 font-semibold">
              <Trash2 size={16} className="text-rose-400" /> Delete failure mode
            </div>
            <p className="text-sm text-slate-300 mb-3">
              Permanently delete{' '}
              <span className="font-medium text-slate-100">
                #{del.mode?.id} {del.mode?.name}
              </span>
              ? This can&rsquo;t be undone.
            </p>
            <p className="text-xs text-slate-500 mb-4">
              Modes that already have human grades or AI verdicts can&rsquo;t be deleted — disable them instead. Any grader
              files on disk are left untouched.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDel({ open: false, mode: null })}
                disabled={delBusy}
                className="text-sm px-3 py-1.5 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
              >
                Cancel
              </button>
              <button
                onClick={doDelete}
                disabled={delBusy}
                className="text-sm px-3 py-1.5 rounded border border-rose-600 bg-rose-600/20 text-rose-100 hover:bg-rose-600/30 disabled:opacity-40 flex items-center gap-1.5"
              >
                {delBusy ? (
                  <>
                    <Loader2 size={14} className="animate-spin" /> Deleting…
                  </>
                ) : (
                  'Delete'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
