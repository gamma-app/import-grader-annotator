import { useEffect, useRef, useState } from 'react'
import { Upload, Loader2, X } from 'lucide-react'
import { api } from '../api'

// Human labels for the backend import job stages (see app/importer.py).
const STAGE_LABEL = {
  queued: 'Queued…',
  converting: 'Converting PPTX → input.pdf…',
  importing: 'Running gamma current import…',
  finalizing: 'Saving & rendering…',
  done: 'Done',
  error: 'Failed',
}

// One-time terminal command that captures the gamma.app login session.
const LOGIN_CMD = 'backend/.venv/bin/python -m app.gamma_login'

export default function ImportPanel({ onImported, showToast }) {
  const [status, setStatus] = useState(null)
  const [open, setOpen] = useState(false)
  const [file, setFile] = useState(null)
  const [title, setTitle] = useState('')
  const [job, setJob] = useState(null)
  const pollRef = useRef(null)

  const busy = !!(job && (job.status === 'running' || job.status === 'cancelling'))
  const ready = !!(status && status.ready)

  const stopPoll = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  const startPoll = (id) => {
    stopPoll()
    pollRef.current = setInterval(async () => {
      try {
        const j = await api.getImportJob(id)
        setJob(j)
        if (j.status !== 'running' && j.status !== 'cancelling') {
          stopPoll()
          if (j.status === 'done') {
            showToast({ type: 'success', msg: `Imported “${j.slug}” — ready to grade.` })
            onImported && onImported()
          } else {
            showToast({ type: 'error', msg: j.error || `Import ${j.status}.` })
          }
        }
      } catch {
        stopPoll()
      }
    }, 1500)
  }

  useEffect(() => {
    api.getImportStatus().then(setStatus).catch(() => {})
    // Resume polling an import that's still running (e.g. after a page reload).
    api
      .getImportJobs()
      .then((r) => {
        if (r.active) {
          setJob(r.active)
          startPoll(r.active.id)
        }
      })
      .catch(() => {})
    return () => stopPoll()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async () => {
    if (!file) return
    try {
      const j = await api.startImport({ file, title: title.trim() })
      setJob(j)
      setOpen(false)
      setFile(null)
      setTitle('')
      if (j.status === 'running' || j.status === 'cancelling') startPoll(j.id)
      else if (j.status === 'done') {
        showToast({ type: 'success', msg: `Imported “${j.slug}”.` })
        onImported && onImported()
      }
    } catch (e) {
      showToast({ type: 'error', msg: String(e) })
    }
  }

  const cancel = async () => {
    if (!job) return
    try {
      setJob(await api.cancelImportJob(job.id))
    } catch (e) {
      showToast({ type: 'error', msg: String(e) })
    }
  }

  // While an import runs, the button becomes a live status chip with Cancel.
  if (busy) {
    return (
      <div className="flex items-center gap-2 text-sm border border-indigo-700/60 bg-indigo-950/40 text-indigo-100 px-3 py-1.5 rounded">
        <Loader2 size={15} className="animate-spin text-indigo-300" />
        <span className="font-medium truncate max-w-[10rem]">{job.title || job.slug}</span>
        <span className="text-xs text-indigo-300/80 truncate">
          {STAGE_LABEL[job.stage] || job.message || '…'}
        </span>
        <button
          onClick={cancel}
          disabled={job.status === 'cancelling'}
          className="ml-1 text-xs px-1.5 py-0.5 rounded border border-indigo-600/60 text-indigo-200 hover:bg-indigo-600/20 disabled:opacity-50"
        >
          {job.status === 'cancelling' ? 'Cancelling…' : 'Cancel'}
        </button>
      </div>
    )
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        title="Upload a PowerPoint and run the gamma current import to create a gradable pair"
        className="flex items-center gap-2 text-sm border border-slate-700 hover:bg-slate-800 px-3 py-1.5 rounded text-slate-200"
      >
        <Upload size={16} /> Import PPTX
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-5 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <h2 className="text-base font-semibold text-slate-100">Import a PowerPoint</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Runs the gamma <span className="text-indigo-300">current import</span> and saves a
                  gradable pair (<code className="text-slate-300">input.pdf</code> +{' '}
                  <code className="text-slate-300">current_output.pdf</code>).
                </p>
              </div>
              <button onClick={() => setOpen(false)} className="text-slate-500 hover:text-slate-300">
                <X size={18} />
              </button>
            </div>

            {!ready && (
              <div className="mb-3 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-200">
                <p className="font-medium mb-1">Importer not ready</p>
                <ul className="list-disc list-inside space-y-0.5">
                  {(status?.missing || ['checking…']).map((m) => (
                    <li key={m}>{m}</li>
                  ))}
                </ul>
                <p className="mt-2 text-amber-200/80">
                  Capture a gamma session once with:
                  <code className="block mt-1 bg-slate-950/60 rounded px-2 py-1 text-[11px] text-slate-200">
                    {LOGIN_CMD}
                  </code>
                </p>
              </div>
            )}

            <label className="block text-xs font-medium text-slate-300 mb-1">PowerPoint file</label>
            <input
              type="file"
              accept=".pptx,.ppt,application/vnd.openxmlformats-officedocument.presentationml.presentation"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-slate-300 mb-3 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-indigo-600 file:text-white hover:file:bg-indigo-500"
            />

            <label className="block text-xs font-medium text-slate-300 mb-1">
              Title <span className="text-slate-500">(optional — defaults to the filename)</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={file ? file.name.replace(/\.(pptx|ppt)$/i, '') : 'Deck title'}
              className="block w-full text-sm bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-slate-100 placeholder:text-slate-500 mb-4"
            />

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setOpen(false)}
                className="text-sm px-3 py-1.5 rounded border border-slate-700 text-slate-300 hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={submit}
                disabled={!file || !ready}
                title={!ready ? 'Importer not ready (see above)' : !file ? 'Choose a .pptx first' : ''}
                className="flex items-center gap-2 text-sm px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white"
              >
                <Upload size={15} /> Import
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
