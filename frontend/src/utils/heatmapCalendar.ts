import type { PlayTrendItem } from '../api/modules'

export interface HeatmapMonthCell {
  date: string
}

export interface HeatmapMonthWeek {
  cells: HeatmapMonthCell[]
}

export interface HeatmapMonthLabel {
  key: string
  text: string
  column: number
}

export function buildDateMonthLabels(weeks: HeatmapMonthWeek[], items: PlayTrendItem[]): HeatmapMonthLabel[] {
  if (!weeks.length || !items.length) return []
  const validDates = new Set(items.map((item) => item.date))
  const labels: HeatmapMonthLabel[] = []

  weeks.forEach((week, index) => {
    const firstOfMonth = week.cells.find((cell) => {
      if (!validDates.has(cell.date)) return false
      return parseDateKey(cell.date).getDate() === 1
    })
    if (!firstOfMonth) return

    const date = parseDateKey(firstOfMonth.date)
    const year = date.getFullYear()
    const month = date.getMonth() + 1
    const previous = labels[labels.length - 1]
    const showYear = !previous || !previous.key.startsWith(`${year}-`)
    labels.push({
      key: `${year}-${String(month).padStart(2, '0')}`,
      text: showYear ? `${year}年${month}月` : `${month}月`,
      column: index + 1
    })
  })

  return labels
}

function parseDateKey(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}
