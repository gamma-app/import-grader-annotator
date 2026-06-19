// Shared UI metadata for grades and severities.

export const GRADE_ORDER = ['pass', 'borderline', 'fail']

export const GRADE_META = {
  pass: {
    label: 'Pass',
    active: 'bg-emerald-500 text-white border-emerald-500',
    idle: 'border-slate-600 text-emerald-300 hover:bg-emerald-500/10',
  },
  borderline: {
    label: 'Borderline',
    active: 'bg-amber-500 text-slate-900 border-amber-500',
    idle: 'border-slate-600 text-amber-300 hover:bg-amber-500/10',
  },
  fail: {
    label: 'Fail',
    active: 'bg-rose-500 text-white border-rose-500',
    idle: 'border-slate-600 text-rose-300 hover:bg-rose-500/10',
  },
}

export const GRADE_DOT = {
  pass: 'bg-emerald-500',
  borderline: 'bg-amber-500',
  fail: 'bg-rose-500',
  ungraded: 'bg-slate-600',
}

export const SEVERITY_META = {
  P0: 'bg-rose-500/20 text-rose-300 border border-rose-500/40',
  P1: 'bg-amber-500/20 text-amber-300 border border-amber-500/40',
  P2: 'bg-slate-500/20 text-slate-300 border border-slate-500/40',
}
