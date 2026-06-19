import { useEffect, useState } from 'react'
import { AlertTriangle, RefreshCw, FileWarning, Loader2, ChevronRight, ChevronDown } from 'lucide-react'
import { api } from '../api'

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

function DeckCard({ d, stats, onOpen }) {
  const openable = stats.available && stats.pair_count > 0
  return (
    <button
      onClick={() => openable && onOpen(d.slug)}
      disabled={!openable}
      className="text-left bg-slate-900 border border-slate-800 hover:border-indigo-600 disabled:opacity-60 disabled:hover:border-slate-800 rounded-lg p-4 transition group w-full"
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <h2 className="font-medium text-slate-100 leading-tight">{d.title}</h2>
          <p className="text-xs text-slate-500 mt-0.5">{d.slug}</p>
        </div>
        {openable && (
          <ChevronRight size={18} className="text-slate-600 group-hover:text-indigo-400 shrink-0" />
        )}
      </div>

      <ProgressBar done={stats.reviewed_count} total={stats.pair_count} />

      <div className="flex flex-wrap gap-1.5 mt-3">
        {!stats.available && (
          <span className="flex items-center gap-1 text-xs px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-300 border border-rose-500/30">
            <FileWarning size={12} /> output not uploaded
          </span>
        )}
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
    </button>
  )
}

export default function Dashboard({ variant, onOpen, showToast }) {
  const [decks, setDecks] = useState(null)
  const [busy, setBusy] = useState(false)
  const [showMisaligned, setShowMisaligned] = useState(false)
  const [showUnavailable, setShowUnavailable] = useState(false)

  const load = () =>
    api.getDecks().then((r) => setDecks(r.decks)).catch((e) => showToast({ type: 'error', msg: String(e) }))

  useEffect(() => {
    load()
  }, [])

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
  const unavailable = withStats.filter((x) => !x.stats.available)

  return (
    <div className="h-full overflow-auto thin-scroll p-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-lg font-semibold text-slate-100">Decks</h1>
            <p className="text-sm text-slate-400">
              {aligned.length} aligned
              {misaligned.length > 0 ? ` · ${misaligned.length} misaligned` : ''}
              {unavailable.length > 0 ? ` · ${unavailable.length} awaiting output` : ''}
            </p>
          </div>
          <button
            onClick={onRescan}
            disabled={busy}
            className="flex items-center gap-2 text-sm border border-slate-700 hover:bg-slate-800 disabled:opacity-50 px-3 py-1.5 rounded text-slate-200"
          >
            {busy ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
            Rescan / re-render
          </button>
        </div>

        {decks.length === 0 ? (
          <div className="border border-dashed border-slate-700 rounded-lg p-10 text-center text-slate-400">
            <p className="font-medium text-slate-300 mb-1">No decks found</p>
            <p className="text-sm">
              Add a folder under <code className="text-indigo-300">data/decks/&lt;slug&gt;/</code> containing
              <code className="text-indigo-300"> input.pdf</code>, <code className="text-indigo-300">ideal_output.pdf</code>, and <code className="text-indigo-300">current_output.pdf</code>, then Rescan.
            </p>
          </div>
        ) : (
          <>
            {aligned.length === 0 ? (
              <p className="text-sm text-slate-500">No aligned decks for this view.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {aligned.map(({ d, stats }) => (
                  <DeckCard key={d.slug} d={d} stats={stats} onOpen={onOpen} />
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
                    input ≠ output page count — set aside for manual handling
                  </span>
                </button>
                {showMisaligned && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 border-l-2 border-amber-500/30 pl-4">
                    {misaligned.map(({ d, stats }) => (
                      <DeckCard key={d.slug} d={d} stats={stats} onOpen={onOpen} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {unavailable.length > 0 && (
              <div className="mt-8">
                <button
                  onClick={() => setShowUnavailable((s) => !s)}
                  className="flex items-center gap-2 w-full text-left mb-3"
                >
                  {showUnavailable ? (
                    <ChevronDown size={16} className="text-slate-400" />
                  ) : (
                    <ChevronRight size={16} className="text-slate-400" />
                  )}
                  <span className="flex items-center gap-1.5 text-sm font-semibold text-slate-300">
                    <FileWarning size={15} /> Awaiting output ({unavailable.length})
                  </span>
                  <span className="text-xs text-slate-500 hidden sm:inline">
                    no output PDF uploaded for this view yet
                  </span>
                </button>
                {showUnavailable && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 border-l-2 border-slate-600/40 pl-4">
                    {unavailable.map(({ d, stats }) => (
                      <DeckCard key={d.slug} d={d} stats={stats} onOpen={onOpen} />
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
