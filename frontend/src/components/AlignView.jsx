import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, ArrowRight, Trash2, Check, AlertTriangle, Loader2, Scissors } from 'lucide-react'
import { api } from '../api'

// Guided "drop the extra output pages" workspace for a misaligned variant.
// The annotator marks which output slides to remove until the output lines up
// 1:1 with the input; Save destructively rewrites the output PDF (backed up once)
// and unlocks the deck for grading. There is no in-app reset.
export default function AlignView({ slug, variant, modes, onBack, onDone, showToast }) {
  const [deck, setDeck] = useState(null)
  const [error, setError] = useState(null)
  const [dropped, setDropped] = useState(() => new Set()) // 1-based output page numbers
  const [saving, setSaving] = useState(false)

  const variantLabel =
    modes?.variants?.find((v) => v.key === variant)?.label || deck?.variant_label || variant

  useEffect(() => {
    let alive = true
    setDeck(null)
    setError(null)
    api
      .getDeck(slug, variant)
      .then((d) => alive && setDeck(d))
      .catch((e) => alive && setError(String(e)))
    return () => {
      alive = false
    }
  }, [slug, variant])

  // Full ordered lists: pairs first (positional), then the leftover unpaired ones.
  // Output position i (0-based) maps to PDF page i+1 (PNGs render 1:1 with pages).
  const inputs = useMemo(
    () => (deck ? [...deck.pairs.map((p) => p.input_image), ...(deck.unpaired?.input || [])] : []),
    [deck],
  )
  const outputs = useMemo(
    () => (deck ? [...deck.pairs.map((p) => p.output_image), ...(deck.unpaired?.output || [])] : []),
    [deck],
  )

  const inputCount = inputs.length
  const outputCount = outputs.length
  const target = outputCount - inputCount // # of slides to drop
  const remaining = outputCount - dropped.size
  const canAlign = outputCount > inputCount
  const canSave = canAlign && remaining === inputCount && !saving

  const toggle = (page) =>
    setDropped((prev) => {
      const next = new Set(prev)
      if (next.has(page)) next.delete(page)
      else next.add(page)
      return next
    })

  const dropTrailing = () =>
    setDropped(new Set(Array.from({ length: target }, (_, i) => inputCount + i + 1)))
  const clearDrops = () => setDropped(new Set())

  // Resulting pairing once the marked outputs are removed.
  const remainingOutputs = useMemo(
    () => outputs.map((src, i) => ({ src, page: i + 1 })).filter((o) => !dropped.has(o.page)),
    [outputs, dropped],
  )
  const pairingRows = useMemo(() => {
    const n = Math.max(inputCount, remainingOutputs.length)
    return Array.from({ length: n }, (_, i) => ({
      input: inputs[i] || null,
      output: remainingOutputs[i] || null,
    }))
  }, [inputs, remainingOutputs, inputCount])

  const onSave = async () => {
    const dropPages = [...dropped].sort((a, b) => a - b)
    setSaving(true)
    try {
      await api.alignDeck(slug, variant, dropPages)
      showToast({
        type: 'success',
        msg: `Aligned — dropped ${dropPages.length} slide(s) · now ${inputCount}/${inputCount}.`,
      })
      onDone()
    } catch (e) {
      showToast({ type: 'error', msg: String(e) })
    } finally {
      setSaving(false)
    }
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center p-8 text-center">
        <div className="max-w-md">
          <p className="text-rose-400 font-semibold mb-2">Couldn't load deck</p>
          <p className="text-slate-400 text-sm">{error}</p>
          <button onClick={onBack} className="mt-4 text-sm text-indigo-300 hover:text-indigo-200">
            Back to decks
          </button>
        </div>
      </div>
    )
  }

  if (!deck) {
    return (
      <div className="h-full flex items-center justify-center text-slate-400">
        <Loader2 className="animate-spin mr-2" size={20} /> Loading deck…
      </div>
    )
  }

  // Can't fix output<input (or already-aligned) by dropping output slides.
  if (!canAlign) {
    const aligned = outputCount === inputCount
    return (
      <div className="h-full flex flex-col">
        <Header
          deck={deck}
          variantLabel={variantLabel}
          onBack={onBack}
          right={null}
        />
        <div className="flex-1 flex items-center justify-center p-8 text-center">
          <div className="max-w-md">
            <AlertTriangle className="mx-auto mb-3 text-amber-400" size={28} />
            <p className="font-semibold text-slate-100 mb-1">
              {aligned ? 'This variant is already aligned' : "Can't align by dropping output slides"}
            </p>
            <p className="text-sm text-slate-400">
              {aligned
                ? `Output and input both have ${inputCount} slides.`
                : `The output has ${outputCount} slides but the input has ${inputCount}. Dropping output slides can only fix decks where output > input.`}
            </p>
            <button
              onClick={aligned ? onDone : onBack}
              className="mt-4 text-sm px-3 py-1.5 rounded border border-indigo-600 text-indigo-200 hover:bg-indigo-600/15"
            >
              {aligned ? 'Open deck' : 'Back to decks'}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      <Header
        deck={deck}
        variantLabel={variantLabel}
        onBack={onBack}
        right={
          <div className="flex items-center gap-3">
            <span
              className={`text-xs font-medium flex items-center gap-1.5 ${
                remaining === inputCount ? 'text-emerald-300' : 'text-amber-300'
              }`}
            >
              {remaining === inputCount ? <Check size={14} /> : <AlertTriangle size={14} />}
              remaining {remaining} / input {inputCount}
            </span>
            <button
              onClick={onSave}
              disabled={!canSave}
              title={
                canSave
                  ? 'Drop the marked slides and align this deck'
                  : `Mark exactly ${target} slide(s) to drop (currently ${dropped.size})`
              }
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-sm font-medium px-3 py-1.5 rounded"
            >
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Scissors size={16} />}
              {saving ? 'Aligning…' : 'Save alignment'}
            </button>
          </div>
        }
      />

      {/* instruction strip */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-slate-800 bg-slate-900/60 text-xs">
        <span className="text-slate-300">
          Drop <span className="font-semibold text-amber-300">{target}</span> extra output slide
          {target === 1 ? '' : 's'} to line up 1:1 with the input.
        </span>
        <span className="text-slate-600">·</span>
        <button onClick={dropTrailing} className="text-indigo-300 hover:text-indigo-200">
          Quick: drop last {target}
        </button>
        <button onClick={clearDrops} className="text-slate-400 hover:text-slate-200">
          Clear
        </button>
        <div className="flex-1" />
        <span className="text-slate-500 hidden md:inline">
          Destructive: edits the output PDF (original backed up once).
        </span>
      </div>

      {/* body: input reference | selectable outputs | resulting pairing */}
      <div className="flex-1 flex min-h-0">
        <Column title={`Input · ${inputCount} slides`} subtitle="reference (never changes)">
          {inputs.map((src, i) => (
            <Thumb key={src} src={src} label={`Input ${i + 1}`} />
          ))}
        </Column>

        <Column
          title={`Output · ${variantLabel}`}
          subtitle={`${outputCount} slides — click the extras to drop`}
          accent
        >
          {outputs.map((src, i) => {
            const page = i + 1
            const isDropped = dropped.has(page)
            return (
              <button
                key={src}
                onClick={() => toggle(page)}
                className={`relative block w-full rounded border text-left transition group ${
                  isDropped
                    ? 'border-rose-500/60 bg-rose-950/30'
                    : 'border-slate-700 hover:border-indigo-500 bg-slate-950'
                }`}
              >
                <div className="relative">
                  <img
                    src={src}
                    draggable={false}
                    className={`w-full object-contain rounded-t ${isDropped ? 'opacity-30' : ''}`}
                  />
                  {isDropped && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded bg-rose-600 text-white">
                        <Trash2 size={13} /> dropped
                      </span>
                    </div>
                  )}
                </div>
                <div
                  className={`flex items-center justify-between px-2 py-1 text-[11px] ${
                    isDropped ? 'text-rose-300' : 'text-slate-400'
                  }`}
                >
                  <span>Output p{page}</span>
                  <span className="opacity-0 group-hover:opacity-100 text-slate-500">
                    {isDropped ? 'keep' : 'drop'}
                  </span>
                </div>
              </button>
            )
          })}
        </Column>

        <Column
          title="Resulting pairing"
          subtitle={remaining === inputCount ? 'lines up 1:1 ✓' : `${remaining} output / ${inputCount} input`}
        >
          {pairingRows.map((row, i) => {
            const mismatch = !row.input || !row.output
            return (
              <div
                key={i}
                className={`flex items-center gap-1.5 rounded border p-1 ${
                  mismatch ? 'border-amber-500/50 bg-amber-950/20' : 'border-slate-800 bg-slate-950'
                }`}
              >
                <PairThumb src={row.input} placeholder="no input" />
                <ArrowRight size={14} className={mismatch ? 'text-amber-400 shrink-0' : 'text-slate-600 shrink-0'} />
                <PairThumb src={row.output} placeholder="extra" />
              </div>
            )
          })}
        </Column>
      </div>
    </div>
  )
}

function Header({ deck, variantLabel, onBack, right }) {
  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b border-slate-800 bg-slate-900">
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-300 hover:text-white">
        <ArrowLeft size={16} /> Decks
      </button>
      <div className="h-4 w-px bg-slate-700" />
      <div className="min-w-0">
        <div className="text-sm font-semibold text-slate-100 truncate">{deck.title}</div>
      </div>
      <span className="shrink-0 text-xs px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-200 border border-violet-500/30">
        {variantLabel}
      </span>
      <span className="shrink-0 text-xs px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30">
        Align mode
      </span>
      <div className="flex-1" />
      {right}
    </div>
  )
}

function Column({ title, subtitle, accent, children }) {
  return (
    <div className={`flex-1 min-w-0 flex flex-col border-r border-slate-800 ${accent ? 'bg-slate-900/40' : ''}`}>
      <div className="px-3 py-2 border-b border-slate-800">
        <div className="text-sm font-semibold text-slate-200 truncate">{title}</div>
        <div className="text-[11px] text-slate-500 truncate">{subtitle}</div>
      </div>
      <div className="flex-1 overflow-auto thin-scroll p-2 space-y-2">{children}</div>
    </div>
  )
}

function Thumb({ src, label }) {
  return (
    <div className="rounded border border-slate-700 bg-slate-950">
      <img src={src} draggable={false} className="w-full object-contain rounded-t" />
      <div className="px-2 py-1 text-[11px] text-slate-400">{label}</div>
    </div>
  )
}

function PairThumb({ src, placeholder }) {
  if (!src) {
    return (
      <div className="flex-1 min-w-0 h-16 flex items-center justify-center rounded bg-slate-900 text-[11px] text-amber-400/80">
        {placeholder}
      </div>
    )
  }
  return (
    <img
      src={src}
      draggable={false}
      className="flex-1 min-w-0 max-h-20 object-contain rounded bg-slate-950"
    />
  )
}
