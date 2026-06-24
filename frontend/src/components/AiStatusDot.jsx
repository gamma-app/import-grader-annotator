// Small health indicator for the AI grader: green when the Anthropic key is
// configured and the graders dir is found, red when something is wrong, grey
// while the status is still loading. Hover for the specifics.
export default function AiStatusDot({ status }) {
  const ok = status?.llm_configured && status?.graders_dir_ok
  const color = ok ? 'bg-emerald-500' : status ? 'bg-rose-500' : 'bg-slate-500'
  const title = !status
    ? 'Checking AI grader…'
    : ok
      ? `AI grader ready · ${status.graders_present}/${status.graders_expected} graders${status.model ? ` · ${status.model}` : ''}`
      : status.llm_configured
        ? `Graders dir not found: ${status.graders_dir || '(vendored backend/graders/)'}`
        : 'ANTHROPIC_API_KEY not set in .env — copy it from gamma\u2019s .envrc'
  return <span className={`w-2 h-2 rounded-full shrink-0 ${color}`} title={title} />
}
