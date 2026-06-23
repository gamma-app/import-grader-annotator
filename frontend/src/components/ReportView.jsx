import { useCallback, useEffect, useMemo, useState } from 'react'
import { ArrowLeft, Loader2, X, ChevronLeft, ChevronRight, BarChart3 } from 'lucide-react'
import { api } from '../api'
import ImageViewer from './ImageViewer.jsx'
import { AI_VERDICT_CHIP, AI_VERDICT_LABEL } from '../constants'

const GRADES = ['pass', 'borderline', 'fail']
const GRADE_LABEL = { pass: 'Pass', borderline: 'Borderline', fail: 'Fail' }
const SEG = { pass: 'bg-emerald-500', borderline: 'bg-amber-500', fail: 'bg-rose-500' }

function ScoreChip({ value }) {
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${AI_VERDICT_CHIP[value] || AI_VERDICT_CHIP.error}`}>
      {AI_VERDICT_LABEL[value] || value}
    </span>
  )
}

function DistBar({ label, dist, total }) {
  return (
    <div>
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span className="font-medium text-slate-300">{label}</span>
        <span>{total} graded</span>
      </div>
      <div className="flex h-3 rounded overflow-hidden bg-slate-800">
        {GRADES.map((g) =>
          dist[g] > 0 ? (
            <div key={g} className={SEG[g]} style={{ width: `${(100 * dist[g]) / total}%` }} title={`${GRADE_LABEL[g]}: ${dist[g]}`} />
          ) : null,
        )}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5 text-[11px] text-slate-400">
        {GRADES.map((g) => (
          <span key={g} className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${SEG[g]}`} />
            {GRADE_LABEL[g]} <span className="text-slate-300 font-medium">{dist[g]}</span>
            {total > 0 && <span className="text-slate-500">({Math.round((100 * dist[g]) / total)}%)</span>}
          </span>
        ))}
      </div>
    </div>
  )
}

function ConfusionMatrix({ confusion }) {
  return (
    <div>
      <div className="text-xs text-slate-400 mb-2">
        Confusion (rows = <span className="text-slate-300">human</span>, columns = <span className="text-slate-300">agent</span>); diagonal = agreement
      </div>
      <div className="inline-grid" style={{ gridTemplateColumns: 'auto repeat(3, 3.5rem)' }}>
        <div />
        {GRADES.map((a) => (
          <div key={a} className="text-[10px] text-slate-400 text-center pb-1 font-medium">{GRADE_LABEL[a]}</div>
        ))}
        {GRADES.map((h) => (
          <MatrixRow key={h} h={h} confusion={confusion} />
        ))}
      </div>
    </div>
  )
}

// One matrix row: a human-label header cell + 3 count cells.
function MatrixRow({ h, confusion }) {
  return (
    <>
      <div className="text-[10px] text-slate-400 pr-2 flex items-center justify-end font-medium">{GRADE_LABEL[h]}</div>
      {GRADES.map((a) => {
        const n = confusion[h][a]
        const diag = h === a
        const cls = diag
          ? 'bg-emerald-500/15 text-emerald-200 border-emerald-500/40'
          : n > 0
            ? 'bg-rose-500/10 text-rose-200 border-rose-500/30'
            : 'bg-slate-800/40 text-slate-600 border-slate-700/60'
        return (
          <div key={a} className={`m-0.5 h-12 rounded border flex items-center justify-center text-sm font-semibold ${cls}`}>
            {n}
          </div>
        )
      })}
    </>
  )
}

function Lightbox({ items, index, variantLabel, onClose, onPrev, onNext }) {
  const d = items[index]
  if (!d) return null
  return (
    <div className="fixed inset-0 z-40 bg-black/80 flex flex-col p-3 sm:p-5" onClick={onClose}>
      <div className="flex-1 flex flex-col bg-slate-900 border border-slate-700 rounded-lg overflow-hidden min-h-0" onClick={(e) => e.stopPropagation()}>
        {/* header */}
        <div className="flex items-center gap-3 px-4 py-2.5 border-b border-slate-800">
          <BarChart3 size={16} className="text-indigo-400 shrink-0" />
          <div className="text-sm font-semibold text-slate-100 truncate">
            {d.title} <span className="text-slate-500 font-normal">· pair {d.pair_index}</span>
          </div>
          <div className="flex-1" />
          <div className="flex items-center gap-1">
            <button onClick={onPrev} disabled={index === 0} className="p-1 rounded hover:bg-slate-800 disabled:opacity-40 text-slate-300" title="Previous (←)">
              <ChevronLeft size={18} />
            </button>
            <span className="text-xs text-slate-400 w-14 text-center">{index + 1} / {items.length}</span>
            <button onClick={onNext} disabled={index === items.length - 1} className="p-1 rounded hover:bg-slate-800 disabled:opacity-40 text-slate-300" title="Next (→)">
              <ChevronRight size={18} />
            </button>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-slate-800 text-slate-400 ml-1" title="Close (Esc)">
            <X size={18} />
          </button>
        </div>
        {/* images */}
        <div className="flex-1 min-h-0">
          <ImageViewer key={`${d.slug}:${d.pair_index}`} inputSrc={d.input_image} outputSrc={d.output_image} outputLabel={`OUTPUT · ${variantLabel}`} />
        </div>
        {/* scores + notes */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-slate-800 border-t border-slate-800 max-h-[34%] overflow-auto thin-scroll">
          <div className="bg-slate-900 p-3">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-xs font-semibold text-slate-300">Human</span>
              <ScoreChip value={d.human_grade} />
            </div>
            <p className="text-xs text-slate-400 whitespace-pre-wrap leading-relaxed">{d.human_note || <span className="italic text-slate-600">no note</span>}</p>
          </div>
          <div className="bg-slate-900 p-3">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-xs font-semibold text-slate-300">Agent</span>
              <ScoreChip value={d.ai_verdict} />
            </div>
            <p className="text-xs text-slate-400 whitespace-pre-wrap leading-relaxed">{d.ai_reason || <span className="italic text-slate-600">no reason</span>}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function ReportView({ variant, modes, showToast, onBack }) {
  const gradeableModes = useMemo(() => {
    const graders = modes.mode_graders || {}
    return modes.modes.filter((m) => Object.prototype.hasOwnProperty.call(graders, String(m.id)))
  }, [modes])

  const [modeId, setModeId] = useState(() => {
    const saved = parseInt(localStorage.getItem('report:modeId') || '', 10)
    if (Number.isInteger(saved) && (modes.mode_graders || {})[String(saved)]) return saved
    return gradeableModes[0]?.id
  })
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [lb, setLb] = useState(null)

  useEffect(() => {
    localStorage.setItem('report:modeId', String(modeId))
  }, [modeId])

  useEffect(() => {
    if (!modeId) return
    let alive = true
    setLoading(true)
    setReport(null)
    setLb(null)
    api
      .getModeReport(modeId, variant)
      .then((r) => alive && setReport(r))
      .catch((e) => alive && showToast({ type: 'error', msg: String(e) }))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [modeId, variant, showToast])

  const dis = report?.disagreements || []
  const closeLb = useCallback(() => setLb(null), [])
  const prevLb = useCallback(() => setLb((i) => (i == null ? i : Math.max(0, i - 1))), [])
  const nextLb = useCallback(() => setLb((i) => (i == null ? i : Math.min(dis.length - 1, i + 1))), [dis.length])

  useEffect(() => {
    if (lb == null) return
    const onKey = (e) => {
      if (e.key === 'Escape') closeLb()
      else if (e.key === 'ArrowLeft') prevLb()
      else if (e.key === 'ArrowRight') nextLb()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [lb, closeLb, prevLb, nextLb])

  const n = report?.counts?.both ?? 0
  const excluded = report ? report.counts.human_only + report.counts.ai_only + report.counts.no_data : 0

  return (
    <div className="h-full flex flex-col">
      {/* sub-header */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-slate-800 bg-slate-900">
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-300 hover:text-white">
          <ArrowLeft size={16} /> Decks
        </button>
        <div className="h-4 w-px bg-slate-700" />
        <BarChart3 size={16} className="text-indigo-400" />
        <span className="text-sm font-semibold text-slate-100">Agreement report</span>
        <select
          value={modeId || ''}
          onChange={(e) => setModeId(Number(e.target.value))}
          className="ml-1 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 max-w-[22rem]"
        >
          {gradeableModes.map((m) => (
            <option key={m.id} value={m.id}>#{m.id} {m.name}</option>
          ))}
        </select>
        <span className="shrink-0 text-xs px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-200 border border-violet-500/30">
          {report?.variant_label || variant}
        </span>
        <div className="flex-1" />
        {loading && <Loader2 size={16} className="animate-spin text-slate-400" />}
      </div>

      {/* body */}
      <div className="flex-1 overflow-auto thin-scroll">
        {!report ? (
          <div className="h-full flex items-center justify-center text-slate-400">
            {loading ? (
              <span className="flex items-center gap-2"><Loader2 className="animate-spin" size={18} /> Loading report…</span>
            ) : (
              'Select a failure mode.'
            )}
          </div>
        ) : n === 0 ? (
          <div className="max-w-md mx-auto text-center mt-20 px-6">
            <BarChart3 size={28} className="mx-auto text-slate-600 mb-3" />
            <p className="text-slate-300 font-medium">No comparable data yet</p>
            <p className="text-sm text-slate-500 mt-1">
              No slide pairs have <em>both</em> a human grade and an agent verdict for{' '}
              <span className="text-slate-300">#{report.mode.id} {report.mode.name}</span> on {report.variant_label}.
              {excluded > 0 && <> {excluded} pair(s) have only one side graded.</>}
            </p>
          </div>
        ) : (
          <div className="max-w-6xl mx-auto p-5 space-y-6">
            {/* summary */}
            <div>
              <div className="flex items-baseline gap-2 flex-wrap">
                <h2 className="text-lg font-semibold text-slate-100">
                  <span className="text-slate-500">#{report.mode.id}</span> {report.mode.name}
                </h2>
                <span className="text-xs text-slate-500">grader: {report.mode.grader}</span>
              </div>
              <p className="text-sm text-slate-400 mt-0.5">
                <span className="text-slate-200 font-medium">{n}</span> pairs with both scores
                {excluded > 0 && (
                  <span className="text-slate-500">
                    {' '}· {excluded} excluded (agent-only {report.counts.ai_only}, human-only {report.counts.human_only}, neither {report.counts.no_data})
                  </span>
                )}
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              {/* distributions */}
              <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-4">
                <h3 className="text-sm font-semibold text-slate-200">Score distribution</h3>
                <DistBar label="Human" dist={report.human_distribution} total={n} />
                <DistBar label="Agent" dist={report.ai_distribution} total={n} />
              </div>
              {/* agreement headline */}
              <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex flex-col justify-center">
                <div className="text-3xl font-bold text-slate-100">{report.agreement_pct}%</div>
                <div className="text-xs text-slate-400">agreement</div>
                <div className="mt-3 flex items-center gap-4 text-sm">
                  <span className="flex items-center gap-1.5 text-emerald-300">
                    <span className="w-2 h-2 rounded-full bg-emerald-500" /> {report.agreements} agree
                  </span>
                  <span className="flex items-center gap-1.5 text-rose-300">
                    <span className="w-2 h-2 rounded-full bg-rose-500" /> {report.disagreements_count} disagree
                  </span>
                </div>
                <div className="mt-2 text-xs text-slate-500">
                  Cohen's κ <span className="text-slate-300 font-medium">{report.cohen_kappa ?? '—'}</span>
                </div>
              </div>
            </div>

            {/* confusion */}
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
              <ConfusionMatrix confusion={report.confusion} />
            </div>

            {/* disagreements gallery */}
            <div>
              <h3 className="text-sm font-semibold text-slate-200 mb-3">
                Disagreements <span className="text-slate-500 font-normal">({dis.length})</span>
              </h3>
              {dis.length === 0 ? (
                <p className="text-sm text-slate-500">Human and agent agree on all {n} compared pairs.</p>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                  {dis.map((d, i) => (
                    <button
                      key={`${d.slug}:${d.pair_index}`}
                      onClick={() => setLb(i)}
                      className="group text-left bg-slate-900 border border-slate-800 rounded-lg overflow-hidden hover:border-indigo-600 transition"
                    >
                      <div className="h-32 bg-slate-950 flex items-center justify-center overflow-hidden">
                        {d.output_image ? (
                          <img src={d.output_image} loading="lazy" className="max-h-full max-w-full object-contain" />
                        ) : (
                          <span className="text-slate-600 text-xs">no image</span>
                        )}
                      </div>
                      <div className="p-2">
                        <div className="text-xs text-slate-300 truncate">{d.title} · pair {d.pair_index}</div>
                        <div className="flex items-center gap-1.5 mt-1.5">
                          <span className="text-[10px] text-slate-500">You</span>
                          <ScoreChip value={d.human_grade} />
                          <span className="text-[10px] text-slate-500 ml-1">AI</span>
                          <ScoreChip value={d.ai_verdict} />
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {lb != null && (
        <Lightbox items={dis} index={lb} variantLabel={report?.variant_label || variant} onClose={closeLb} onPrev={prevLb} onNext={nextLb} />
      )}
    </div>
  )
}
