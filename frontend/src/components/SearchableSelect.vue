<template>
  <div ref="rootEl" class="searchable-select" :class="{ 'is-open': open }">
    <button
      type="button"
      class="searchable-select__trigger"
      :class="triggerClass"
      @click.stop="toggle"
    >
      <span class="searchable-select__trigger-text">{{ displayLabel }}</span>
      <span class="searchable-select__caret" aria-hidden="true">▾</span>
    </button>
    <div v-show="open" class="searchable-select__dropdown" @mousedown.prevent>
      <input
        ref="searchInputRef"
        v-model="query"
        type="text"
        class="searchable-select__search"
        :placeholder="searchPlaceholder"
        autocomplete="off"
        @keydown.escape.stop="close"
      />
      <ul class="searchable-select__list" role="listbox">
        <li
          v-if="showAllOption"
          role="option"
          :aria-selected="modelValue === 0"
          :class="{ 'is-active': modelValue === 0 }"
          class="searchable-select__item"
          @click="pick(0)"
        >
          {{ emptyLabel }}
        </li>
        <li
          v-for="opt in filteredOptions"
          :key="opt.id"
          role="option"
          :aria-selected="modelValue === opt.id"
          :class="{ 'is-active': modelValue === opt.id }"
          class="searchable-select__item"
          @click="pick(opt.id)"
        >
          {{ opt.label }}
        </li>
        <li v-if="showEmptyState" class="searchable-select__empty">无匹配项</li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

export type SearchableOption = {
  id: number
  label: string
  /** 用于关键字匹配（可含卡号、发行方、车牌等） */
  keywords: string
}

const props = withDefaults(
  defineProps<{
    modelValue: number
    options: SearchableOption[]
    allowEmpty?: boolean
    emptyLabel?: string
    searchPlaceholder?: string
    /** 附加到触发按钮的 class，如 filter-control */
    triggerClass?: string
  }>(),
  {
    allowEmpty: false,
    emptyLabel: '全部',
    searchPlaceholder: '输入关键字筛选…',
    triggerClass: '',
  },
)

const emit = defineEmits<{ 'update:modelValue': [v: number] }>()

const rootEl = ref<HTMLElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)
const open = ref(false)
const query = ref('')

const queryTrim = computed(() => query.value.trim())

const filteredOptions = computed(() => {
  const q = queryTrim.value
  if (!q) return props.options
  const ql = q.toLowerCase()
  return props.options.filter((o) => o.keywords.toLowerCase().includes(ql))
})

function allOptionMatchesQuery(): boolean {
  const q = queryTrim.value
  if (!q) return true
  if (props.emptyLabel.includes(q)) return true
  if ('全部'.includes(q)) return true
  if (q.length <= 2 && '全部'.startsWith(q)) return true
  return false
}

const showAllOption = computed(() => props.allowEmpty && allOptionMatchesQuery())

const showEmptyState = computed(
  () => !showAllOption.value && filteredOptions.value.length === 0,
)

const displayLabel = computed(() => {
  if (props.allowEmpty && props.modelValue === 0) return props.emptyLabel
  const hit = props.options.find((o) => o.id === props.modelValue)
  return hit?.label ?? (props.modelValue ? `#${props.modelValue}` : props.emptyLabel)
})

function pick(id: number) {
  emit('update:modelValue', id)
  close()
}

function close() {
  open.value = false
  query.value = ''
}

function toggle() {
  open.value = !open.value
  if (open.value) {
    void nextTick(() => searchInputRef.value?.focus())
  } else {
    query.value = ''
  }
}

function onDocPointerDown(ev: PointerEvent) {
  const el = rootEl.value
  if (!el || !open.value) return
  const t = ev.target as Node
  if (!el.contains(t)) close()
}

watch(open, (v) => {
  if (!v) query.value = ''
})

onMounted(() => document.addEventListener('pointerdown', onDocPointerDown, true))
onUnmounted(() => document.removeEventListener('pointerdown', onDocPointerDown, true))
</script>

<style scoped>
/* 工具栏内与表单内共用：触发器可较窄，下拉层单独加宽以便卡号+单位单行展示 */
.searchable-select {
  position: relative;
  flex: 1 1 220px;
  min-width: 180px;
  max-width: min(400px, 100%);
}

/* 触发器：与 FuelView 筛选区 input[type=date] 同风格（白底、12px 圆角、无浏览器蓝框） */
.searchable-select__trigger {
  width: 100%;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin: 0;
  cursor: pointer;
  text-align: left;
  font: inherit;
  font-size: 13px;
  line-height: 1.35;
  color: var(--cl-near-black, #1a1a1a);
  padding: 10px 10px;
  min-height: 42px;
  border: 1px solid var(--cl-border-cream, #e8e0d4);
  border-radius: 12px;
  background: var(--cl-white, #fff);
  box-shadow: none;
  appearance: none;
  -webkit-appearance: none;
}

.searchable-select__trigger:hover {
  border-color: var(--cl-border-warm, #d4c4b0);
}

.searchable-select__trigger:focus {
  outline: none;
}

.searchable-select__trigger:focus-visible,
.searchable-select.is-open .searchable-select__trigger {
  outline: none;
  border-color: var(--cl-border-warm, #d4c4b0);
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.05);
}

.searchable-select__trigger-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.searchable-select__caret {
  flex-shrink: 0;
  font-size: 10px;
  opacity: 0.65;
}

.searchable-select__dropdown {
  position: absolute;
  left: 0;
  top: calc(100% + 4px);
  z-index: 50;
  box-sizing: border-box;
  /* 至少 420px，且可随最长选项变宽；不超过视口 */
  min-width: max(100%, 420px);
  width: max-content;
  max-width: min(640px, calc(100vw - 24px));
  background: var(--cl-white, #fff);
  border: 1px solid var(--cl-border-cream, #e8e0d4);
  border-radius: 12px;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.12);
  padding: 8px;
  max-height: 280px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.searchable-select__search {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 10px;
  border-radius: 12px;
  border: 1px solid var(--cl-border-cream, #e8e0d4);
  background: var(--cl-white, #fff);
  color: var(--cl-near-black, #1a1a1a);
  font-size: 13px;
}

.searchable-select__search:focus {
  outline: none;
  border-color: var(--cl-border-warm, #d4c4b0);
}

.searchable-select__list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-x: auto;
  overflow-y: auto;
  max-height: 220px;
}

.searchable-select__item {
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 12px;
  cursor: pointer;
  line-height: 1.35;
  white-space: nowrap;
}

.searchable-select__item:hover {
  background: var(--cl-warm-sand, #f5efe6);
}

.searchable-select__item.is-active {
  background: rgba(181, 51, 51, 0.12);
  font-weight: 700;
}

.searchable-select__empty {
  padding: 12px 10px;
  font-size: 12px;
  color: var(--cl-olive, #6b6b5a);
  text-align: center;
}

@media (max-width: 768px) {
  .searchable-select__trigger {
    min-height: 48px;
    padding: 12px 14px;
    font-size: 16px;
    border-radius: 12px;
  }

  .searchable-select__caret {
    font-size: 11px;
    opacity: 0.72;
  }

  .searchable-select__dropdown {
    min-width: 100%;
    width: 100%;
    max-width: 100%;
    max-height: min(56vh, 380px);
    top: calc(100% + 6px);
    padding: 10px;
    border-radius: 14px;
    box-shadow: 0 12px 28px rgba(20, 20, 19, 0.16);
  }

  .searchable-select__search {
    min-height: 46px;
    font-size: 16px;
    border-radius: 12px;
  }

  .searchable-select__list {
    max-height: min(42vh, 300px);
  }

  .searchable-select__item {
    padding: 12px;
    font-size: 15px;
    line-height: 1.45;
    border-radius: 10px;
  }
}
</style>
