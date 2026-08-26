export interface ApplicationDateParts {
  year: number
  month: number
  day: number
  hour: number
  minute: number
  second: number
  dateKey: string
  timeKey: string
}

const WALL_CLOCK_RE = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$/

export function parseApplicationDateTime(value: string | number | null | undefined, timeZone = 'Asia/Shanghai'): ApplicationDateParts | null {
  if (value == null || value === '') return null
  if (typeof value === 'string') {
    const match = WALL_CLOCK_RE.exec(value.trim())
    if (match) return partsFromNumbers(match.slice(1, 7).map(Number))
  }
  const timestamp = typeof value === 'number' ? (value >= 100_000_000_000 ? value : value * 1000) : Date.parse(value)
  if (!Number.isFinite(timestamp)) return null
  try {
    const values = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23'
    }).formatToParts(new Date(timestamp))
    const get = (type: Intl.DateTimeFormatPartTypes) => Number(values.find((part) => part.type === type)?.value)
    return partsFromNumbers([get('year'), get('month'), get('day'), get('hour'), get('minute'), get('second')])
  } catch {
    return null
  }
}

export function formatInstant(timestamp: number, timeZone = 'Asia/Shanghai'): string {
  return formatApplicationDateTime(timestamp, timeZone)
}

export function formatApplicationDateTime(value: string | number | null | undefined, timeZone = 'Asia/Shanghai'): string {
  const parts = parseApplicationDateTime(value, timeZone)
  return parts ? `${parts.dateKey} ${parts.timeKey}` : '—'
}

export function applicationTodayKey(timeZone = 'Asia/Shanghai'): string {
  return parseApplicationDateTime(Date.now(), timeZone)?.dateKey || ''
}

export function calendarDayDifference(laterDateKey: string, earlierDateKey: string): number {
  return Math.round((dateKeyAsUtc(laterDateKey) - dateKeyAsUtc(earlierDateKey)) / 86_400_000)
}

function partsFromNumbers(values: number[]): ApplicationDateParts | null {
  const [year, month, day, hour, minute, second] = values
  if (![year, month, day, hour, minute, second].every(Number.isFinite)) return null
  return {
    year, month, day, hour, minute, second,
    dateKey: `${year}-${pad(month)}-${pad(day)}`,
    timeKey: `${pad(hour)}:${pad(minute)}:${pad(second)}`
  }
}

function dateKeyAsUtc(value: string): number {
  const [year, month, day] = value.split('-').map(Number)
  return Date.UTC(year, month - 1, day)
}

function pad(value: number): string {
  return String(value).padStart(2, '0')
}
