import { GRADE_META, GRADE_ORDER, SEVERITY_META, GRADE_DOT } from '../constants'

export function ModeRow({ mode, value, onChange }) {
  const grade = value?.grade || 'ungraded'
  const note = value?.note || ''
  return (
    <div className="px-3 py-2.5 border-b border-slate-800">
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
}

export default function ModePanel({ modes, elementOrder, values, onChange }) {
  const byElement = {}
  modes.forEach((m) => {
    ;(byElement[m.element] ||= []).push(m)
  })
  const order = elementOrder.filter((e) => byElement[e])

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
            />
          ))}
        </div>
      ))}
    </div>
  )
}
