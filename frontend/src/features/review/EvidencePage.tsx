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
  ScoreMeter,
  SessionReviewHeader,
} from './components'
import { formatScore, SKILL_LABELS } from './labels'
import { RankedBarChart } from './RankedBarChart'

const CHART_ROWS = 15
const TABLE_ROWS = 40

const TABS = [
  { value: 'keywords', label: 'Keywords' },
  { value: 'skills', label: 'Skills' },
  { value: 'themes', label: 'Themes' },
  { value: 'overlap', label: 'NUC overlap' },
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
            {session.document_count === 1 ? '' : 's'}: frequent terms, the skills employers and
            policy mention, the themes discovered and how each theme compares with the NUC core.
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
              <CardTitle>Top {Math.min(CHART_ROWS, terms.length)} terms by TF-IDF</CardTitle>
              <CardDescription>
                Mean TF-IDF weight across {formatNumber(result.data.passage_count)} passages
                (normalised text: lower case, lemmas, stop words removed).
              </CardDescription>
            </CardHeader>
            <CardContent>
              <RankedBarChart
                label="Top terms by TF-IDF score"
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
                    <TableHead className="text-right">TF-IDF</TableHead>
                    <TableHead className="text-right">Passages</TableHead>
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

  if (result.isPending) return <LoadingBlock label="Loading themes" />
  if (result.isError) {
    return (
      <ErrorPanel
        title="Could not load themes"
        error={result.error}
        onRetry={() => void result.refetch()}
      />
    )
  }
  const data = result.data
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {data.topic_count} theme{data.topic_count === 1 ? '' : 's'} discovered in{' '}
        {formatNumber(data.modelled_passages)} passages. {formatNumber(data.outlier_passages)}{' '}
        passages did not fit any theme and were left out.
      </p>
      {data.topics.length === 0 ? (
        <EmptyPanel icon={SearchX} title="No themes" />
      ) : (
        <ul className="grid gap-4 md:grid-cols-2" aria-label="Themes">
          {data.topics.map((topic) => (
            <li key={topic.topic_id}>
              <Card className="h-full">
                <CardHeader>
                  <CardTitle>{topic.title}</CardTitle>
                  <CardDescription>
                    {topic.size} passages from {topic.document_count} document
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
                  <ScoreMeter label="Theme strength" value={topic.strength} />
                  <details className="text-sm">
                    <summary className="cursor-pointer font-medium">
                      Sample passages ({topic.samples.length})
                    </summary>
                    <ul className="mt-2 space-y-2">
                      {topic.samples.map((sample) => (
                        <li key={sample.passage_id} className="rounded-md bg-muted/60 p-2">
                          <p className="text-xs font-medium text-muted-foreground">
                            {sample.document_title}
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
  const duplicates = candidates.filter((c) => c.overlap_status === 'Potential Duplicate').length

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Similarity to the NUC core</CardTitle>
          <CardDescription>
            Highest cosine similarity between each theme and any passage of{' '}
            {nuc_core_version?.version_label ?? 'the NUC core'}. Above {formatScore(threshold)} a
            theme is marked as a potential duplicate of existing core content ({duplicates} of{' '}
            {candidates.length}).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <ul className="flex flex-wrap gap-4 text-xs text-muted-foreground" aria-label="Legend">
            <li className="flex items-center gap-1.5">
              <span className="size-2.5 rounded-sm bg-viz-series" aria-hidden="true" />
              At or below the threshold (new)
            </li>
            <li className="flex items-center gap-1.5">
              <span className="size-2.5 rounded-sm bg-viz-warning" aria-hidden="true" />
              <AlertTriangle className="size-3.5" aria-hidden="true" />
              Above the threshold (potential duplicate)
            </li>
          </ul>
          <RankedBarChart
            label="Maximum similarity of each theme to the NUC core"
            domain={[0, 1]}
            format={formatScore}
            threshold={{ value: threshold, label: `threshold ${formatScore(threshold)}` }}
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
              <TableHead>Theme</TableHead>
              <TableHead className="text-right">Max similarity</TableHead>
              <TableHead className="text-right">Novelty</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="min-w-80">Closest NUC core passage</TableHead>
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
                    {formatScore(c.max_similarity)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatScore(c.novelty)}
                  </TableCell>
                  <TableCell>
                    <OverlapBadge status={c.overlap_status} />
                  </TableCell>
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
