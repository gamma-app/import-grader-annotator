import { useState } from 'react'
import { RefreshCw, Loader2 } from 'lucide-react'
import { GRADE_META, GRADE_ORDER, SEVERITY_META, GRADE_DOT, AI_VERDICT_CHIP, AI_VERDICT_LABEL } from '../constants'

function AiCell({ ai, gradeable, onRegrade, regrading }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="w-60 shrink-0 border-l border-slate-800 bg-slate-900/40 px-3 py-2.5">
      {!gradeable ? (
        <div className="text-[11px] text-slate-500 italic">no AI grader</div>
      ) : regrading ? (
        <div className="flex items-center gap-1.5 text-[11px] text-indigo-300">
          <Loader2 size={12} className="animate-spin" /> grading…
        </div>
      ) : !ai ? (
        <div className="flex items-center justify-between gap-2">
          <span className="text-[11px] text-slate-500">not run</span>
          {onRegrade && (
            <button
              onClick={onRegrade}
              title="Run this grader"
              className="p-0.5 rounded text-slate-500 hover:text-indigo-300 hover:bg-slate-800"
            >
              <RefreshCw size={12} />
            </button>
          )}
        </div>
      ) : (
        <div>
          <div className="flex items-center justify-between gap-2">
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${AI_VERDICT_CHIP[ai.verdict] || AI_VERDICT_CHIP.error}`}
            >
              {AI_VERDICT_LABEL[ai.verdict] || ai.verdict}
            </span>
            {onRegrade && (
              <button
                onClick={onRegrade}
                title="Re-grade"
                className="p-0.5 rounded text-slate-500 hover:text-indigo-300 hover:bg-slate-800"
              >
                <RefreshCw size={12} />
              </button>
            )}
          </div>
          {ai.reason && (
            <button
              onClick={() => setExpanded((v) => !v)}
              title={expanded ? 'Click to collapse' : 'Click to expand'}
              className={`mt-1 w-full text-left text-[11px] leading-snug text-slate-400 hover:text-slate-300 ${expanded ? '' : 'line-clamp-3'}`}
            >
              {ai.reason}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export function ModeRow({ mode, value, onChange, showAi = false, ai, gradeable = false, onRegrade, regrading = false }) {
  const grade = value?.grade || 'ungraded'
  const note = value?.note || ''
  const manual = (
    <div className="flex-1 min-w-0 px-3 py-2.5">
      <div className="flex items-start gap-2">
        <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${GRADE_DOT[grade]}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-sm text-slate-200 font-medium">
              <span className="text-slate-500">#{mode.id}</span> {mode.name}
            </span>
            <span className={`text-[10px] px-1 rounded ${SEVERITY_META[mode.severity] || ''}`}>{mode.severity}</span>
            <span className="text-[10px] px-1 rounded bg-slate-700/40 text-slate-400 border border-slate-600/40">
              {mode.dimension}
            </span>
          </div>

          <div className="flex gap-1.5 mt-1.5">
            {GRADE_ORDER.map((g) => {
              const active = grade === g
              const meta = GRADE_META[g]
              return (
                <button
                  key={g}
                  onClick={() => onChange({ grade: active ? 'ungraded' : g })}
                  className={`text-xs px-2 py-0.5 rounded border transition ${active ? meta.active : meta.idle}`}
                >
                  {meta.label}
                </button>
              )
            })}
          </div>

          <textarea
            value={note}
            onChange={(e) => onChange({ note: e.target.value })}
            placeholder="note…"
            rows={note ? 2 : 1}
            className="mt-2 w-full bg-slate-800/60 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 resize-y"
          />
        </div>
      </div>
    </div>
  )

  if (!showAi) {
    return <div className="border-b border-slate-800">{manual}</div>
  }
  return (
    <div className="flex border-b border-slate-800">
      {manual}
      <AiCell ai={ai} gradeable={gradeable} onRegrade={onRegrade} regrading={regrading} />
    </div>
  )
}

export default function ModePanel({
  modes,
  elementOrder,
  values,
  onChange,
  aiByMode = {},
  gradeableIds,
  onRegrade,
  regradingIds,
}) {
  const byElement = {}
  modes.forEach((m) => {
    ;(byElement[m.element] ||= []).push(m)
  })
  const order = elementOrder.filter((e) => byElement[e])
  const hasGrader = (id) => (gradeableIds ? gradeableIds.has(id) : false)
  const isRegrading = (id) => (regradingIds ? regradingIds.has(id) : false)

  return (
    <div>
      {order.map((el) => (
        <div key={el}>
          <div className="sticky top-0 z-10 bg-slate-900/95 backdrop-blur px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400 border-b border-slate-800">
            {el}
          </div>
          {byElement[el].map((m) => (
            <ModeRow
              key={m.id}
              mode={m}
              value={values[String(m.id)]}
              onChange={(partial) => onChange(String(m.id), partial)}
              showAi
              ai={aiByMode[String(m.id)]}
              gradeable={hasGrader(m.id)}
              regrading={isRegrading(m.id)}
              onRegrade={onRegrade ? () => onRegrade(m.id) : undefined}
            />
          ))}
        </div>
      ))}
    </div>
  )
}
