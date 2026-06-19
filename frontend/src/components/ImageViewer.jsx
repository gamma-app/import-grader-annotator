import { useCallback, useRef, useState } from 'react'
import { ZoomIn, ZoomOut, Maximize2, Minimize2, RotateCcw } from 'lucide-react'

const MIN_SCALE = 1
const MAX_SCALE = 8

// A side-by-side viewer where both panels share one zoom/pan transform, so the
// same region of input vs output stays aligned while you compare them.
export default function ImageViewer({ inputSrc, outputSrc, outputLabel = 'OUTPUT' }) {
  const [t, setT] = useState({ scale: 1, x: 0, y: 0 })
  const [fullscreen, setFullscreen] = useState(false)
  const drag = useRef(null)

  const clamp = (s) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, s))

  const reset = useCallback(() => setT({ scale: 1, x: 0, y: 0 }), [])

  const zoomAt = useCallback((rect, cx, cy, factor) => {
    setT((prev) => {
      const next = clamp(prev.scale * factor)
      if (next === prev.scale) return prev
      const k = next / prev.scale
      // Keep the point under the cursor fixed (container coords, origin 0,0).
      const x = cx - (cx - prev.x) * k
      const y = cy - (cy - prev.y) * k
      return { scale: next, x: next === 1 ? 0 : x, y: next === 1 ? 0 : y }
    })
  }, [])

  const onWheel = (e) => {
    e.preventDefault()
    const rect = e.currentTarget.getBoundingClientRect()
    const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15
    zoomAt(rect, e.clientX - rect.left, e.clientY - rect.top, factor)
  }

  const onPointerDown = (e) => {
    drag.current = { sx: e.clientX, sy: e.clientY, ox: t.x, oy: t.y }
    e.currentTarget.setPointerCapture?.(e.pointerId)
  }
  const onPointerMove = (e) => {
    if (!drag.current) return
    setT((prev) => ({ ...prev, x: drag.current.ox + (e.clientX - drag.current.sx), y: drag.current.oy + (e.clientY - drag.current.sy) }))
  }
  const onPointerUp = (e) => {
    drag.current = null
    e.currentTarget?.releasePointerCapture?.(e.pointerId)
  }

  const Panel = ({ label, src, color }) => (
    <div
      className="relative flex-1 overflow-hidden bg-slate-950 select-none touch-none"
      onWheel={onWheel}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerLeave={onPointerUp}
      onDoubleClick={reset}
      style={{ cursor: drag.current ? 'grabbing' : t.scale > 1 ? 'grab' : 'default' }}
    >
      <div className={`absolute top-2 left-2 z-10 text-xs font-semibold px-2 py-0.5 rounded ${color}`}>{label}</div>
      <div
        className="w-full h-full flex items-center justify-center"
        style={{ transform: `translate(${t.x}px, ${t.y}px) scale(${t.scale})`, transformOrigin: '0 0' }}
      >
        {src ? (
          <img src={src} draggable={false} className="max-w-full max-h-full object-contain pointer-events-none" />
        ) : (
          <span className="text-slate-600 text-sm">no image</span>
        )}
      </div>
    </div>
  )

  return (
    <div className={fullscreen ? 'fixed inset-0 z-50 bg-slate-950 flex flex-col' : 'h-full flex flex-col'}>
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-slate-800 bg-slate-900">
        <span className="text-xs text-slate-400 mr-1">Zoom {Math.round(t.scale * 100)}%</span>
        <button className="p-1 rounded hover:bg-slate-800 text-slate-300" onClick={() => setT((p) => ({ ...p, scale: clamp(p.scale / 1.25) }))} title="Zoom out">
          <ZoomOut size={16} />
        </button>
        <button className="p-1 rounded hover:bg-slate-800 text-slate-300" onClick={() => setT((p) => ({ ...p, scale: clamp(p.scale * 1.25) }))} title="Zoom in">
          <ZoomIn size={16} />
        </button>
        <button className="p-1 rounded hover:bg-slate-800 text-slate-300" onClick={reset} title="Reset (double-click)">
          <RotateCcw size={16} />
        </button>
        <div className="flex-1" />
        <span className="text-xs text-slate-500 mr-1 hidden md:inline">scroll to zoom · drag to pan</span>
        <button className="p-1 rounded hover:bg-slate-800 text-slate-300" onClick={() => setFullscreen((f) => !f)} title="Fullscreen">
          {fullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
        </button>
      </div>
      <div className="flex-1 flex gap-px bg-slate-800 min-h-0">
        <Panel label="INPUT (original)" src={inputSrc} color="bg-sky-500/20 text-sky-200 border border-sky-500/40" />
        <Panel label={outputLabel} src={outputSrc} color="bg-violet-500/20 text-violet-200 border border-violet-500/40" />
      </div>
    </div>
  )
}
