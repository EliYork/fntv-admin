<template>
  <div class="playback-heatmap">
    <el-radio-group v-if="availableModes.length > 1" v-model="selectedMode" class="heatmap-mode" size="small" aria-label="点阵图模式">
      <el-radio-button value="date">日期点阵</el-radio-button>
      <el-radio-button value="weekhour">时段点阵</el-radio-button>
    </el-radio-group>

    <div v-if="selectedMode === 'date'" class="heatmap-scroll" @mouseleave="hideTooltip">
      <template v-if="sortedDateItems.length">
        <div class="date-months" :style="{ '--heatmap-columns': String(dateWeeks.length) }" aria-hidden="true">
          <span v-for="label in dateMonthLabels" :key="label.key" :style="{ gridColumn: `${label.column} / span 4` }">{{ label.text }}</span>
        </div>
        <div class="date-layout">
          <div class="date-weekdays" aria-hidden="true">
            <span></span><span>一</span><span></span><span>三</span><span></span><span>五</span><span></span>
          </div>
          <div
            class="date-grid"
            :style="{ '--heatmap-columns': String(dateWeeks.length) }"
            role="img"
            :aria-label="`${sortedDateItems[0]?.date} 至 ${sortedDateItems[sortedDateItems.length - 1]?.date} 的每日播放趋势`"
          >
            <template v-for="week in dateWeeks" :key="week.key">
              <span
                v-for="cell in week.cells"
                :key="cell.key"
                class="heatmap-cell"
                :class="[`level-${cell.item ? levelFor(cell.item.play_count, dateLevels) : 0}`, { 'is-outside': !cell.item }]"
                :aria-label="cell.item ? `${cell.date} 播放 ${cell.item.play_count} 次` : undefined"
                @mouseenter="showDateTooltip($event, cell)"
                @mousemove="moveTooltip($event)"
              ></span>
            </template>
          </div>
        </div>
      </template>
      <EmptyState v-else description="暂无播放趋势数据" />
    </div>

    <div v-else class="heatmap-scroll" @mouseleave="hideTooltip">
      <template v-if="weeklyItems.length">
        <div class="weekhour-axis" aria-hidden="true">
          <span></span>
          <span v-for="hour in hourLabels" :key="hour" :style="{ gridColumn: `${hour + 2}` }">{{ hour }}</span>
        </div>
        <div class="weekhour-layout">
          <div class="weekhour-weekdays" aria-hidden="true">
            <span v-for="label in weekdayLabels" :key="label">{{ label }}</span>
          </div>
          <div class="weekhour-grid" role="img" :aria-label="weekdayRangeLabel">
            <span
              v-for="cell in weeklyItems"
              :key="`${cell.weekday}-${cell.hour}`"
              class="heatmap-cell"
              :class="`level-${levelFor(cell.play_count, weeklyLevels)}`"
              :aria-label="`${cell.label} 播放 ${cell.play_count} 次`"
              @mouseenter="showWeeklyTooltip($event, cell)"
              @mousemove="moveTooltip($event)"
            ></span>
          </div>
        </div>
      </template>
      <EmptyState v-else description="暂无播放时段数据" />
    </div>

    <div v-if="tooltip.visible" class="heatmap-tooltip" :style="{ left: `${tooltip.left}px`, top: `${tooltip.top}px` }" role="tooltip">
      <strong>{{ tooltip.title }}</strong>
      <span>播放 {{ tooltip.playCount }} 次</span>
      <span v-if="tooltip.watchedCount !== null">看完 {{ tooltip.watchedCount }} 次</span>
      <span v-if="tooltip.activeUserCount !== null">活跃用户 {{ tooltip.activeUserCount }} 人</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import EmptyState from './EmptyState.vue'
import type { PlayTrendItem, WeeklyHourlyDistributionItem } from '../api/modules'

type HeatmapMode = 'date' | 'weekhour'
interface HeatmapCell { key: string; date: string; item: PlayTrendItem | null }
interface HeatmapWeek { key: string; cells: HeatmapCell[] }

const props = withDefaults(
  defineProps<{
    dateItems?: PlayTrendItem[]
    weeklyItems?: WeeklyHourlyDistributionItem[]
    modes?: HeatmapMode[]
    initialMode?: HeatmapMode
    weekdayRangeLabel?: string
  }>(),
  {
    dateItems: () => [],
    weeklyItems: () => [],
    modes: () => ['date'],
    initialMode: 'date',
    weekdayRangeLabel: '按星期与小时聚合'
  }
)

const selectedMode = ref<HeatmapMode>(props.initialMode)
const weekdayLabels = ['一', '二', '三', '四', '五', '六', '日']
const weekdayFullLabels = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
const hourLabels = [0, 3, 6, 9, 12, 15, 18, 21, 23]
const tooltip = reactive({
  visible: false,
  left: 0,
  top: 0,
  title: '',
  playCount: 0,
  watchedCount: null as number | null,
  activeUserCount: null as number | null
})

const availableModes = computed(() => props.modes.filter((mode) => mode === 'date' || mode === 'weekhour'))
const sortedDateItems = computed(() => [...props.dateItems].sort((a, b) => a.date.localeCompare(b.date)))
const dateWeeks = computed(() => buildDateWeeks(sortedDateItems.value))
const dateMonthLabels = computed(() => buildDateMonthLabels(dateWeeks.value, sortedDateItems.value))
const dateLevels = computed(() => quantileLevels(sortedDateItems.value.map((item) => item.play_count)))
const weeklyLevels = computed(() => quantileLevels(props.weeklyItems.map((item) => item.play_count)))

watch(availableModes, (modes) => {
  if (!modes.includes(selectedMode.value)) selectedMode.value = modes[0] || 'date'
}, { immediate: true })

function quantileLevels(values: number[]): number[] {
  const positive = values.filter((value) => value > 0).sort((a, b) => a - b)
  if (!positive.length) return [Infinity, Infinity, Infinity, Infinity]
  const pick = (q: number) => positive[Math.min(positive.length - 1, Math.floor(positive.length * q))]
  return [pick(0.2), pick(0.4), pick(0.6), pick(0.8)]
}

function levelFor(value: number, levels: number[]): number {
  if (value <= 0) return 0
  if (value > levels[3]) return 4
  if (value > levels[2]) return 3
  if (value > levels[1]) return 2
  return 1
}

function buildDateWeeks(items: PlayTrendItem[]): HeatmapWeek[] {
  if (!items.length) return []
  const byDate = new Map(items.map((item) => [item.date, item]))
  const first = parseDateKey(items[0].date)
  const last = parseDateKey(items[items.length - 1].date)
  const start = addDays(first, -mondayIndex(first))
  const end = addDays(last, 6 - mondayIndex(last))
  const weeks: HeatmapWeek[] = []
  for (let cursor = start; cursor <= end; cursor = addDays(cursor, 7)) {
    const cells: HeatmapCell[] = []
    for (let day = 0; day < 7; day += 1) {
      const current = addDays(cursor, day)
      const key = formatDateKey(current)
      cells.push({ key, date: key, item: byDate.get(key) || null })
    }
    weeks.push({ key: formatDateKey(cursor), cells })
  }
  return weeks
}

function buildDateMonthLabels(weeks: HeatmapWeek[], items: PlayTrendItem[]) {
  if (!weeks.length || !items.length) return []
  const validDates = new Set(items.map((item) => item.date))
  const seenMonths = new Set<string>()
  const labels: Array<{ key: string; text: string; column: number }> = []
  weeks.forEach((week, index) => {
    const firstVisible = week.cells.find((cell) => validDates.has(cell.date))
    if (!firstVisible) return
    const date = parseDateKey(firstVisible.date)
    const monthKey = `${date.getFullYear()}-${date.getMonth()}`
    if (seenMonths.has(monthKey)) return
    seenMonths.add(monthKey)
    labels.push({
      key: monthKey,
      text: date.getMonth() === 0 ? `${date.getFullYear()}年 1月` : `${date.getMonth() + 1}月`,
      column: index + 1
    })
  })
  return labels
}

function parseDateKey(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function formatDateKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

function mondayIndex(date: Date): number { return (date.getDay() + 6) % 7 }

function showDateTooltip(event: MouseEvent, cell: HeatmapCell) {
  if (!cell.item) return hideTooltip()
  const date = parseDateKey(cell.date)
  tooltip.visible = true
  tooltip.title = `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${weekdayFullLabels[date.getDay()]}`
  tooltip.playCount = cell.item.play_count
  tooltip.watchedCount = cell.item.watched_count
  tooltip.activeUserCount = cell.item.active_user_count
  moveTooltip(event)
}

function showWeeklyTooltip(event: MouseEvent, cell: WeeklyHourlyDistributionItem) {
  tooltip.visible = true
  tooltip.title = cell.label
  tooltip.playCount = cell.play_count
  tooltip.watchedCount = null
  tooltip.activeUserCount = null
  moveTooltip(event)
}

function moveTooltip(event: MouseEvent) {
  if (!tooltip.visible) return
  tooltip.left = Math.max(8, Math.min(event.clientX + 14, window.innerWidth - 218))
  tooltip.top = Math.max(8, Math.min(event.clientY + 14, window.innerHeight - 128))
}

function hideTooltip() { tooltip.visible = false }
</script>

<style scoped>
.playback-heatmap { min-width: 0; }
.heatmap-mode { margin-bottom: 14px; }
.heatmap-scroll { overflow-x: auto; padding: 2px 0 4px; }
.date-months { --heatmap-columns: 5; display: grid; grid-template-columns: repeat(var(--heatmap-columns), minmax(13px, 18px)); justify-content: space-between; gap: 4px; width: calc(100% - 30px); min-width: max-content; margin: 0 0 9px 30px; color: var(--app-muted); font-size: 10px; }
.date-months span { white-space: nowrap; }
.date-layout { display: grid; grid-template-columns: 20px minmax(0, 1fr); gap: 10px; width: 100%; min-width: max-content; }
.date-weekdays { display: grid; grid-template-rows: repeat(7, 18px); gap: 4px; width: 20px; color: var(--app-muted); font-size: 9px; line-height: 18px; text-align: right; }
.date-grid { --heatmap-columns: 5; display: grid; grid-auto-flow: column; grid-template-rows: repeat(7, 18px); grid-template-columns: repeat(var(--heatmap-columns), minmax(13px, 18px)); justify-content: space-between; gap: 4px; width: 100%; min-width: max-content; }
.heatmap-cell { display: block; width: 18px; height: 18px; border-radius: 3px; background: var(--app-data-0); }
.heatmap-cell.is-outside { visibility: hidden; }
.heatmap-cell.level-1 { background: var(--app-data-1); }
.heatmap-cell.level-2 { background: var(--app-data-2); }
.heatmap-cell.level-3 { background: var(--app-data-3); }
.heatmap-cell.level-4 { background: var(--app-data-4); }
.weekhour-axis { display: grid; grid-template-columns: 24px repeat(24, 18px); gap: 4px; width: max-content; margin-bottom: 8px; color: var(--app-muted); font-size: 9px; text-align: center; }
.weekhour-layout { display: flex; gap: 10px; width: max-content; }
.weekhour-weekdays { display: grid; grid-template-rows: repeat(7, 18px); gap: 4px; width: 20px; color: var(--app-muted); font-size: 9px; line-height: 18px; text-align: right; }
.weekhour-grid { display: grid; grid-template-columns: repeat(24, 18px); grid-template-rows: repeat(7, 18px); grid-auto-flow: row; gap: 4px; }
.heatmap-tooltip { position: fixed; z-index: 4000; display: grid; gap: 4px; width: 194px; padding: 10px 12px; border: 1px solid var(--app-border); border-radius: 8px; background: var(--app-surface); box-shadow: 0 12px 28px rgba(18, 22, 20, 0.14); color: var(--app-muted-strong); font-size: 12px; pointer-events: none; }
.heatmap-tooltip strong { color: var(--app-title); font-size: 12px; }

@media (max-width: 760px) {
  .date-grid, .date-months { justify-content: start; }
}
</style>
