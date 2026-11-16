import { PageHeader } from '@/components/shared/PageHeader'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

import { useSettings } from './api'
import { GeneralSettingsForm, type SettingsSection } from './GeneralSettingsForm'
import { SkillPatternsPanel } from './SkillPatternsPanel'
import { StopWordsPanel } from './StopWordsPanel'

/** Settings (Settings.dc.html): scoring, skills, words to ignore, NUC exclusions, names. */
export function SettingsPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-[18px]">
      <PageHeader
        title="Settings"
        description="How topics are scored and what the system looks for: scoring defaults, the skills it recognises, words to ignore, the NUC courses left out of the comparison and the course-style names given to topics."
      />
      <Tabs defaultValue="scoring" className="gap-[18px]">
        <TabsList>
          <TabsTrigger value="scoring">Scoring</TabsTrigger>
          <TabsTrigger value="skills">Skills list</TabsTrigger>
          <TabsTrigger value="stop-words">Words to ignore</TabsTrigger>
          <TabsTrigger value="exclusions">NUC courses to leave out</TabsTrigger>
          <TabsTrigger value="names">Course-style topic names</TabsTrigger>
        </TabsList>
        <TabsContent value="scoring">
          <GeneralSection section="scoring" />
        </TabsContent>
        <TabsContent value="skills">
          <SkillPatternsPanel />
        </TabsContent>
        <TabsContent value="stop-words">
          <StopWordsPanel />
        </TabsContent>
        <TabsContent value="exclusions">
          <GeneralSection section="exclusions" />
        </TabsContent>
        <TabsContent value="names">
          <GeneralSection section="names" />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function GeneralSection({ section }: { section: SettingsSection }) {
  const settings = useSettings()
  if (settings.isPending) {
    return (
      <div className="space-y-4" aria-label="Loading settings">
        <Skeleton className="h-48 w-full rounded-[20px]" />
        <Skeleton className="h-48 w-full rounded-[20px]" />
      </div>
    )
  }
  if (settings.isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load the settings</AlertTitle>
        <AlertDescription className="space-y-2">
          <p>{settings.error.message}</p>
          <Button variant="outline" size="sm" onClick={() => void settings.refetch()}>
            Try again
          </Button>
        </AlertDescription>
      </Alert>
    )
  }
  return <GeneralSettingsForm settings={settings.data.settings} section={section} />
}
