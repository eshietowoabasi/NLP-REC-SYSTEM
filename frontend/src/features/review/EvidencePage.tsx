import { AlertTriangle, SearchX } from 'lucide-react'
import { useState } from 'react'
import { useParams } from 'react-router'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CATEGORY_LABELS, UPLOAD_CATEGORIES } from '@/features/documents/labels'
import { formatNumber } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { SkillLabel, UploadCategory } from '@/types/api'

import { useSessionResult } from './api'
import {
  CompletedSessionGate,
  EmptyPanel,
  ErrorPanel,
  LoadingBlock,
  OverlapBadge,
  ScoreLevelText,
  ScoreMeter,
  SessionReviewHeader,
} from './components'
import { formatPercent, SKILL_LABELS, toPoints } from './labels'
import { RankedBarChart } from './RankedBarChart'

const CHART_ROWS = 15
const TABLE_ROWS = 40

const TABS = [
  { value: 'keywords', label: 'Keywords' },
  { value: 'skills', label: 'Skills' },
  { value: 'themes', label: 'Topics' },
  { value: 'overlap', label: 'NUC core' },
] as const

export function EvidencePage() {
  const sessionId = Number(useParams().sessionId)
  return (
    <CompletedSessionGate sessionId={sessionId} title="Evidence">
      {(session) => (
        <div className="mx-auto max-w-6xl space-y-6">
          <SessionReviewHeader
            sessionId={session.id}
            sessionName={session.session_name}
            title="Evidence"
          />
          <p className="text-sm text-muted-foreground">
            What the analysis found in the {session.document_count} selected document
            {session.document_count === 1 ? '' : 's'}: the words that stand out, the skills
            employers ask for, the topics found, and how each topic compares with the NUC core.
          </p>
          <Tabs defaultValue="keywords" className="gap-4">
            <TabsList>
              {TABS.map((tab) => (
                <TabsTrigger key={tab.value} value={tab.value}>
                  {tab.label}
                </TabsTrigger>
              ))}
            </TabsList>
            <TabsContent value="keywords">
              <KeywordsTab sessionId={session.id} />
            </TabsContent>
            <TabsContent value="skills">
              <SkillsTab sessionId={session.id} />
            </TabsContent>
            <TabsContent value="themes">
              <ThemesTab sessionId={session.id} />
            </TabsContent>
            <TabsContent value="overlap">
              <OverlapTab sessionId={session.id} />
            </TabsContent>
          </Tabs>
        </div>
      )}
    </CompletedSessionGate>
  )
}

/* ------------------------------------------------------------------ keywords */

function KeywordsTab({ sessionId }: { sessionId: number }) {
  const result = useSessionResult(sessionId, 'keywords')
  const [category, setCategory] = useState<'all' | UploadCategory>('all')

  if (result.isPending) return <LoadingBlock label="Loading keywords" />
  if (result.isError) {
    return (
      <ErrorPanel
        title="Could not load keywords"
        error={result.error}
        onRetry={() => void result.refetch()}
      />
    )
  }
  const terms = category === 'all' ? result.data.overall : (result.data.by_category[category] ?? [])
  const available = UPLOAD_CATEGORIES.filter((c) => result.data.by_category[c]?.length)

  return (
    <div className="space-y-4">
      <div className="grid gap-1.5">
        <Label htmlFor="keyword-category">Document category</Label>
        <Select value={category} onValueChange={(value) => setCategory(value as typeof category)}>
          <SelectTrigger id="keyword-category" className="w-52">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {available.map((value) => (
              <SelectItem key={value} value={value}>
                {CATEGORY_LABELS[value]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {terms.length === 0 ? (
        <EmptyPanel icon={SearchX} title="No keywords">
          No terms were extracted for this category.
        </EmptyPanel>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
          <Card>
            <CardHeader>
              <CardTitle>Top {Math.min(CHART_ROWS, terms.length)} words that stand out</CardTitle>
              <CardDescription>
                Words that are common in some extracts but not everywhere, across{' '}
                {formatNumber(result.data.passage_count)} extracts. Everyday words are left out.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <RankedBarChart
                label="Words that stand out"
                data={terms.slice(0, CHART_ROWS).map((t) => ({
                  label: t.term,
                  value: t.score,
                  detail: `in ${t.passage_count} passages`,
                }))}
              />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Keyword table</CardTitle>
            </CardHeader>
            <CardContent className="max-h-[32rem] overflow-y-auto">
              <Table aria-label="Keywords">
                <TableHeader>
                  <TableRow>
                    <TableHead>Term</TableHead>
                    <TableHead className="text-right">Weight</TableHead>
                    <TableHead className="text-right">Extracts</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {terms.slice(0, TABLE_ROWS).map((t) => (
                    <TableRow key={t.term}>
                      <TableCell className="font-medium">{t.term}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {t.score.toFixed(3)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{t.passage_count}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

/* -------------------------------------------------------------------- skills */

const SKILL_TYPES: readonly SkillLabel[] = ['SKILL', 'TOOL', 'LANGUAGE', 'CERT']

function SkillsTab({ sessionId }: { sessionId: number }) {
  const result = useSessionResult(sessionId, 'entities')
  const [type, setType] = useState<'all' | SkillLabel>('all')

  if (result.isPending) return <LoadingBlock label="Loading skills" />
  if (result.isError) {
    return (
      <ErrorPanel
        title="Could not load skills"
        error={result.error}
        onRetry={() => void result.refetch()}
      />
    )
  }
  const data = result.data
  const skills = data.skills.filter((s) => type === 'all' || s.label === type)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="grid gap-1.5">
          <Label htmlFor="skill-type">Type</Label>
          <Select value={type} onValueChange={(value) => setType(value as typeof type)}>
            <SelectTrigger id="skill-type" className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              {SKILL_TYPES.map((value) => (
                <SelectItem key={value} value={value}>
                  {SKILL_LABELS[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <p className="text-sm text-muted-foreground">
          {formatNumber(data.passages_with_skills)} of {formatNumber(data.passage_count)} passages
          mention at least one recognised skill.
        </p>
      </div>
      {skills.length === 0 ? (
        <EmptyPanel icon={SearchX} title="No skills recognised">
          No skill patterns matched these documents. Administrators can add patterns under Settings.
        </EmptyPanel>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
          <Card>
            <CardHeader>
              <CardTitle>Most widely mentioned</CardTitle>
              <CardDescription>
                Number of documents (of {data.document_count}) that mention each skill.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <RankedBarChart
                label="Skills by number of documents mentioning them"
                format={(value) => String(Math.round(value))}
                data={skills.slice(0, CHART_ROWS).map((s) => ({
                  label: s.name,
                  value: s.document_frequency,
                  detail: `${SKILL_LABELS[s.label]} · ${s.mentions} mentions`,
                }))}
              />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Skill table</CardTitle>
            </CardHeader>
            <CardContent className="max-h-[32rem] overflow-y-auto">
              <Table aria-label="Skills">
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead className="text-right">Documents</TableHead>
                    <TableHead className="text-right">Mentions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {skills.slice(0, TABLE_ROWS).map((s) => (
                    <TableRow key={s.name}>
                      <TableCell className="font-medium">{s.name}</TableCell>
                      <TableCell>{SKILL_LABELS[s.label]}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {s.document_frequency}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{s.mentions}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

/* -------------------------------------------------------------------- themes */

function ThemesTab({ sessionId }: { sessionId: number }) {
  const result = useSessionResult(sessionId, 'topics')

  if (result.isPending) return <LoadingBlock label="Loading topics" />
  if (result.isError) {
    return (
      <ErrorPanel
        title="Could not load the topics"
        error={result.error}
        onRetry={() => void result.refetch()}
      />
    )
  }
  const data = result.data
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {data.topic_count} topic{data.topic_count === 1 ? '' : 's'} found in{' '}
        {formatNumber(data.modelled_passages)} extracts. {formatNumber(data.outlier_passages)}{' '}
        extracts did not fit any topic and were left out.
      </p>
      {data.topics.length === 0 ? (
        <EmptyPanel icon={SearchX} title="No topics found" />
      ) : (
        <ul className="grid gap-4 md:grid-cols-2" aria-label="Topics">
          {data.topics.map((topic) => (
            <li key={topic.topic_id}>
              <Card className="h-full">
                <CardHeader>
                  <CardTitle>{topic.title}</CardTitle>
                  <CardDescription>
                    {topic.size} extracts from {topic.document_count} document
                    {topic.document_count === 1 ? '' : 's'}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex flex-wrap gap-1">
                    {topic.keywords.slice(0, 10).map((k) => (
                      <Badge key={k.term} variant="secondary">
                        {k.term}
                      </Badge>
                    ))}
                  </div>
                  <ScoreMeter label="Comes up" value={topic.strength} />
                  <details className="text-sm">
                    <summary className="cursor-pointer font-medium">
                      Example extracts ({topic.samples.length})
                    </summary>
                    <ul className="mt-2 space-y-2">
                      {topic.samples.map((sample) => (
                        <li key={sample.passage_id} className="rounded-md bg-muted/60 p-2">
                          <p className="text-xs font-medium text-muted-foreground">
                            {sample.document_label ?? sample.document_title}
                          </p>
                          <p>{sample.text}</p>
                        </li>
                      ))}
                    </ul>
                  </details>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------- overlap */

function OverlapTab({ sessionId }: { sessionId: number }) {
  const result = useSessionResult(sessionId, 'similarity')

  if (result.isPending) return <LoadingBlock label="Loading overlap" />
  if (result.isError) {
    return (
      <ErrorPanel
        title="Could not load the overlap analysis"
        error={result.error}
        onRetry={() => void result.refetch()}
      />
    )
  }
  const { threshold, candidates, nuc_core_version } = result.data
  const byCourse = result.data.basis === 'course'
  const duplicates = candidates.filter((c) => c.overlap_status === 'Potential Duplicate').length

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Similarity to the NUC core</CardTitle>
          <CardDescription>
            How similar each topic is, by meaning, to the closest {byCourse ? 'course' : 'extract'}{' '}
            of {nuc_core_version?.version_label ?? 'the NUC core'}. Above {formatPercent(threshold)}{' '}
            a topic is marked “May already be in NUC core” as it may duplicate existing core content
            ({duplicates} of {candidates.length}).
            {result.data.courses_compared != null && (
              <>
                {' '}
                {result.data.courses_compared} courses were compared;{' '}
                {result.data.courses_excluded ?? 0} general-studies, SIWES and project courses were
                excluded from comparison.
              </>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <ul className="flex flex-wrap gap-4 text-xs text-muted-foreground" aria-label="Legend">
            <li className="flex items-center gap-1.5">
              <span className="size-2.5 rounded-sm bg-viz-series" aria-hidden="true" />
              At or below the threshold (not in NUC core)
            </li>
            <li className="flex items-center gap-1.5">
              <span className="size-2.5 rounded-sm bg-viz-warning" aria-hidden="true" />
              <AlertTriangle className="size-3.5" aria-hidden="true" />
              Above the threshold (may already be in NUC core)
            </li>
          </ul>
          <RankedBarChart
            label="How similar each topic is to the NUC core"
            domain={[0, 1]}
            format={formatPercent}
            threshold={{ value: threshold, label: `threshold ${formatPercent(threshold)}` }}
            data={candidates.map((c) => ({
              label: c.title,
              value: c.max_similarity,
              detail: c.overlap_status,
              flagged: c.overlap_status === 'Potential Duplicate',
            }))}
          />
        </CardContent>
      </Card>

      <div className="overflow-x-auto rounded-lg border">
        <Table aria-label="Overlap with the NUC core">
          <TableHeader>
            <TableRow>
              <TableHead>Topic</TableHead>
              <TableHead className="text-right">Similarity</TableHead>
              <TableHead className="text-right">How new</TableHead>
              <TableHead>Status</TableHead>
              {byCourse && <TableHead className="min-w-48">Closest NUC course</TableHead>}
              <TableHead className="min-w-80">Closest NUC core extract</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {candidates.map((c) => {
              const duplicate = c.overlap_status === 'Potential Duplicate'
              return (
                <TableRow
                  key={c.topic_id}
                  className={cn(duplicate && 'bg-amber-50/70 dark:bg-amber-950/40')}
                >
                  <TableCell className="font-medium">{c.title}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatPercent(c.max_similarity)}
                  </TableCell>
                  <TableCell className="text-right whitespace-nowrap tabular-nums">
                    {toPoints(c.novelty)} <ScoreLevelText value={c.novelty} />
                  </TableCell>
                  <TableCell>
                    <OverlapBadge status={c.overlap_status} />
                  </TableCell>
                  {byCourse && (
                    <TableCell className="text-sm whitespace-normal">
                      {c.closest_nuc_course ? (
                        <>
                          <span className="font-medium">{c.closest_nuc_course.code}</span> –{' '}
                          {c.closest_nuc_course.title}
                        </>
                      ) : (
                        '—'
                      )}
                    </TableCell>
                  )}
                  <TableCell className="text-sm whitespace-normal text-muted-foreground">
                    {c.closest_nuc_passage.page_number != null && (
                      <span className="font-medium text-foreground">
                        p. {c.closest_nuc_passage.page_number}:{' '}
                      </span>
                    )}
                    {c.closest_nuc_passage.text}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
