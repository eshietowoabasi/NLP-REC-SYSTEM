'use client'

import * as React from 'react'
import { cn } from 'cn'

/*
 * SkillBridge tables (design spec §4): rows inside a white card, a sand header row with small
 * upper-case labels, 1px dividers between rows and no zebra stripes. Wrap a table in
 * <TableCard> when it is not already inside a card.
 */

function TableCard({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="table-card"
      className={cn('overflow-hidden rounded-[20px] border border-line bg-white', className)}
      {...props}
    />
  )
}

function Table({ className, ...props }: React.ComponentProps<'table'>) {
  return (
    <div data-slot="table-container" className="relative w-full overflow-x-auto">
      <table
        data-slot="table"
        className={cn('w-full caption-bottom text-sm text-ink', className)}
        {...props}
      />
    </div>
  )
}

function TableHeader({ className, ...props }: React.ComponentProps<'thead'>) {
  return (
    <thead
      data-slot="table-header"
      className={cn('bg-sand [&_tr]:border-t-0 [&_tr]:hover:bg-sand', className)}
      {...props}
    />
  )
}

function TableBody({ className, ...props }: React.ComponentProps<'tbody'>) {
  return <tbody data-slot="table-body" className={cn(className)} {...props} />
}

function TableFooter({ className, ...props }: React.ComponentProps<'tfoot'>) {
  return (
    <tfoot
      data-slot="table-footer"
      className={cn('border-t border-divider bg-sand font-bold [&>tr]:last:border-b-0', className)}
      {...props}
    />
  )
}

function TableRow({ className, ...props }: React.ComponentProps<'tr'>) {
  return (
    <tr
      data-slot="table-row"
      className={cn(
        'border-t border-divider transition-colors hover:bg-sand/60 has-aria-expanded:bg-sand/60 data-[state=selected]:bg-terracotta-tint/50',
        className,
      )}
      {...props}
    />
  )
}

function TableHead({ className, ...props }: React.ComponentProps<'th'>) {
  return (
    <th
      data-slot="table-head"
      className={cn(
        'h-11 px-3 text-left align-middle text-xs font-bold tracking-[0.04em] whitespace-nowrap text-muted-ink uppercase first:pl-6 last:pr-6 [&:has([role=checkbox])]:pr-0',
        className,
      )}
      {...props}
    />
  )
}

function TableCell({ className, ...props }: React.ComponentProps<'td'>) {
  return (
    <td
      data-slot="table-cell"
      className={cn(
        'px-3 py-3.5 align-middle whitespace-nowrap first:pl-6 last:pr-6 [&:has([role=checkbox])]:pr-0',
        className,
      )}
      {...props}
    />
  )
}

function TableCaption({ className, ...props }: React.ComponentProps<'caption'>) {
  return (
    <caption
      data-slot="table-caption"
      className={cn('mt-4 text-sm text-muted-ink', className)}
      {...props}
    />
  )
}

export {
  Table,
  TableCard,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
}
