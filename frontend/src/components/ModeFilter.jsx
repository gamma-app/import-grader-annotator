import { useMemo, useState } from 'react'
import { Filter, Check, X } from 'lucide-react'
import { SEVERITY_META } from '../constants'

const SEVERITY_ORDER = ['P0', 'P1', 'P2']

function Box({ checked, partial }) {
  return (
    <span
      className={`shrink-0 w-3.5 h-3.5 rounded-sm border flex items-center justify-center ${
        checked
          ? 'bg-indigo-500 border-indigo-500'
          : partial
            ? 'bg-indigo-500/30 border-indigo-500'
            : 'border-slate-600'
      }`}
    >
      {checked && <Check size={11} className="text-white" />}
    </span>
  )
}

// View-only filter for the slide-level grading rail. `value` is null (= all modes
// shown) or a Set of visible mode ids. App-wide + session-only: it is not persisted.
export default function ModeFilter({ modes, elementOrder, value, onChange }) {
  const [open, setOpen] = useState(false)

  const allIds = useMemo(() => modes.map((m) => m.id), [modes])
  const total = allIds.length
  const isAll = value == null
  const has = (id) => isAll || value.has(id)
  const count = isAll ? total : value.size

  const byElement = useMemo(() => {
    const m = {}
    modes.forEach((x) => (m[x.element] ||= []).push(x))
    return m
  }, [modes])
  const order = elementOrder.filter((e) => byElement[e])

  const severities = SEVERITY_ORDER.filter((s) => modes.some((m) => m.severity === s))

  const emit = (next) => onChange(next.size >= total ? null : next)
  const effective = () => new Set(isAll ? allIds : value)
  const toggleId = (id) => {
    const next = effective()
    next.has(id) ? next.delete(id) : next.add(id)
    emit(next)
  }
  const toggleMany = (ids) => {
    const next = effective()
    const allOn = ids.every((id) => next.has(id))
    ids.forEach((id) => (allOn ? next.delete(id) : next.add(id)))
    emit(next)
  }

  return (
    <div className="relative w-full">
      <div className="flex items-center gap-1">
        <button
          onClick={() => setOpen((o) => !o)}
          className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded border transition ${
            isAll
              ? 'border-slate-600 text-slate-300 hover:bg-slate-800'
              : 'border-indigo-500 text-indigo-200 bg-indigo-500/10'
          }`}
        >
          <Filter size={13} />
          {isAll ? 'Filter modes' : `${count}/${total} modes`}
        </button>
        {!isAll && (
          <button
            onClick={() => onChange(null)}
            title="Clear filter — show all modes"
            className="p-0.5 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800"
          >
            <X size={14} />
          </button>
        )}
      </div>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1.5 z-50 w-80 max-h-[70vh] flex flex-col bg-slate-900 border border-slate-700 rounded-lg shadow-xl">
            <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800">
              <span className="text-sm font-semibold text-slate-200">Show failure modes</span>
              <button onClick={() => setOpen(false)} className="p-0.5 rounded hover:bg-slate-800 text-slate-400">
                <X size={15} />
              </button>
            </div>

            <div className="px-3 py-2 border-b border-slate-800 space-y-2">
              <div className="flex items-center gap-1.5 text-xs">
                <span className="text-slate-500">Quick:</span>
                <button onClick={() => onChange(null)} className="px-2 py-0.5 rounded border border-slate-600 text-slate-300 hover:bg-slate-800">
                  All
                </button>
                <button onClick={() => onChange(new Set())} className="px-2 py-0.5 rounded border border-slate-600 text-slate-300 hover:bg-slate-800">
                  None
                </button>
              </div>
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-xs text-slate-500">Severity:</span>
                {severities.map((s) => {
                  const ids = modes.filter((m) => m.severity === s).map((m) => m.id)
                  const allOn = ids.every((id) => has(id))
                  return (
                    <button
                      key={s}
                      onClick={() => toggleMany(ids)}
                      className={`text-[11px] px-1.5 py-0.5 rounded border ${allOn ? SEVERITY_META[s] || '' : 'border-slate-600 text-slate-400 hover:bg-slate-800'}`}
                    >
                      {s}
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="flex-1 overflow-auto thin-scroll py-1">
              {order.map((el) => {
                const groupIds = byElement[el].map((m) => m.id)
                const allOn = groupIds.every((id) => has(id))
                const someOn = groupIds.some((id) => has(id))
                return (
                  <div key={el} className="mb-1">
                    <button
                      onClick={() => toggleMany(groupIds)}
                      className="w-full flex items-center gap-2 px-3 py-1 text-left hover:bg-slate-800/40"
                    >
                      <Box checked={allOn} partial={someOn && !allOn} />
                      <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">{el}</span>
                    </button>
                    {byElement[el].map((m) => (
                      <button
                        key={m.id}
                        onClick={() => toggleId(m.id)}
                        className="w-full flex items-center gap-2 px-3 py-1 pl-6 text-left hover:bg-slate-800/50"
                      >
                        <Box checked={has(m.id)} />
                        <span className="text-xs text-slate-200 min-w-0 truncate">
                          <span className="text-slate-500">#{m.id}</span> {m.name}
                        </span>
                        <span className={`ml-auto shrink-0 text-[10px] px-1 rounded ${SEVERITY_META[m.severity] || ''}`}>{m.severity}</span>
                      </button>
                    ))}
                  </div>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
