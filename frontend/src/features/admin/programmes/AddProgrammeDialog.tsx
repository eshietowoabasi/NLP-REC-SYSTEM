import { Loader2, Plus } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useCreateProgramme } from '@/features/programmes/api'
import { DisciplineSelect } from '@/features/programmes/DisciplineSelect'
import type { NucDiscipline, Programme } from '@/types/api'

/** "Add programme" button and form; the new programme is selected once it is created. */
export function AddProgrammeDialog({ onCreated }: { onCreated: (programme: Programme) => void }) {
  const create = useCreateProgramme()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [faculty, setFaculty] = useState('')
  const [discipline, setDiscipline] = useState<NucDiscipline | null>(null)

  const reset = () => {
    setName('')
    setCode('')
    setFaculty('')
    setDiscipline(null)
    create.reset()
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    create.mutate(
      {
        name: name.trim(),
        discipline_code: code.trim() || null,
        faculty: faculty.trim() || null,
        nuc_discipline: discipline,
        country: 'Nigeria',
      },
      {
        onSuccess: (programme) => {
          toast.success(`${programme.name} added. Next, upload its NUC core.`)
          setOpen(false)
          reset()
          onCreated(programme)
        },
      },
    )
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (!next) reset()
      }}
    >
      <DialogTrigger asChild>
        <Button>
          <Plus aria-hidden="true" /> Add programme
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add programme</DialogTitle>
          <DialogDescription>
            Any NUC CCMAS programme. You can upload its NUC core, set up job collection and add its
            planners next.
          </DialogDescription>
        </DialogHeader>
        <form id="add-programme" className="grid gap-3.5" onSubmit={submit}>
          <div className="grid gap-1.5">
            <Label htmlFor="new-programme-name">Programme name</Label>
            <Input
              id="new-programme-name"
              placeholder="e.g. Nursing Science"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
            />
          </div>
          <div className="grid gap-3.5 sm:grid-cols-[140px_1fr]">
            <div className="grid gap-1.5">
              <Label htmlFor="new-programme-code">Code</Label>
              <Input
                id="new-programme-code"
                placeholder="NSC"
                value={code}
                onChange={(event) => setCode(event.target.value)}
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="new-programme-faculty">Faculty (optional)</Label>
              <Input
                id="new-programme-faculty"
                placeholder="e.g. Faculty of Basic Clinical Sciences"
                value={faculty}
                onChange={(event) => setFaculty(event.target.value)}
              />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="new-programme-discipline">NUC discipline</Label>
            <DisciplineSelect
              id="new-programme-discipline"
              className="w-full"
              value={discipline}
              onChange={setDiscipline}
              noneLabel="Choose later (general skills only)"
            />
            <p className="text-xs text-body-soft">
              Picks the skills list used to measure employer demand.
            </p>
          </div>
          {create.isError && (
            <p role="alert" className="text-sm text-destructive">
              {create.error.message}
            </p>
          )}
        </form>
        <DialogFooter>
          <Button variant="outline" type="button" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button type="submit" form="add-programme" disabled={create.isPending || !name.trim()}>
            {create.isPending && <Loader2 className="animate-spin" aria-hidden="true" />}
            Add programme
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
