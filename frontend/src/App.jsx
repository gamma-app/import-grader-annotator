import { useEffect, useState } from 'react'
import { Download, Loader2, Layers } from 'lucide-react'
import { api } from './api'
import Dashboard from './components/Dashboard.jsx'
import DeckView from './components/DeckView.jsx'

export default function App() {
  const [modes, setModes] = useState(null)
  const [error, setError] = useState(null)
  const [view, setView] = useState({ name: 'dashboard' })
  const [variant, setVariant] = useState(() => localStorage.getItem('variant') || 'ideal')
  const [exporting, setExporting] = useState(false)
  const [toast, setToast] = useState(null)
  // View-only failure-mode filter for the grading rail: null = all modes shown,
  // or a Set of visible mode ids. App-wide and session-only (not persisted).
  const [modeFilter, setModeFilter] = useState(null)

  useEffect(() => {
    api.getModes().then(setModes).catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    localStorage.setItem('variant', variant)
  }, [variant])

  const showToast = (t) => {
    setToast(t)
    setTimeout(() => setToast(null), 4500)
  }

  const onExport = async () => {
    setExporting(true)
    try {
      const r = await api.runExport()
      showToast({ type: 'success', msg: `Exported ${r.row_count} rows · ${r.deck_count} decks → data/exports/` })
    } catch (e) {
      showToast({ type: 'error', msg: String(e) })
    } finally {
      setExporting(false)
    }
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center p-8 text-center">
        <div className="max-w-md">
          <p className="text-rose-400 font-semibold mb-2">Couldn't reach the backend</p>
          <p className="text-slate-400 text-sm">{error}</p>
          <p className="text-slate-500 text-xs mt-4">Make sure the API is running on port 8000.</p>
        </div>
      </div>
    )
  }

  if (!modes) {
    return (
      <div className="h-full flex items-center justify-center text-slate-400">
        <Loader2 className="animate-spin mr-2" size={20} /> Loading…
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      <header className="flex items-center gap-4 px-5 py-3 border-b border-slate-800 bg-slate-900/80 backdrop-blur">
        <button
          className="flex items-center gap-2 font-semibold text-slate-100"
          onClick={() => setView({ name: 'dashboard' })}
        >
          <Layers size={20} className="text-indigo-400" />
          Import Slide-Pair Grader
        </button>

        <div className="ml-1 flex items-center bg-slate-800/80 border border-slate-700 rounded-lg p-0.5 text-sm">
          {modes.variants.map((v) => (
            <button
              key={v.key}
              onClick={() => setVariant(v.key)}
              title={v.pdf}
              className={`px-3 py-1 rounded-md transition ${
                variant === v.key ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:text-white'
              }`}
            >
              {v.label}
            </button>
          ))}
        </div>

        <div className="flex-1" />
        <button
          onClick={onExport}
          disabled={exporting}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium px-3 py-1.5 rounded"
        >
          {exporting ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
          Export
        </button>
      </header>

      <main className="flex-1 overflow-hidden">
        {view.name === 'dashboard' ? (
          <Dashboard
            variant={variant}
            onOpen={(slug) => setView({ name: 'deck', slug })}
            showToast={showToast}
          />
        ) : (
          <DeckView
            key={`${view.slug}:${variant}`}
            slug={view.slug}
            variant={variant}
            modes={modes}
            modeFilter={modeFilter}
            onModeFilterChange={setModeFilter}
            onBack={() => setView({ name: 'dashboard' })}
            showToast={showToast}
          />
        )}
      </main>

      {toast && (
        <div
          className={`fixed bottom-5 right-5 px-4 py-2.5 rounded-lg shadow-lg text-sm font-medium ${
            toast.type === 'error'
              ? 'bg-rose-600 text-white'
              : 'bg-emerald-600 text-white'
          }`}
        >
          {toast.msg}
        </div>
      )}
    </div>
  )
}
