// Polished, white-themed PDF for one agreement report (mode + variant).
// Rendered with @react-pdf/renderer (vector text + real pagination). Built on
// demand and lazy-loaded by ReportView so the lib stays out of the main bundle.
import { Document, Page, View, Text, Image, StyleSheet } from '@react-pdf/renderer'

const GRADES = ['pass', 'borderline', 'fail', 'na']
const GRADE_LABEL = { pass: 'Pass', borderline: 'Borderline', fail: 'Fail', na: 'N/A' }
const GRADE_COLOR = { pass: '#10b981', borderline: '#f59e0b', fail: '#f43f5e', na: '#64748b' }
const GRADE_SOFT = { pass: '#ecfdf5', borderline: '#fffbeb', fail: '#fff1f2', na: '#f1f5f9' }
const GRADE_INK = { pass: '#047857', borderline: '#b45309', fail: '#be123c', na: '#334155' }

const C = {
  ink: '#0f172a',
  sub: '#475569',
  muted: '#94a3b8',
  line: '#e2e8f0',
  card: '#f8fafc',
  accent: '#4f46e5',
  white: '#ffffff',
}

// Resolve a same-origin /images/... path to an absolute URL so @react-pdf can
// fetch it (works on the Vite dev server proxy and the prod :8000 host alike).
function abs(src) {
  if (!src) return null
  try {
    return new URL(src, window.location.origin).href
  } catch {
    return src
  }
}

// Guard against a pathologically long note overflowing a non-splitting card.
function clip(s, max = 800) {
  if (!s) return ''
  return s.length > max ? `${s.slice(0, max).trimEnd()}…` : s
}

const styles = StyleSheet.create({
  // cover
  cover: { paddingTop: 92, paddingHorizontal: 48, paddingBottom: 48, fontFamily: 'Helvetica', color: C.ink },
  coverBand: { position: 'absolute', top: 0, left: 0, right: 0, height: 10, backgroundColor: C.accent },
  kicker: { fontSize: 11, letterSpacing: 2, color: C.accent, fontWeight: 'bold', marginBottom: 8 },
  coverTitle: { fontSize: 26, fontWeight: 'bold', color: C.ink, marginBottom: 12 },
  metaRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 3 },
  metaText: { fontSize: 11, color: C.sub },
  metaDivider: { fontSize: 11, color: C.muted, marginHorizontal: 6 },
  metaSub: { fontSize: 10, color: C.muted, marginBottom: 28 },
  coverCard: { flexDirection: 'row', borderWidth: 1, borderColor: C.line, borderRadius: 8, backgroundColor: C.card, padding: 20 },
  coverStat: { width: '42%', borderRightWidth: 1, borderRightColor: C.line, paddingRight: 16, justifyContent: 'center' },
  bigPct: { fontSize: 40, fontWeight: 'bold', color: C.ink },
  bigPctLabel: { fontSize: 10, color: C.sub, marginTop: 2 },
  coverStatsRight: { flex: 1, paddingLeft: 16, justifyContent: 'center' },
  kv: { fontSize: 11, color: C.sub, marginBottom: 4 },
  kvNum: { color: C.ink, fontWeight: 'bold' },
  kvMuted: { fontSize: 9, color: C.muted, marginTop: 2 },
  footer: { position: 'absolute', bottom: 28, left: 48, fontSize: 9, color: C.muted },

  // content pages
  page: { paddingVertical: 40, paddingHorizontal: 48, fontFamily: 'Helvetica', color: C.ink },
  h2: { fontSize: 14, fontWeight: 'bold', color: C.ink, marginBottom: 6, marginTop: 6 },
  caption: { fontSize: 9, color: C.muted, marginBottom: 8 },
  card: { borderWidth: 1, borderColor: C.line, borderRadius: 8, padding: 14, marginBottom: 16 },

  // distributions
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  distLabel: { fontSize: 11, fontWeight: 'bold', color: C.ink },
  distMeta: { fontSize: 9, color: C.muted },
  barTrack: { flexDirection: 'row', height: 12, borderRadius: 6, backgroundColor: '#eef2f7', marginTop: 4, marginBottom: 6, overflow: 'hidden' },
  legend: { flexDirection: 'row', flexWrap: 'wrap' },
  legendItem: { flexDirection: 'row', alignItems: 'center', marginRight: 14, marginBottom: 2 },
  dot: { width: 6, height: 6, borderRadius: 3, marginRight: 4 },
  legendText: { fontSize: 9, color: C.sub },

  // confusion matrix
  confRow: { flexDirection: 'row', alignItems: 'center' },
  confCorner: { width: 70, height: 22 },
  confColHead: { width: 52, fontSize: 9, color: C.sub, textAlign: 'center', fontWeight: 'bold' },
  confRowHead: { width: 70, fontSize: 9, color: C.sub, textAlign: 'right', paddingRight: 8, fontWeight: 'bold' },
  confCell: { width: 48, height: 38, margin: 2, borderWidth: 1, borderRadius: 4, alignItems: 'center', justifyContent: 'center' },
  confCellText: { fontSize: 12, fontWeight: 'bold' },

  // chips
  chipRow: { flexDirection: 'row', alignItems: 'center' },
  chipLabel: { fontSize: 8, color: C.muted },
  chip: { borderRadius: 3, paddingHorizontal: 5, paddingVertical: 2, marginLeft: 4 },
  chipText: { fontSize: 8, fontWeight: 'bold' },

  // disagreement cards
  disCard: { borderWidth: 1, borderColor: C.line, borderRadius: 8, padding: 12, marginBottom: 12, backgroundColor: C.white },
  disTitle: { fontSize: 11, fontWeight: 'bold', color: C.ink },
  imgRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 },
  imgBox: { width: '49%', borderWidth: 1, borderColor: C.line, borderRadius: 6, backgroundColor: C.card, padding: 6 },
  imgCap: { fontSize: 7, color: C.muted, marginBottom: 4, fontWeight: 'bold', letterSpacing: 0.5 },
  img: { width: '100%', height: 150, objectFit: 'contain' },
  noImg: { fontSize: 9, color: C.muted, height: 150, textAlign: 'center', paddingTop: 64 },
  noteRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 },
  noteCol: { width: '49%' },
  noteHead: { fontSize: 8, color: C.muted, fontWeight: 'bold', marginBottom: 2 },
  noteText: { fontSize: 9, color: C.sub, lineHeight: 1.4 },

  pageNum: { position: 'absolute', bottom: 24, right: 48, fontSize: 8, color: C.muted },
})

function Chip({ grade }) {
  return (
    <View style={[styles.chip, { backgroundColor: GRADE_SOFT[grade] || '#f1f5f9' }]}>
      <Text style={[styles.chipText, { color: GRADE_INK[grade] || C.sub }]}>{GRADE_LABEL[grade] || grade}</Text>
    </View>
  )
}

function DistRow({ label, dist, total }) {
  return (
    <View style={{ marginBottom: 10 }}>
      <View style={styles.rowBetween}>
        <Text style={styles.distLabel}>{label}</Text>
        <Text style={styles.distMeta}>{total} graded</Text>
      </View>
      <View style={styles.barTrack}>
        {GRADES.map((g) =>
          dist[g] > 0 ? <View key={g} style={{ width: `${(100 * dist[g]) / total}%`, backgroundColor: GRADE_COLOR[g] }} /> : null,
        )}
      </View>
      <View style={styles.legend}>
        {GRADES.map((g) => (
          <View key={g} style={styles.legendItem}>
            <View style={[styles.dot, { backgroundColor: GRADE_COLOR[g] }]} />
            <Text style={styles.legendText}>
              {GRADE_LABEL[g]} {dist[g]}
              {total > 0 ? ` (${Math.round((100 * dist[g]) / total)}%)` : ''}
            </Text>
          </View>
        ))}
      </View>
    </View>
  )
}

function Confusion({ confusion }) {
  return (
    <View>
      <View style={styles.confRow}>
        <View style={styles.confCorner} />
        {GRADES.map((a) => (
          <Text key={a} style={styles.confColHead}>{GRADE_LABEL[a]}</Text>
        ))}
      </View>
      {GRADES.map((h) => (
        <View key={h} style={styles.confRow}>
          <Text style={styles.confRowHead}>{GRADE_LABEL[h]}</Text>
          {GRADES.map((a) => {
            const cnt = confusion[h][a]
            const diag = h === a
            const bg = diag ? '#ecfdf5' : cnt > 0 ? '#fff1f2' : '#f8fafc'
            const fg = diag ? '#047857' : cnt > 0 ? '#be123c' : '#94a3b8'
            const bc = diag ? '#a7f3d0' : cnt > 0 ? '#fecdd3' : '#e2e8f0'
            return (
              <View key={a} style={[styles.confCell, { backgroundColor: bg, borderColor: bc }]}>
                <Text style={[styles.confCellText, { color: fg }]}>{cnt}</Text>
              </View>
            )
          })}
        </View>
      ))}
    </View>
  )
}

function DisagreementCard({ d, variantLabel }) {
  const input = abs(d.input_image)
  const output = abs(d.output_image)
  return (
    <View style={styles.disCard} wrap={false}>
      <View style={styles.rowBetween}>
        <Text style={styles.disTitle}>{d.title} · pair {d.pair_index}</Text>
        <View style={styles.chipRow}>
          <Text style={styles.chipLabel}>Human</Text>
          <Chip grade={d.human_grade} />
          <Text style={[styles.chipLabel, { marginLeft: 8 }]}>AI</Text>
          <Chip grade={d.ai_verdict} />
        </View>
      </View>
      <View style={styles.imgRow}>
        <View style={styles.imgBox}>
          <Text style={styles.imgCap}>INPUT</Text>
          {input ? <Image src={input} style={styles.img} /> : <Text style={styles.noImg}>no image</Text>}
        </View>
        <View style={styles.imgBox}>
          <Text style={styles.imgCap}>OUTPUT · {variantLabel}</Text>
          {output ? <Image src={output} style={styles.img} /> : <Text style={styles.noImg}>no image</Text>}
        </View>
      </View>
      <View style={styles.noteRow}>
        <View style={styles.noteCol}>
          <Text style={styles.noteHead}>Human note</Text>
          <Text style={styles.noteText}>{clip(d.human_note) || '—'}</Text>
        </View>
        <View style={styles.noteCol}>
          <Text style={styles.noteHead}>AI reasoning</Text>
          <Text style={styles.noteText}>{clip(d.ai_reason) || '—'}</Text>
        </View>
      </View>
    </View>
  )
}

export default function ReportPdf({ report, maxPairs = 10 }) {
  const m = report.mode
  const n = report.counts.both
  const excluded = report.counts.human_only + report.counts.ai_only + report.counts.no_data
  const allDis = report.disagreements || []
  const totalDis = report.disagreements_count ?? allDis.length
  const shown = allDis.slice(0, maxPairs)
  const generated = new Date().toLocaleString()

  return (
    <Document title={`agreement-report_mode-${m.id}_${report.variant}`} author="Import Slide-Pair Grader">
      {/* Cover */}
      <Page size="A4" style={styles.cover}>
        <View style={styles.coverBand} />
        <Text style={styles.kicker}>AGREEMENT REPORT</Text>
        <Text style={styles.coverTitle}>#{m.id} {m.name}</Text>
        <View style={styles.metaRow}>
          <Text style={styles.metaText}>Grader: {m.grader || '—'}</Text>
          <Text style={styles.metaDivider}>·</Text>
          <Text style={styles.metaText}>Variant: {report.variant_label}</Text>
        </View>
        <Text style={styles.metaSub}>Generated {generated}</Text>

        <View style={styles.coverCard}>
          <View style={styles.coverStat}>
            <Text style={styles.bigPct}>{report.agreement_pct != null ? `${report.agreement_pct}%` : '—'}</Text>
            <Text style={styles.bigPctLabel}>human–agent agreement</Text>
          </View>
          <View style={styles.coverStatsRight}>
            <Text style={styles.kv}>
              <Text style={styles.kvNum}>{n}</Text> pairs compared
            </Text>
            <Text style={styles.kv}>
              <Text style={[styles.kvNum, { color: GRADE_INK.pass }]}>{report.agreements}</Text> agree ·{' '}
              <Text style={[styles.kvNum, { color: GRADE_INK.fail }]}>{report.disagreements_count}</Text> disagree
            </Text>
            <Text style={styles.kv}>
              Cohen's kappa <Text style={styles.kvNum}>{report.cohen_kappa ?? '—'}</Text>
            </Text>
            {excluded > 0 && (
              <Text style={styles.kvMuted}>
                {excluded} excluded (agent-only {report.counts.ai_only}, human-only {report.counts.human_only}, neither {report.counts.no_data})
              </Text>
            )}
          </View>
        </View>
        <Text style={styles.footer}>Import Slide-Pair Failure-Mode Grader</Text>
      </Page>

      {/* Stats */}
      <Page size="A4" style={styles.page}>
        <Text style={styles.h2}>Score distribution</Text>
        <View style={styles.card}>
          <DistRow label="Human" dist={report.human_distribution} total={n} />
          <DistRow label="Agent" dist={report.ai_distribution} total={n} />
        </View>

        <Text style={styles.h2}>Confusion matrix</Text>
        <Text style={styles.caption}>Rows = human, columns = agent; diagonal = agreement.</Text>
        <View style={styles.card}>
          <Confusion confusion={report.confusion} />
        </View>

        <Text style={styles.pageNum} fixed render={({ pageNumber, totalPages }) => `${pageNumber} / ${totalPages}`} />
      </Page>

      {/* Disagreements */}
      <Page size="A4" style={styles.page}>
        <Text style={styles.h2}>
          Disagreements {shown.length > 0 ? `(showing ${shown.length} of ${totalDis})` : ''}
        </Text>
        {shown.length === 0 ? (
          <Text style={styles.caption}>Human and agent agree on all {n} compared pairs.</Text>
        ) : (
          shown.map((d) => <DisagreementCard key={`${d.slug}:${d.pair_index}`} d={d} variantLabel={report.variant_label} />)
        )}
        <Text style={styles.pageNum} fixed render={({ pageNumber, totalPages }) => `${pageNumber} / ${totalPages}`} />
      </Page>
    </Document>
  )
}
