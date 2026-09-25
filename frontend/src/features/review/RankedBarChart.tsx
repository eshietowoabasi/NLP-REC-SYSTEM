import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

/** One horizontal bar. `flagged` bars take the warning colour (the caller labels why). */
export interface BarDatum {
  label: string
  value: number
  /** Extra line shown in the hover tooltip. */
  detail?: string
  flagged?: boolean
}

const BAR_THICKNESS = 16 // ≤ 24px; the rest of each band is air
const ROW_HEIGHT = 32
const LABEL_WIDTH = 170
const LABEL_CHARS = 26

/** One-line category label, shortened with an ellipsis; the full text is in a <title>. */
function CategoryTick({
  x,
  y,
  payload,
}: {
  x?: number | string
  y?: number | string
  payload?: { value: string }
}) {
  const text = payload?.value ?? ''
  const short = text.length > LABEL_CHARS ? `${text.slice(0, LABEL_CHARS - 1).trimEnd()}…` : text
  return (
    <text
      x={Number(x) - 6}
      y={Number(y)}
      dy="0.35em"
      textAnchor="end"
      fontSize={12}
      fill="var(--foreground)"
    >
      <title>{text}</title>
      {short}
    </text>
  )
}

interface TooltipProps {
  active?: boolean
  payload?: { payload: BarDatum }[]
  format: (value: number) => string
}

function BarTooltip({ active, payload, format }: TooltipProps) {
  const datum = payload?.[0]?.payload
  if (!active || !datum) return null
  return (
    <div className="rounded-md border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md">
      <p className="font-medium">{datum.label}</p>
      <p className="tabular-nums">{format(datum.value)}</p>
      {datum.detail && <p className="text-muted-foreground">{datum.detail}</p>}
    </div>
  )
}

/**
 * Single-series ranked bar chart (magnitude → one hue), bars growing from a shared baseline,
 * with a hover tooltip. The data is also shown in a table next to every use of this chart,
 * so nothing is available only through colour or hover.
 */
export function RankedBarChart({
  data,
  label,
  format = (value) => value.toFixed(3),
  domain,
  threshold,
}: {
  data: BarDatum[]
  /** Accessible name for the figure. */
  label: string
  format?: (value: number) => string
  domain?: [number, number]
  /** Optional vertical reference line (e.g. the duplicate threshold). */
  threshold?: { value: number; label: string }
}) {
  const height = Math.max(data.length * ROW_HEIGHT + 40, 120)
  return (
    <figure aria-label={label} className="w-full">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} layout="vertical" margin={{ top: 16, right: 24, bottom: 4, left: 4 }}>
          <CartesianGrid horizontal={false} stroke="var(--viz-grid)" strokeWidth={1} />
          <XAxis
            type="number"
            domain={domain ?? [0, 'auto']}
            tickFormatter={format}
            tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }}
            axisLine={{ stroke: 'var(--viz-axis)' }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={LABEL_WIDTH}
            interval={0}
            tick={<CategoryTick />}
            axisLine={{ stroke: 'var(--viz-axis)' }}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: 'var(--muted)' }}
            content={<BarTooltip format={format} />}
            isAnimationActive={false}
          />
          <Bar
            dataKey="value"
            barSize={BAR_THICKNESS}
            radius={[0, 4, 4, 0]}
            isAnimationActive={false}
          >
            {data.map((datum) => (
              <Cell
                key={datum.label}
                fill={datum.flagged ? 'var(--viz-warning)' : 'var(--viz-series)'}
              />
            ))}
          </Bar>
          {threshold && (
            <ReferenceLine
              x={threshold.value}
              stroke="var(--foreground)"
              strokeWidth={1}
              label={{
                value: threshold.label,
                position: 'top',
                fill: 'var(--muted-foreground)',
                fontSize: 11,
              }}
            />
          )}
        </BarChart>
      </ResponsiveContainer>
    </figure>
  )
}
