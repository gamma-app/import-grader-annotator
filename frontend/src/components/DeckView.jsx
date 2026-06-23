import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, ChevronLeft, ChevronRight, Loader2, Check, AlertTriangle, Palette, X, Sparkles } from 'lucide-react'
import { api } from '../api'
import ImageViewer from './ImageViewer.jsx'
import ModePanel, { ModeRow } from './ModePanel.jsx'
import ModeFilter from './ModeFilter.jsx'
import AiStatusDot from './AiStatusDot.jsx'

export default function DeckView({ slug, variant, modes, modeFilter, onModeFilterChange, onBack, showToast }) {
  const [deck, setDeck] = useState(null)
  const [index, setIndex] = useState(0)
  const [saving, setSaving] = useState(false)
  const [showDeckPanel, setShowDeckPanel] = useState(false)
  // AI grader (import-evals) — view-only overlay, fetched per slug:variant.
  const [aiStatus, setAiStatus] = useState(null)
  const [aiGrades, setAiGrades] = useState({ pairs: {} })
  const [aiRun, setAiRun] = useState(null) // { active: true } while grading the pair
  const [regrading, setRegrading] = useState(() => new Set()) // mode ids re-grading now

  const deckRef = useRef(deck)
  const timers = useRef({})
  useEffect(() => {
    deckRef.current = deck
  }, [deck])

  const pairModes = useMemo(() => modes.modes.filter((m) => m.level === 'pair'), [modes])
  const deckModes = useMemo(() => modes.modes.filter((m) => m.level === 'deck'), [modes])
  // View-only: which pair modes the rail renders. Filtering never changes saved
  // grades, the reviewed/complete status, dashboard progress, or exports.
  const visiblePairModes = useMemo(
    () => (modeFilter ? pairModes.filter((m) => modeFilter.has(m.id)) : pairModes),
    [pairModes, modeFilter],
  )
  const gradeableIds = useMemo(
    () => new Set(Object.keys(modes.mode_graders || {}).map(Number)),
    [modes],
  )
  const aiReady = !!(aiStatus && aiStatus.eval_server_reachable && aiStatus.graders_dir_ok)

  // ----- load deck
  useEffect(() => {
    let alive = true
    setDeck(null)
    api
      .getDeck(slug, variant)
      .then((d) => {
        if (!alive) return
        setDeck(d)
        const saved = parseInt(localStorage.getItem(`pos:${slug}:${variant}`) || '', 10)
        const firstUnreviewed = d.pairs.findIndex((p) => !p.reviewed)
        const start = Number.isInteger(saved) && saved >= 0 && saved < d.pairs.length
          ? saved
          : firstUnreviewed >= 0
            ? firstUnreviewed
            : 0
        setIndex(start)
      })
      .catch((e) => showToast({ type: 'error', msg: String(e) }))
    return () => {
      alive = false
    }
  }, [slug]) // eslint-disable-line react-hooks/exhaustive-deps

  // ----- load AI grader status + stored verdicts (DeckView remounts per slug:variant)
  useEffect(() => {
    let alive = true
    api.getAiStatus().then((s) => alive && setAiStatus(s)).catch(() => {})
    api
      .getAiGrades(slug, variant)
      .then((g) => alive && setAiGrades(g && g.pairs ? g : { pairs: {} }))
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [slug, variant])

  // ----- debounced autosave plumbing
  const schedule = useCallback((key, fn, delay = 600) => {
    if (timers.current[key]) clearTimeout(timers.current[key].id)
    const id = setTimeout(() => {
      delete timers.current[key]
      fn()
    }, delay)
    timers.current[key] = { id, fn }
  }, [])

  const flushAll = useCallback(() => {
    Object.values(timers.current).forEach(({ id, fn }) => {
      clearTimeout(id)
      fn()
    })
    timers.current = {}
  }, [])

  useEffect(() => () => flushAll(), [flushAll])

  const savePair = useCallback(
    (pairIndex) => {
      const d = deckRef.current
      const pair = d?.pairs.find((p) => p.index === pairIndex)
      if (!pair) return
      setSaving(true)
      api
        .putPair(slug, variant, pairIndex, pair.modes)
        .then((updated) =>
          setDeck((prev) =>
            prev
              ? {
                  ...prev,
                  pairs: prev.pairs.map((p) =>
                    p.index === pairIndex ? { ...p, reviewed: updated.reviewed, updated_at: updated.updated_at } : p,
                  ),
                }
              : prev,
          ),
        )
        .catch((e) => showToast({ type: 'error', msg: String(e) }))
        .finally(() => setSaving(false))
    },
    [slug, variant, showToast],
  )

  const saveDeckLevel = useCallback(() => {
    const d = deckRef.current
    if (!d) return
    setSaving(true)
    api
      .putDeckLevel(slug, variant, d.deck_level)
      .catch((e) => showToast({ type: 'error', msg: String(e) }))
      .finally(() => setSaving(false))
  }, [slug, variant, showToast])

  // ----- editing handlers
  const updatePairMode = useCallback(
    (modeId, partial) => {
      setDeck((prev) => {
        if (!prev) return prev
        const pairs = prev.pairs.map((p, i) =>
          i === index
            ? { ...p, modes: { ...p.modes, [modeId]: { ...p.modes[modeId], ...partial } } }
            : p,
        )
        return { ...prev, pairs }
      })
      const pairIndex = deckRef.current?.pairs[index]?.index
      if (pairIndex != null) schedule(`pair:${pairIndex}`, () => savePair(pairIndex))
    },
    [index, schedule, savePair],
  )

  const updateDeckMode = useCallback(
    (modeId, partial) => {
      setDeck((prev) =>
        prev ? { ...prev, deck_level: { ...prev.deck_level, [modeId]: { ...prev.deck_level[modeId], ...partial } } } : prev,
      )
      schedule('deck', saveDeckLevel)
    },
    [schedule, saveDeckLevel],
  )

  // ----- AI grading (on-demand; view-only, never touches human grades)
  const mergeAiCells = useCallback((pairIndex, cells) => {
    setAiGrades((prev) => {
      const pairs = { ...(prev.pairs || {}) }
      pairs[String(pairIndex)] = { ...(pairs[String(pairIndex)] || {}), ...cells }
      return { ...prev, pairs }
    })
  }, [])

  const runPairAi = useCallback(
    async (force = false) => {
      const p = deckRef.current?.pairs[index]
      if (!p) return
      setAiRun({ active: true })
      try {
        const res = await api.runAiPair(slug, variant, p.index, { force })
        mergeAiCells(p.index, res.modes || {})
      } catch (e) {
        showToast({ type: 'error', msg: String(e) })
      } finally {
        setAiRun(null)
      }
    },
    [slug, variant, index, mergeAiCells, showToast],
  )

  const regradeMode = useCallback(
    async (modeId) => {
      const p = deckRef.current?.pairs[index]
      if (!p) return
      setRegrading((s) => new Set(s).add(modeId))
      try {
        const res = await api.runAiPair(slug, variant, p.index, { modes: [modeId], force: true })
        mergeAiCells(p.index, res.modes || {})
      } catch (e) {
        showToast({ type: 'error', msg: String(e) })
      } finally {
        setRegrading((s) => {
          const n = new Set(s)
          n.delete(modeId)
          return n
        })
      }
    },
    [slug, variant, index, mergeAiCells, showToast],
  )

  // ----- navigation
  const goto = useCallback(
    (next) => {
      if (!deckRef.current) return
      const clamped = Math.max(0, Math.min(deckRef.current.pairs.length - 1, next))
      flushAll()
      setIndex(clamped)
      localStorage.setItem(`pos:${slug}:${variant}`, String(clamped))
    },
    [slug, variant, flushAll],
  )

  useEffect(() => {
    const onKey = (e) => {
      const tag = e.target.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      if (e.key === 'ArrowRight') goto(index + 1)
      else if (e.key === 'ArrowLeft') goto(index - 1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [index, goto])

  if (!deck) {
    return (
      <div className="h-full flex items-center justify-center text-slate-400">
        <Loader2 className="animate-spin mr-2" size={20} /> Loading deck…
      </div>
    )
  }

  const pair = deck.pairs[index]
  const aiForPair = pair ? aiGrades.pairs?.[String(pair.index)] || {} : {}
  const reviewedCount = deck.pairs.filter((p) => p.reviewed).length
  const total = deck.pairs.length
  const deckGraded = deckModes.every((m) => (deck.deck_level[String(m.id)]?.grade || 'ungraded') !== 'ungraded')

  return (
    <div className="h-full flex flex-col">
      {/* sub-header */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-slate-800 bg-slate-900">
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-300 hover:text-white">
          <ArrowLeft size={16} /> Decks
        </button>
        <div className="h-4 w-px bg-slate-700" />
        <div className="min-w-0">
          <div className="text-sm font-semibold text-slate-100 truncate">{deck.title}</div>
        </div>
        <span className="shrink-0 text-xs px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-200 border border-violet-500/30">
          {deck.variant_label}
        </span>
        {deck.alignment.misaligned && (
          <span className="flex items-center gap-1 text-xs px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30">
            <AlertTriangle size={12} /> misaligned {deck.alignment.input_count}≠{deck.alignment.output_count}
          </span>
        )}

        <div className="flex-1" />

        {saving && (
          <span className="flex items-center gap-1 text-xs text-slate-400">
            <Loader2 size={12} className="animate-spin" /> saving
          </span>
        )}
        <span className="text-xs text-slate-400">{reviewedCount}/{total} reviewed</span>

        <button
          onClick={() => setShowDeckPanel(true)}
          className={`flex items-center gap-1 text-xs px-2 py-1 rounded border ${
            deckGraded ? 'border-emerald-600 text-emerald-300' : 'border-slate-600 text-slate-300 hover:bg-slate-800'
          }`}
        >
          <Palette size={13} /> Deck-level (#18)
        </button>

        <div className="flex items-center gap-1">
          <button onClick={() => goto(index - 1)} disabled={index === 0} className="p-1 rounded hover:bg-slate-800 disabled:opacity-40 text-slate-300">
            <ChevronLeft size={18} />
          </button>
          <span className="text-xs text-slate-300 w-16 text-center">
            Pair {index + 1}/{total}
          </span>
          <button onClick={() => goto(index + 1)} disabled={index === total - 1} className="p-1 rounded hover:bg-slate-800 disabled:opacity-40 text-slate-300">
            <ChevronRight size={18} />
          </button>
        </div>
      </div>

      {/* body */}
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 min-w-0">
          <ImageViewer
            key={pair?.index}
            inputSrc={pair?.input_image}
            outputSrc={pair?.output_image}
            outputLabel={`OUTPUT · ${deck.variant_label}`}
          />
        </div>

        <aside className="w-[40rem] shrink-0 border-l border-slate-800 flex flex-col bg-slate-900">
          <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800">
            <span className="text-sm font-semibold text-slate-200">Slide-level modes</span>
            <span className="flex items-center gap-1 text-xs text-slate-400">
              {pair?.reviewed ? (
                <>
                  <Check size={13} className="text-emerald-400" /> complete
                </>
              ) : (
                'in progress'
              )}
            </span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 border-b border-slate-800">
            <ModeFilter
              modes={pairModes}
              elementOrder={modes.element_order}
              value={modeFilter}
              onChange={onModeFilterChange}
            />
            <div className="flex-1" />
            <AiStatusDot status={aiStatus} />
            <button
              onClick={() => runPairAi(false)}
              disabled={aiRun?.active || !aiReady}
              title={
                aiStatus && !aiStatus.eval_server_reachable
                  ? 'Start the eval-server: yarn dev:eval-server'
                  : 'Run all AI graders for this pair'
              }
              className="flex items-center gap-1.5 whitespace-nowrap text-xs px-2 py-1 rounded border border-indigo-600 text-indigo-200 hover:bg-indigo-600/15 disabled:opacity-40"
            >
              {aiRun?.active ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
              {aiRun?.active ? 'Grading…' : 'Run AI'}
            </button>
          </div>
          <div className="flex-1 overflow-auto thin-scroll">
            {pair &&
              (visiblePairModes.length ? (
                <ModePanel
                  modes={visiblePairModes}
                  elementOrder={modes.element_order}
                  values={pair.modes}
                  onChange={updatePairMode}
                  aiByMode={aiForPair}
                  gradeableIds={gradeableIds}
                  regradingIds={regrading}
                  onRegrade={aiReady ? regradeMode : undefined}
                />
              ) : (
                <div className="p-4 text-center text-sm text-slate-400">
                  No modes match the filter.
                  <button
                    onClick={() => onModeFilterChange(null)}
                    className="block mx-auto mt-2 text-xs text-indigo-300 hover:text-indigo-200"
                  >
                    Show all modes
                  </button>
                </div>
              ))}
          </div>
        </aside>
      </div>

      {/* deck-level modal */}
      {showDeckPanel && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={() => setShowDeckPanel(false)}>
          <div className="bg-slate-900 border border-slate-700 rounded-lg w-full max-w-lg max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
              <div>
                <h3 className="font-semibold text-slate-100">Deck-level grading</h3>
                <p className="text-xs text-slate-400">Graded once per deck — applies to the whole deck, not a single slide.</p>
              </div>
              <button onClick={() => setShowDeckPanel(false)} className="p-1 rounded hover:bg-slate-800 text-slate-400">
                <X size={18} />
              </button>
            </div>
            <div className="overflow-auto thin-scroll">
              {deckModes.map((m) => (
                <ModeRow key={m.id} mode={m} value={deck.deck_level[String(m.id)]} onChange={(partial) => updateDeckMode(String(m.id), partial)} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
