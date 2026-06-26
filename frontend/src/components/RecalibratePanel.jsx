import { useMemo, useState } from 'react'
import {
  X, Check, AlertTriangle, Loader2, TrendingUp, TrendingDown, Minus,
  ChevronDown, ChevronRight, Trophy,
} from 'lucide-react'

const GRADES = ['pass', 'borderline', 'fail', 'na']
const VERDICT_COLOR = {
  pass: 'text-emerald-300',
  borderline: 'text-amber-300',
  fail: 'text-rose-300',
  na: 'text-slate-400',
}

const fmtK = (k) => (k === null || k === undefined ? '\u2014' : k.toFixed(3))
const fmtP = (p) => (p === null || p === undefined ? '\u2014' : `${p}%`)

// ----- tiny line-level diff (LCS) for the prompt before/after
function diffLines(aText, bText) {
  const a = (aText || '').split('\n')
  const b = (bText || '').split('\n')
  const n = a.length
  const m = b.length
  const dp = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0))
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1])
  const out = []
  let i = 0
  let j = 0
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      out.push({ t: 'ctx', v: a[i] })
      i++
      j++
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      out.push({ t: 'del', v: a[i] })
      i++
    } else {
      out.push({ t: 'add', v: b[j] })
      j++
    }
  }
  while (i < n) out.push({ t: 'del', v: a[i++] })
  while (j < m) out.push({ t: 'add', v: b[j++] })
  return out
}

function Delta({ before, after, pct = false }) {
  const b = before ?? null
  const a = after ?? null
  if (a === null) return <span className="text-slate-500">{'\u2014'}</span>
  const d = b === null ? null : Math.round((a - b) * (pct ? 10 : 1000)) / (pct ? 10 : 1000)
  const up = d !== null && d > 0
  const down = d !== null && d < 0
  const Icon = up ? TrendingUp : down ? TrendingDown : Minus
  const color = up ? 'text-emerald-400' : down ? 'text-rose-400' : 'text-slate-500'
  return (
    <span className={`inline-flex items-center gap-1 ${color}`}>
      <Icon size={12} />
      {d === null ? '' : `${d > 0 ? '+' : ''}${pct ? d.toFixed(1) : d.toFixed(3)}`}
    </span>
  )
}

function ScoreRow({ label, base, win, highlight }) {
  return (
    <tr className={highlight ? 'bg-indigo-950/30' : ''}>
      <td className="py-1.5 px-2 text-slate-300 font-medium">
        {label}
        {highlight && <span className="ml-1.5 text-[10px] text-indigo-300">(held out)</span>}
      </td>
      <td className="py-1.5 px-2 text-right text-slate-400">{base.n}</td>
      <td className="py-1.5 px-2 text-right text-slate-300 tabular-nums">{fmtK(base.cohen_kappa)}</td>
      <td className="py-1.5 px-2 text-right text-slate-100 tabular-nums">{fmtK(win.cohen_kappa)}</td>
      <td className="py-1.5 px-2 text-right tabular-nums">
        <Delta before={base.cohen_kappa} after={win.cohen_kappa} />
      </td>
      <td className="py-1.5 px-2 text-right text-slate-300 tabular-nums">{fmtP(base.agreement_pct)}</td>
      <td className="py-1.5 px-2 text-right text-slate-100 tabular-nums">{fmtP(win.agreement_pct)}</td>
      <td className="py-1.5 px-2 text-right tabular-nums">
        <Delta before={base.agreement_pct} after={win.agreement_pct} pct />
      </td>
    </tr>
  )
}

function Confusion({ title, score }) {
  const conf = score.confusion || {}
  const max = Math.max(1, ...GRADES.flatMap((h) => GRADES.map((a) => conf[h]?.[a] || 0)))
  return (
    <div>
      <div className="text-xs text-slate-400 mb-1">
        {title} <span className="text-slate-500">· κ {fmtK(score.cohen_kappa)} · {fmtP(score.agreement_pct)} · n={score.n}</span>
      </div>
      <table className="text-[11px] border-collapse">
        <thead>
          <tr>
            <th className="p-1 text-slate-500 font-normal text-left">h \ ai</th>
            {GRADES.map((g) => (
              <th key={g} className={`p-1 font-normal ${VERDICT_COLOR[g]}`}>{g.slice(0, 4)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {GRADES.map((h) => (
            <tr key={h}>
              <td className={`p-1 ${VERDICT_COLOR[h]}`}>{h.slice(0, 4)}</td>
              {GRADES.map((a) => {
                const v = conf[h]?.[a] || 0
                const diag = h === a
                const intensity = v ? 0.12 + 0.5 * (v / max) : 0
                return (
                  <td
                    key={a}
                    className={`p-1 text-center tabular-nums border border-slate-800 ${
                      diag ? 'text-emerald-200' : v ? 'text-rose-200' : 'text-slate-600'
                    }`}
                    style={{ background: v ? `rgba(${diag ? '16,185,129' : '244,63,94'},${intensity})` : 'transparent' }}
                  >
                    {v}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function FlipList({ title, items, tone }) {
  const [open, setOpen] = useState(false)
  const color = tone === 'good' ? 'text-emerald-300' : 'text-rose-300'
  if (!items?.length)
    return (
      <div className="text-xs text-slate-500">
        {title}: <span className="text-slate-400">0</span>
      </div>
    )
  return (
    <div>
      <button onClick={() => setOpen((o) => !o)} className={`flex items-center gap-1.5 text-xs font-medium ${color}`}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        {title}: {items.length}
      </button>
      {open && (
        <div className="mt-2 space-y-2 pl-1">
          {items.map((f, i) => (
            <div key={i} className="flex gap-2 items-start border border-slate-800 rounded-lg p-2 bg-slate-900/50">
              <div className="flex gap-1 shrink-0">
                <img src={f.input_image} alt="input" className="w-20 h-auto rounded border border-slate-700" />
                <img src={f.output_image} alt="output" className="w-20 h-auto rounded border border-slate-700" />
              </div>
              <div className="min-w-0 text-[11px]">
                <div className="text-slate-300 truncate">
                  {f.title} <span className="text-slate-500">· {f.variant} · pair {f.pair_index}</span>
                </div>
                <div className="mt-0.5">
                  human <span className={VERDICT_COLOR[f.human_grade]}>{f.human_grade}</span>
                  <span className="text-slate-500"> · was </span>
                  <span className={VERDICT_COLOR[f.before]}>{f.before}</span>
                  <span className="text-slate-500"> {'\u2192'} </span>
                  <span className={VERDICT_COLOR[f.after]}>{f.after}</span>
                </div>
                {f.human_note && <div className="mt-0.5 text-slate-500 line-clamp-2">{f.human_note}</div>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function RecalibratePanel({ run, onClose, onAdopt, onReject, busy }) {
  const [showDiff, setShowDiff] = useState(false)
  const diff = useMemo(
    () => (showDiff ? diffLines(run.current_prompt, run.winner?.prompt) : null),
    [showDiff, run],
  )
  const base = run.baseline || {}
  const win = run.winner?.scores || {}
  const flips = run.winner?.test_flips || { fixed: [], broke: [] }
  const candidates = run.candidates || []
  const decided = run.status === 'approved' || run.status === 'rejected'
  const testKDelta =
    (win.test?.cohen_kappa ?? null) !== null && (base.test?.cohen_kappa ?? null) !== null
      ? win.test.cohen_kappa - base.test.cohen_kappa
      : null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => !busy && onClose()}>
      <div
        className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* header */}
        <div className="flex items-center gap-3 px-5 py-3 border-b border-slate-800 shrink-0">
          <Trophy size={17} className="text-indigo-400" />
          <div className="min-w-0">
            <h2 className="font-semibold text-slate-100 truncate">
              Recalibration proposal <span className="text-slate-500 font-normal">· #{run.mode_id} {run.mode_name}</span>
            </h2>
            <p className="text-[11px] text-slate-500">
              {run.dataset_size} labeled pairs · {run.split_sizes?.train}/{run.split_sizes?.val}/{run.split_sizes?.test} train/val/test ·
              optimizer {run.optimizer_model} · seed {run.seed}
            </p>
          </div>
          <div className="flex-1" />
          {decided && (
            <span className={`text-xs px-2 py-0.5 rounded border ${run.status === 'approved' ? 'border-emerald-600/50 text-emerald-300' : 'border-slate-600 text-slate-400'}`}>
              {run.status}
            </span>
          )}
          <button onClick={() => !busy && onClose()} className="p-1.5 rounded hover:bg-slate-800 text-slate-400">
            <X size={18} />
          </button>
        </div>

        {/* body */}
        <div className="flex-1 overflow-auto thin-scroll p-5 space-y-6">
          {/* scores */}
          <section>
            <h3 className="text-sm font-semibold text-slate-200 mb-2">Agreement: current → proposed</h3>
            <table className="w-full text-xs border border-slate-800 rounded-lg overflow-hidden">
              <thead className="bg-slate-800/50 text-slate-400">
                <tr>
                  <th className="py-1.5 px-2 text-left font-medium">split</th>
                  <th className="py-1.5 px-2 text-right font-medium">n</th>
                  <th className="py-1.5 px-2 text-right font-medium">κ now</th>
                  <th className="py-1.5 px-2 text-right font-medium">κ new</th>
                  <th className="py-1.5 px-2 text-right font-medium">Δκ</th>
                  <th className="py-1.5 px-2 text-right font-medium">% now</th>
                  <th className="py-1.5 px-2 text-right font-medium">% new</th>
                  <th className="py-1.5 px-2 text-right font-medium">Δ%</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {base.train && <ScoreRow label="train" base={base.train} win={win.train} />}
                {base.val && <ScoreRow label="validation" base={base.val} win={win.val} />}
                {base.test && <ScoreRow label="test" base={base.test} win={win.test} highlight />}
              </tbody>
            </table>
            <p className="text-[11px] text-slate-500 mt-1.5">
              The test split was never seen during optimization or selection — it is the honest before/after.
            </p>
          </section>

          {/* confusion + flips */}
          <section className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="flex gap-4">
              {base.test && <Confusion title="Current (test)" score={base.test} />}
              {win.test && <Confusion title="Proposed (test)" score={win.test} />}
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-slate-200">Test changes</h3>
              <FlipList title="Fixed (wrong → right)" items={flips.fixed} tone="good" />
              <FlipList title="Broke (right → wrong)" items={flips.broke} tone="bad" />
            </div>
          </section>

          {/* candidates */}
          <section>
            <h3 className="text-sm font-semibold text-slate-200 mb-2">Candidates (selected on validation κ)</h3>
            <div className="space-y-1">
              {candidates.map((c) => {
                const isWinner = c.id === run.winner_id
                const s = c.val_score
                return (
                  <div
                    key={c.id}
                    className={`text-xs px-2 py-1.5 rounded border ${
                      isWinner ? 'border-indigo-600/50 bg-indigo-950/30' : 'border-slate-800'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-slate-400 w-7">{c.id}</span>
                      {isWinner && <Trophy size={12} className="text-indigo-400" />}
                      {c.error ? (
                        <span className="text-rose-400 truncate">failed: {c.error}</span>
                      ) : (
                        <>
                          <span className="text-slate-300">val κ {fmtK(s?.cohen_kappa)}</span>
                          <span className="text-slate-500">· {fmtP(s?.agreement_pct)}</span>
                          {s?.errors > 0 && <span className="text-amber-400">· {s.errors} err</span>}
                        </>
                      )}
                      <span className="flex-1" />
                      <span className="text-slate-600">temp {c.temperature}</span>
                    </div>
                    {c.summary && (
                      <p className="text-slate-400 mt-1 leading-snug pl-9">{c.summary}</p>
                    )}
                  </div>
                )
              })}
            </div>
            <p className="text-[11px] text-slate-500 mt-1.5">Each row summarizes how that candidate rewrote the rubric.</p>
          </section>

          {/* themes */}
          {run.winner?.themes && (
            <section>
              <h3 className="text-sm font-semibold text-slate-200 mb-1.5">Root-cause analysis (winner)</h3>
              <p className="text-xs text-slate-400 whitespace-pre-wrap leading-relaxed bg-slate-950/40 border border-slate-800 rounded-lg p-3">
                {run.winner.themes}
              </p>
            </section>
          )}

          {/* prompt diff */}
          <section>
            <button
              onClick={() => setShowDiff((s) => !s)}
              className="flex items-center gap-1.5 text-sm font-semibold text-slate-200"
            >
              {showDiff ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
              Prompt changes
            </button>
            {showDiff && (
              <pre className="mt-2 text-[11px] bg-slate-950/60 border border-slate-800 rounded-lg p-3 overflow-auto thin-scroll max-h-[40vh] font-mono leading-relaxed">
                {diff.map((d, i) => (
                  <div
                    key={i}
                    className={
                      d.t === 'add'
                        ? 'bg-emerald-500/10 text-emerald-200'
                        : d.t === 'del'
                          ? 'bg-rose-500/10 text-rose-200'
                          : 'text-slate-400'
                    }
                  >
                    <span className="select-none text-slate-600">{d.t === 'add' ? '+ ' : d.t === 'del' ? '- ' : '  '}</span>
                    {d.v || ' '}
                  </div>
                ))}
              </pre>
            )}
          </section>
        </div>

        {/* footer */}
        <div className="flex items-center gap-3 px-5 py-3 border-t border-slate-800 shrink-0">
          {!decided && (
            <span className="text-[11px] text-slate-500 max-w-sm leading-snug">
              Adopting writes <span className="font-mono text-slate-400">prompt.md</span>, keeps the {run.dataset_size}{' '}
              labeled verdict{run.dataset_size === 1 ? '' : 's'}, and clears this mode&rsquo;s other (now-stale) AI scores.
            </span>
          )}
          {flips.broke?.length > 0 && (
            <span className="flex items-center gap-1.5 text-xs text-amber-300">
              <AlertTriangle size={13} /> introduces {flips.broke.length} regression{flips.broke.length === 1 ? '' : 's'} on test
            </span>
          )}
          {testKDelta !== null && (
            <span className="text-xs text-slate-400">
              test κ {testKDelta >= 0 ? '+' : ''}{testKDelta.toFixed(3)}
            </span>
          )}
          <div className="flex-1" />
          {!decided ? (
            <>
              <button
                onClick={onReject}
                disabled={busy}
                className="text-sm px-3 py-1.5 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
              >
                Reject
              </button>
              <button
                onClick={onAdopt}
                disabled={busy}
                title="Write prompt.md, keep the labeled verdicts, and clear this mode's stale AI scores"
                className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded border border-emerald-600 bg-emerald-600/20 text-emerald-100 hover:bg-emerald-600/30 disabled:opacity-40"
              >
                {busy ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                {busy ? 'Adopting…' : 'Adopt prompt'}
              </button>
            </>
          ) : (
            <button
              onClick={onClose}
              className="text-sm px-3 py-1.5 rounded border border-slate-700 text-slate-300 hover:bg-slate-800"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
