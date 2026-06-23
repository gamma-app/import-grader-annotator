// Small health indicator for the AI grader: green when the eval-server is
// reachable and the graders dir is found, red when something is wrong, grey
// while the status is still loading. Hover for the specifics.
export default function AiStatusDot({ status }) {
  const ok = status?.eval_server_reachable && status?.graders_dir_ok
  const color = ok ? 'bg-emerald-500' : status ? 'bg-rose-500' : 'bg-slate-500'
  const title = !status
    ? 'Checking AI grader…'
    : ok
      ? `AI grader ready · ${status.graders_present}/${status.graders_expected} graders · ${status.eval_server_url}`
      : status.eval_server_reachable
        ? `Graders dir not found: ${status.graders_dir || '(set IMPORT_EVALS_GRADERS_DIR in .env)'}`
        : `eval-server unreachable at ${status.eval_server_url} — run \`yarn dev:eval-server\``
  return <span className={`w-2 h-2 rounded-full shrink-0 ${color}`} title={title} />
}
