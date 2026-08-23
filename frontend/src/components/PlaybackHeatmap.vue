<template>
  <div class="playback-heatmap">
    <div v-if="availableModes.length > 1" class="heatmap-toolbar">
      <el-radio-group v-model="selectedMode" size="small">
        <el-radio-button label="date">日期点阵</el-radio-button>
        <el-radio-button label="weekhour">时段点阵</el-radio-button>
      </el-radio-group>
      <span class="heatmap-note">{{ modeNote }}</span>
    </div>

    <div v-if="selectedMode === 'date'" class="heatmap-wrap" @mouseleave="hideTooltip">
      <template v-if="dateItems.length">
        <div class="date-months" :style="{ '--heatmap-columns': String(dateWeeks.length) }">
          <span v-for="label in dateMonthLabels" :key="label.key" :style="{ gridColumn: `${label.column} / span 4` }">{{ label.text }}</span>
        </div>
        <div class="date-body">
          <div class="date-weekdays" aria-hidden="true">
            <span></span>
            <span>周一</span>
            <span></span>
            <span>周三</span>
            <span></span>
            <span>周五</span>
            <span></span>
          </div>
          <div class="date-grid" :style="{ '--heatmap-columns': String(dateWeeks.length) }">
            <template v-for="week in dateWeeks" :key="week.key">
              <div
                v-for="cell in week.cells"
                :key="cell.key"
                class="heatmap-cell"
                :class="[`level-${cell.item ? levelFor(cell.item.play_count, dateLevels) : 0}`, { 'is-empty': !cell.item }]"
                :aria-label="cell.item ? `${cell.date} 播放 ${cell.item.play_count} 次` : cell.date"
                @mouseenter="showDateTooltip($event, cell)"
                @mousemove="moveTooltip($event)"
              ></div>
            </template>
          </div>
        </div>
        <div class="heatmap-summary">
          <span>{{ dateItems[0]?.date }} 至 {{ dateItems[dateItems.length - 1]?.date }}</span>
          <span>共 {{ dateTotal }} 次播放</span>
        </div>
        <HeatmapLegend />
      </template>
      <EmptyState v-else description="暂无播放趋势数据" />
    </div>

    <div v-else class="heatmap-wrap weekhour-wrap" @mouseleave="hideTooltip">
      <template v-if="weeklyItems.length">
        <div class="weekhour-axis">
          <span></span>
          <span v-for="hour in hourLabels" :key="hour" :style="{ gridColumn: `${hour + 2}` }">{{ hour }}</span>
        </div>
        <div class="weekhour-body">
          <div class="weekhour-weekdays" aria-hidden="true">
            <span v-for="label in weekdayLabels" :key="label">{{ label }}</span>
          </div>
          <div class="weekhour-grid">
            <div
              v-for="cell in weeklyItems"
              :key="`${cell.weekday}-${cell.hour}`"
              class="heatmap-cell"
              :class="`level-${levelFor(cell.play_count, weeklyLevels)}`"
              :aria-label="`${cell.label} 播放 ${cell.play_count} 次`"
              @mouseenter="showWeeklyTooltip($event, cell)"
              @mousemove="moveTooltip($event)"
            ></div>
          </div>
        </div>
        <div class="heatmap-summary">
          <span>{{ weekdayRangeLabel }}</span>
          <span>共 {{ weeklyTotal }} 次播放</span>
        </div>
        <HeatmapLegend />
      </template>
      <EmptyState v-else description="暂无播放时段数据" />
    </div>

    <div v-if="tooltip.visible" class="heatmap-tooltip" :style="{ left: `${tooltip.left}px`, top: `${tooltip.top}px` }">
      <strong>{{ tooltip.title }}</strong>
      <span>播放 {{ tooltip.playCount }} 次</span>
      <span v-if="tooltip.watchedCount !== null">看完 {{ tooltip.watchedCount }} 次</span>
      <span v-if="tooltip.activeUserCount !== null">活跃用户 {{ tooltip.activeUserCount }} 人</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, reactive, ref, watch } from 'vue'
import EmptyState from './EmptyState.vue'
import type { PlayTrendItem, WeeklyHourlyDistributionItem } from '../api/modules'

type HeatmapMode = 'date' | 'weekhour'

interface HeatmapCell {
  key: string
  date: string
  item: PlayTrendItem | null
}

interface HeatmapWeek {
  key: string
  cells: HeatmapCell[]
}

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
const weekdayLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
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
const dateWeeks = computed(() => buildDateWeeks(props.dateItems))
const dateMonthLabels = computed(() => buildDateMonthLabels(dateWeeks.value, props.dateItems))
const dateLevels = computed(() => quantileLevels(props.dateItems.map((item) => item.play_count)))
const weeklyLevels = computed(() => quantileLevels(props.weeklyItems.map((item) => item.play_count)))
const dateTotal = computed(() => props.dateItems.reduce((total, item) => total + item.play_count, 0))
const weeklyTotal = computed(() => props.weeklyItems.reduce((total, item) => total + item.play_count, 0))
const modeNote = computed(() => (selectedMode.value === 'date' ? '按日期查看播放活跃度' : '按星期和小时查看播放习惯'))

watch(
  availableModes,
  (modes) => {
    if (!modes.includes(selectedMode.value)) {
      selectedMode.value = modes[0] || 'date'
    }
  },
  { immediate: true }
)

const HeatmapLegend = defineComponent({
  name: 'HeatmapLegend',
  setup() {
    return () =>
      h('div', { class: 'heatmap-legend' }, [
        h('span', '少'),
        ...[0, 1, 2, 3, 4].map((level) => h('i', { class: ['heatmap-cell', `level-${level}`] })),
        h('span', '多')
      ])
  }
})

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
  const rangeStart = items[0].date
  const rangeEnd = items[items.length - 1].date
  const labels: Array<{ key: string; text: string; column: number }> = []
  const firstMonth = parseDateKey(rangeStart)
  const lastMonth = parseDateKey(rangeEnd)
  const firstLabelMonth = firstMonth.getDate() === 1
    ? new Date(firstMonth.getFullYear(), firstMonth.getMonth(), 1)
    : new Date(firstMonth.getFullYear(), firstMonth.getMonth() + 1, 1)

  for (let cursor = firstLabelMonth; cursor <= lastMonth; cursor = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1)) {
    const monthStart = formatDateKey(cursor)
    const weekIndex = weeks.findIndex((week) => week.cells.some((cell) => cell.date === monthStart))
    if (weekIndex < 0) continue
    labels.push({
      key: `${cursor.getFullYear()}-${cursor.getMonth()}`,
      text: cursor.getMonth() === 0 ? `${cursor.getFullYear()}年1月` : `${cursor.getMonth() + 1}月`,
      column: weekIndex + 1
    })
  }
  return labels
}

function parseDateKey(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function formatDateKey(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

function mondayIndex(date: Date): number {
  return (date.getDay() + 6) % 7
}

function showDateTooltip(event: MouseEvent, cell: HeatmapCell): void {
  if (!cell.item) {
    hideTooltip()
    return
  }
  tooltip.visible = true
  tooltip.title = formatDateTitle(cell.date)
  tooltip.playCount = cell.item.play_count
  tooltip.watchedCount = cell.item.watched_count
  tooltip.activeUserCount = cell.item.active_user_count
  moveTooltip(event)
}

function formatDateTitle(date: string): string {
  const d = parseDateKey(date)
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${weekdayFullLabels[d.getDay()]}`
}

function showWeeklyTooltip(event: MouseEvent, cell: WeeklyHourlyDistributionItem): void {
  tooltip.visible = true
  tooltip.title = cell.label
  tooltip.playCount = cell.play_count
  tooltip.watchedCount = null
  tooltip.activeUserCount = null
  moveTooltip(event)
}

function moveTooltip(event: MouseEvent): void {
  if (!tooltip.visible) return
  tooltip.left = Math.max(8, Math.min(event.clientX + 14, window.innerWidth - 220))
  tooltip.top = Math.max(8, Math.min(event.clientY + 14, window.innerHeight - 120))
}

function hideTooltip(): void {
  tooltip.visible = false
}
</script>

<style scoped>
.playback-heatmap {
  min-width: 0;
}

.heatmap-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.heatmap-note,
.heatmap-summary,
.heatmap-legend,
.date-months,
.date-weekdays,
.weekhour-axis,
.weekhour-weekdays {
  color: var(--app-muted);
  font-size: 12px;
}

.heatmap-wrap {
  display: grid;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.date-months {
  --heatmap-columns: 5;
  display: grid;
  grid-template-columns: repeat(var(--heatmap-columns), minmax(13px, 17px));
  justify-content: space-between;
  gap: 3px;
  width: calc(100% - 38px);
  margin-left: 38px;
  min-width: 240px;
}

.date-months span {
  white-space: nowrap;
}

.date-body {
  position: relative;
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 8px;
  width: 100%;
  min-width: 240px;
}

.date-weekdays {
  display: grid;
  grid-template-rows: repeat(7, 17px);
  gap: 3px;
  width: 30px;
  line-height: 17px;
  text-align: right;
}

.date-grid {
  --heatmap-columns: 5;
  display: grid;
  grid-auto-flow: column;
  grid-template-rows: repeat(7, 17px);
  grid-template-columns: repeat(var(--heatmap-columns), minmax(13px, 17px));
  justify-content: space-between;
  gap: 3px;
  width: 100%;
  min-width: max-content;
}

.weekhour-axis {
  display: grid;
  grid-template-columns: 42px repeat(24, 20px);
  gap: 5px;
  width: max-content;
  min-width: 480px;
  line-height: 18px;
  text-align: center;
}

.weekhour-body {
  display: flex;
  gap: 8px;
  width: max-content;
  min-width: 480px;
}

.weekhour-weekdays {
  display: grid;
  grid-template-rows: repeat(7, 20px);
  gap: 5px;
  width: 34px;
  line-height: 20px;
  text-align: right;
}

.weekhour-grid {
  display: grid;
  grid-template-columns: repeat(24, 20px);
  grid-template-rows: repeat(7, 20px);
  grid-auto-flow: row;
  gap: 5px;
}

.heatmap-cell {
  display: inline-block;
  width: 17px;
  height: 17px;
  border: 1px solid var(--app-border-soft);
  border-radius: 4px;
  background: #edf2f7;
}

.weekhour-grid .heatmap-cell {
  width: 20px;
  height: 20px;
}

.heatmap-cell.is-empty {
  border-color: transparent;
  background: transparent;
}

.heatmap-cell.level-0 {
  background: #f1f5f9;
}

.heatmap-cell.level-1 {
  background: #dbeafe;
}

.heatmap-cell.level-2 {
  background: #93c5fd;
}

.heatmap-cell.level-3 {
  background: #3b82f6;
}

.heatmap-cell.level-4 {
  background: #1d4ed8;
}

.heatmap-summary {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
}

.heatmap-legend {
  display: flex;
  align-items: center;
  gap: 5px;
}

.heatmap-tooltip {
  position: fixed;
  z-index: 4000;
  display: grid;
  gap: 4px;
  width: 190px;
  padding: 10px 12px;
  border: 1px solid rgba(15, 23, 42, 0.14);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.97);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.16);
  color: #334155;
  font-size: 12px;
  pointer-events: none;
}

.heatmap-tooltip strong {
  color: #111827;
  font-size: 13px;
}

[data-theme='dark'] .heatmap-cell {
  border-color: #263149;
  background: #1d2633;
}

[data-theme='dark'] .heatmap-cell.level-0 {
  background: #1d2633;
}

[data-theme='dark'] .heatmap-cell.level-1 {
  background: #274b6e;
}

[data-theme='dark'] .heatmap-cell.level-2 {
  background: #1d4ed8;
}

[data-theme='dark'] .heatmap-cell.level-3 {
  background: #3b82f6;
}

[data-theme='dark'] .heatmap-cell.level-4 {
  background: #93c5fd;
}

[data-theme='dark'] .heatmap-tooltip {
  border-color: #334155;
  background: rgba(15, 23, 42, 0.97);
  color: #cbd5e1;
}

[data-theme='dark'] .heatmap-tooltip strong {
  color: #f8fafc;
}

@media (max-width: 640px) {
  .heatmap-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
