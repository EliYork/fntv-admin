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
          <span v-for="label in dateMonthLabels" :key="label.key">{{ label.text }}</span>
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
                :class="[`level-${cell.item ? levelFor(cell.item.play_count, dateMax) : 0}`, { 'is-empty': !cell.item }]"
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
              :class="`level-${levelFor(cell.play_count, weeklyMax)}`"
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
const dateMonthLabels = computed(() =>
  dateWeeks.value.map((week, index, weeks) => ({
    key: week.key,
    text: monthLabelForWeek(week, index, weeks)
  }))
)
const dateMax = computed(() => maxValue(props.dateItems.map((item) => item.play_count)))
const weeklyMax = computed(() => maxValue(props.weeklyItems.map((item) => item.play_count)))
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

function maxValue(values: number[]): number {
  return values.reduce((max, value) => Math.max(max, value), 0)
}

function levelFor(value: number, max: number): number {
  if (value <= 0 || max <= 0) return 0
  const ratio = value / max
  if (ratio >= 0.75) return 4
  if (ratio >= 0.5) return 3
  if (ratio >= 0.25) return 2
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

function monthLabelForWeek(week: HeatmapWeek, index: number, weeks: HeatmapWeek[]): string {
  const firstCell = week.cells[0]
  const monthStart = week.cells.find((cell) => parseDateKey(cell.date).getDate() === 1)
  const previousMonth = index > 0 ? parseDateKey(weeks[index - 1].cells[0].date).getMonth() : -1
  const currentMonth = parseDateKey(firstCell.date).getMonth()
  const labelCell = monthStart || (index === 0 || currentMonth !== previousMonth ? firstCell : null)
  return labelCell ? `${parseDateKey(labelCell.date).getMonth() + 1}月` : ''
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
  tooltip.title = cell.date
  tooltip.playCount = cell.item.play_count
  tooltip.watchedCount = cell.item.watched_count
  tooltip.activeUserCount = cell.item.active_user_count
  moveTooltip(event)
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
  grid-template-columns: 38px repeat(var(--heatmap-columns), 14px);
  gap: 4px;
  width: max-content;
  min-width: 240px;
}

.date-months span:first-child {
  grid-column: 2;
}

.date-body {
  position: relative;
  display: flex;
  gap: 8px;
  width: max-content;
  min-width: 240px;
}

.date-weekdays {
  display: grid;
  grid-template-rows: repeat(7, 14px);
  gap: 4px;
  width: 30px;
  line-height: 14px;
  text-align: right;
}

.date-grid {
  --heatmap-columns: 5;
  display: grid;
  grid-auto-flow: column;
  grid-template-rows: repeat(7, 14px);
  grid-template-columns: repeat(var(--heatmap-columns), 14px);
  gap: 4px;
  width: max-content;
}

.weekhour-axis {
  display: grid;
  grid-template-columns: 42px repeat(24, 16px);
  gap: 4px;
  width: max-content;
  min-width: 480px;
  line-height: 14px;
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
  grid-template-rows: repeat(7, 16px);
  gap: 4px;
  width: 34px;
  line-height: 16px;
  text-align: right;
}

.weekhour-grid {
  display: grid;
  grid-template-columns: repeat(24, 16px);
  grid-template-rows: repeat(7, 16px);
  grid-auto-flow: row;
  gap: 4px;
}

.heatmap-cell {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 1px solid var(--app-border-soft);
  border-radius: 3px;
  background: #edf2f7;
}

.weekhour-grid .heatmap-cell {
  width: 16px;
  height: 16px;
}

.heatmap-cell.is-empty {
  opacity: 0.35;
}

.heatmap-cell.level-1 {
  background: #bfdbfe;
}

.heatmap-cell.level-2 {
  background: #60a5fa;
}

.heatmap-cell.level-3 {
  background: #2563eb;
}

.heatmap-cell.level-4 {
  background: #1e40af;
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

[data-theme='dark'] .heatmap-cell.level-1 {
  background: #1e3a5f;
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
