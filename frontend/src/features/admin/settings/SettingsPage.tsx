import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

import { useSettings } from './api'
import { GeneralSettingsForm } from './GeneralSettingsForm'
import { SkillPatternsPanel } from './SkillPatternsPanel'
import { StopWordsPanel } from './StopWordsPanel'

export function SettingsPage() {
  const settings = useSettings()

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">Settings</h2>
        <p className="text-sm text-muted-foreground">
          System defaults, the skill patterns used to recognise skills, and domain stop words.
        </p>
      </div>
      <Tabs defaultValue="general" className="gap-4">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="skills">Skill patterns</TabsTrigger>
          <TabsTrigger value="stop-words">Stop words</TabsTrigger>
        </TabsList>
        <TabsContent value="general">
          {settings.isPending ? (
            <div className="space-y-4" aria-label="Loading settings">
              <Skeleton className="h-48 w-full" />
              <Skeleton className="h-48 w-full" />
            </div>
          ) : settings.isError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not load the settings</AlertTitle>
              <AlertDescription className="space-y-2">
                <p>{settings.error.message}</p>
                <Button variant="outline" size="sm" onClick={() => void settings.refetch()}>
                  Try again
                </Button>
              </AlertDescription>
            </Alert>
          ) : (
            <GeneralSettingsForm settings={settings.data.settings} />
          )}
        </TabsContent>
        <TabsContent value="skills">
          <SkillPatternsPanel />
        </TabsContent>
        <TabsContent value="stop-words">
          <StopWordsPanel />
        </TabsContent>
      </Tabs>
    </div>
  )
}
