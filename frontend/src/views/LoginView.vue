<template>
  <div class="page" :class="{ 'page--preview-open': previewOpen }" @keydown.enter.prevent="onSubmit">
    <div class="bg-grid" aria-hidden="true" />
    <div class="bg-shape bg-shape--left" aria-hidden="true" />
    <div class="bg-shape bg-shape--right" aria-hidden="true" />
    <div class="bg-orbit bg-orbit--one" aria-hidden="true" />
    <div class="bg-orbit bg-orbit--two" aria-hidden="true" />

    <div class="page-container">
      <section class="hero">
        <p class="hero-kicker">BUS FLEET CONSOLE</p>
        <h1>
          <span>哈尔滨工务段</span>
          <span>汽车管理信息系统</span>
        </h1>
        <p class="hero-sub">
          统一管理车辆、驾驶员、油耗与维保，形成可追溯、可审计、可分析的公务车业务闭环。
        </p>
        <div class="hero-tags">
          <span>智能调度</span>
          <span>闭环台账</span>
          <span>风险预警</span>
        </div>
        <div class="hero-metrics">
          <div class="metric">
            <div class="metric-v">7 x 24</div>
            <div class="metric-k">运营值守</div>
          </div>
          <div class="metric">
            <div class="metric-v">全流程</div>
            <div class="metric-k">申请到归档</div>
          </div>
          <div class="metric">
            <div class="metric-v">多维度</div>
            <div class="metric-k">统计分析</div>
          </div>
        </div>

      </section>

      <section class="login-card">
        <div class="card-hd">
          <h2>账号登录</h2>
          <p>请输入您的业务账号并完成滑块校验</p>
        </div>

        <div class="toast" v-if="toast">{{ toast }}</div>

        <form class="form" @submit.prevent="onSubmit">
          <div class="field">
            <label>用户名</label>
            <input v-model.trim="username" type="text" autocomplete="username" placeholder="请输入用户名" />
          </div>
          <div class="field">
            <label>密码</label>
            <input
              v-model="password"
              type="password"
              autocomplete="current-password"
              placeholder="请输入密码"
            />
          </div>
          <p class="pwd-hint">密码需为 8-16 位，含大小写字母、数字和特殊字符。</p>

          <div class="slider-wrap">
            <SliderVerify v-if="sliderSessionId" :session-id="sliderSessionId" @ready="sliderReady = true" />
          </div>

          <button type="button" class="preview-btn" @click="openPreview">先看一眼功能预览</button>
          <button type="submit" class="cta-btn" :disabled="loading">
            <span>{{ loading ? '登录中...' : '进入系统' }}</span>
          </button>
          <p class="cta-note">登录后可立即查看车辆态势、审批节点与费用动态。</p>
        </form>
      </section>
    </div>

    <div v-if="previewOpen" class="preview-mask" aria-hidden="true" @click="closePreview" />
    <section
      v-if="previewOpen"
      class="preview-panel"
      role="dialog"
      aria-modal="true"
      aria-label="功能预览"
    >
      <header class="preview-hd">
        <h3>功能预览</h3>
        <button type="button" class="preview-close" @click="closePreview">关闭</button>
      </header>

      <div
        class="preview-carousel"
        :style="{ transform: `translateX(-${previewIndex * 100}%)` }"
        @touchstart.passive="onPreviewTouchStart"
        @touchend.passive="onPreviewTouchEnd"
      >
        <article class="preview-card">
          <p class="preview-card__kpi">车辆总览</p>
          <p class="preview-card__v">126 台</p>
          <p class="preview-card__desc">在库 121 · 维修 5 · 本日待派 18</p>
        </article>
        <article class="preview-card">
          <p class="preview-card__kpi">审批进度</p>
          <p class="preview-card__v">9 单</p>
          <p class="preview-card__desc">待审批 4 · 待派车 3 · 待归档 2</p>
        </article>
        <article class="preview-card">
          <p class="preview-card__kpi">运营动态</p>
          <p class="preview-card__v">今日 38 笔</p>
          <p class="preview-card__desc">油卡使用 24 · 维修保养 6 · 通行动态 8</p>
        </article>
      </div>

      <div class="preview-progress" aria-hidden="true">
        <span
          v-for="(_, idx) in 3"
          :key="idx"
          class="preview-progress__dot"
          :class="{ 'preview-progress__dot--active': idx === previewIndex }"
        />
      </div>

      <footer class="preview-ft">
        <button type="button" class="preview-enter" @click="closePreview">立即登录查看完整功能</button>
      </footer>
    </section>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import * as authApi from '@/api/auth'
import SliderVerify from '@/components/SliderVerify.vue'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()

const username = ref('')
const password = ref('')
const sliderSessionId = ref('')
const sliderReady = ref(false)
const loading = ref(false)
const toast = ref('')
const previewOpen = ref(false)
const previewIndex = ref(0)
let previewTimer: ReturnType<typeof setInterval> | null = null
let previewTouchStartX = 0

const pwdRegex = /^(?=.*[0-9])(?=.*[A-Z])(?=.*[a-z])(?=.*[^a-zA-Z0-9]).{8,16}$/

function showToast(msg: string) {
  toast.value = msg
  window.setTimeout(() => {
    toast.value = ''
  }, 2200)
}

function openPreview() {
  previewOpen.value = true
  previewIndex.value = 0
  if (previewTimer) clearInterval(previewTimer)
  previewTimer = setInterval(() => {
    previewIndex.value = (previewIndex.value + 1) % 3
  }, 2200)
}

function closePreview() {
  previewOpen.value = false
  if (previewTimer) {
    clearInterval(previewTimer)
    previewTimer = null
  }
}

function onPreviewTouchStart(e: TouchEvent) {
  previewTouchStartX = e.changedTouches[0]?.clientX ?? 0
}

function onPreviewTouchEnd(e: TouchEvent) {
  const endX = e.changedTouches[0]?.clientX ?? 0
  const delta = endX - previewTouchStartX
  if (Math.abs(delta) < 52) return
  if (delta > 0) previewIndex.value = Math.max(previewIndex.value - 1, 0)
  else previewIndex.value = Math.min(previewIndex.value + 1, 2)
}

onMounted(async () => {
  try {
    const res = await authApi.startSliderSession()
    sliderSessionId.value = res.session_id
    sliderReady.value = false
  } catch {
    showToast('初始化滑块失败，请刷新页面')
  }

})

onBeforeUnmount(() => {
  if (previewTimer) clearInterval(previewTimer)
})

async function onSubmit() {
  if (!sliderReady.value) {
    showToast('请拖动滑块验证')
    return
  }
  if (!username.value || !password.value) {
    showToast('请输入用户名密码')
    return
  }
  if (!pwdRegex.test(password.value)) {
    showToast('密码不符合安全规范，请联系管理员修改密码，否则无法登陆')
    return
  }

  loading.value = true
  try {
    await user.login({
      username: username.value,
      password: password.value,
      slider_session_id: sliderSessionId.value,
    })
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/app/dashboard'
    await router.replace(redirect || '/app/dashboard')
  } catch (e) {
    if (axios.isAxiosError(e)) {
      const status = e.response?.status
      const detail = formatAxiosDetail(e.response?.data)
      if (status === 423) {
        showToast(detail || '您连续输入错误次数过多，您的用户已被锁定十分钟')
      } else if (status === 401) {
        showToast(detail || '用户名密码错误,如果连续错误超过3次，用户将被锁定')
      } else if (status === 400) {
        showToast(detail || '请求参数错误')
      } else {
        showToast('登录失败，请稍后重试')
      }
    } else {
      showToast('登录失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}

function formatAxiosDetail(data: unknown): string | undefined {
  if (!data || typeof data !== 'object') return undefined
  const detail = (data as { detail?: unknown }).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === 'object' && 'msg' in item) {
          return String((item as { msg: unknown }).msg)
        }
        try {
          return JSON.stringify(item)
        } catch {
          return String(item)
        }
      })
      .join('；')
  }
  return undefined
}
</script>

<style scoped>
.page {
  position: relative;
  min-height: 100%;
  min-height: 100dvh;
  margin: 0;
  padding: clamp(28px, 5vw, 56px);
  padding-left: max(clamp(28px, 5vw, 56px), env(safe-area-inset-left));
  padding-right: max(clamp(28px, 5vw, 56px), env(safe-area-inset-right));
  padding-bottom: max(clamp(28px, 5vw, 56px), env(safe-area-inset-bottom));
  box-sizing: border-box;
  color: var(--cl-near-black);
  background:
    radial-gradient(circle at 10% 12%, rgba(201, 100, 66, 0.14), transparent 44%),
    radial-gradient(circle at 88% 85%, rgba(94, 93, 89, 0.12), transparent 38%),
    linear-gradient(145deg, #f8f6ef 0%, #f3f0e5 48%, #ece8db 100%);
  font-family:
    'PingFang SC',
    'Hiragino Sans GB',
    'Microsoft YaHei',
    'Noto Sans CJK SC',
    'Source Han Sans SC',
    sans-serif;
  text-rendering: optimizeLegibility;
  font-feature-settings: 'kern' 1;
  overflow-x: hidden;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  touch-action: auto;
}

.page--preview-open {
  overflow: hidden;
}

.bg-grid {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  opacity: 0.25;
  background-image:
    linear-gradient(rgba(127, 118, 102, 0.12) 1px, transparent 1px),
    linear-gradient(90deg, rgba(127, 118, 102, 0.12) 1px, transparent 1px);
  background-size: 30px 30px;
  mask-image: radial-gradient(circle at center, black 32%, transparent 86%);
}

.page-container {
  position: relative;
  z-index: 2;
  margin: 0 auto;
  max-width: 1120px;
  min-height: calc(100vh - clamp(56px, 10vw, 112px));
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(340px, 420px);
  gap: clamp(24px, 4vw, 48px);
  align-items: center;
  padding-bottom: 14px;
}

.hero {
  padding: clamp(10px, 2vw, 26px);
  animation: hero-fade-in 0.7s ease;
}

.hero-kicker {
  margin: 0;
  color: var(--cl-olive);
  letter-spacing: 0.34em;
  font-size: 0.66rem;
  font-weight: 600;
  text-transform: uppercase;
  transform: scaleX(0.92);
  transform-origin: left center;
  opacity: 0.92;
}

h1 {
  margin: 12px 0 0;
  font-size: clamp(1.7rem, 3.4vw, 2.75rem);
  font-weight: 600;
  line-height: 1.16;
  letter-spacing: 0.02em;
  font-family:
    'STSong',
    'Songti SC',
    'Noto Serif CJK SC',
    'Source Han Serif SC',
    Georgia,
    serif;
  color: var(--cl-near-black);
  text-wrap: balance;
}

h1 span {
  display: block;
}

h1 span:first-child {
  font-size: 0.78em;
  letter-spacing: 0.08em;
  color: #4a4945;
}

h1 span:last-child {
  margin-top: 4px;
}

.hero-sub {
  margin: 16px 0 0;
  max-width: 600px;
  color: var(--cl-charcoal);
  font-size: 0.97rem;
  line-height: 1.9;
  letter-spacing: 0.01em;
}

.hero-tags {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hero-tags span {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 11px;
  border-radius: 999px;
  border: 1px solid rgba(201, 100, 66, 0.26);
  background: rgba(255, 255, 255, 0.48);
  color: #5c5850;
  font-size: 0.75rem;
  letter-spacing: 0.06em;
}

.hero-metrics {
  margin-top: 26px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.metric {
  border: 1px solid rgba(201, 100, 66, 0.2);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(250, 249, 245, 0.78), rgba(250, 249, 245, 0.62));
  backdrop-filter: blur(4px);
  padding: 12px 12px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
}

.metric-v {
  font-family:
    'STSong',
    'Songti SC',
    'Noto Serif CJK SC',
    Georgia,
    serif;
  font-size: 1.12rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--cl-near-black);
}

.metric-k {
  margin-top: 4px;
  color: var(--cl-olive);
  font-size: 0.76rem;
  letter-spacing: 0.05em;
}

.login-card {
  box-sizing: border-box;
  border-radius: 22px;
  border: 1px solid rgba(232, 230, 220, 0.86);
  background: rgba(250, 249, 245, 0.94);
  box-shadow:
    rgba(34, 25, 18, 0.08) 0px 20px 52px,
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  padding: clamp(20px, 2.2vw, 28px);
  animation: card-pop-in 0.65s cubic-bezier(0.2, 0.9, 0.32, 1);
}

.card-hd h2 {
  margin: 0;
  font-family:
    'STSong',
    'Songti SC',
    'Noto Serif CJK SC',
    'Source Han Serif SC',
    Georgia,
    serif;
  font-size: 1.42rem;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.card-hd p {
  margin: 8px 0 0;
  color: var(--cl-olive);
  font-size: 0.82rem;
  letter-spacing: 0.03em;
}

.pwd-hint {
  margin: -2px 0 0;
  color: #7b756b;
  font-size: 0.75rem;
  line-height: 1.45;
}

.form {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.preview-btn {
  border: 1px dashed rgba(142, 132, 109, 0.62);
  background: rgba(255, 255, 255, 0.65);
  color: #5f5a50;
  box-shadow: none;
  font-size: 0.84rem;
  letter-spacing: 0.06em;
}

.preview-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.92);
  box-shadow: rgba(90, 83, 73, 0.16) 0 8px 16px -12px;
}

.field {
  display: grid;
  gap: 7px;
}

.field label {
  color: var(--cl-charcoal);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.06em;
}

input {
  width: 100%;
  box-sizing: border-box;
  height: 48px;
  line-height: 1.25;
  margin: 0;
  padding: 0 14px;
  background: var(--cl-white);
  border-radius: 12px;
  border: 1px solid #ddd6c6;
  font-size: 0.98rem;
  font-weight: 500;
  letter-spacing: 0.01em;
  color: var(--cl-near-black);
  transition:
    border-color 0.16s ease,
    box-shadow 0.16s ease,
    background-color 0.16s ease;
}

.slider-wrap {
  margin-top: 2px;
}

input::placeholder {
  color: var(--cl-stone);
}

input:focus {
  outline: none;
  border-color: var(--cl-focus);
  box-shadow: 0 0 0 3px rgba(201, 100, 66, 0.2);
  background: #fffdf9;
}

.form button {
  cursor: pointer;
  width: 100%;
  height: 48px;
  margin-top: 4px;
  padding: 0;
  background: linear-gradient(135deg, #bf5631, #c96442 58%, #d37b5d);
  border-radius: 12px;
  border: 0;
  box-shadow: rgba(201, 100, 66, 0.48) 0px 10px 24px -10px;
  font-size: 0.98rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--cl-ivory);
  transition:
    transform 0.15s ease,
    filter 0.15s ease,
    box-shadow 0.15s ease;
}

.cta-btn {
  position: relative;
  overflow: hidden;
  isolation: isolate;
}

.cta-btn::before {
  content: '';
  position: absolute;
  inset: -1px;
  z-index: -1;
  border-radius: inherit;
  background: linear-gradient(120deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.45), rgba(255, 255, 255, 0.08));
  transform: translateX(-120%);
  animation: cta-sweep 2.8s ease-in-out infinite;
}

.cta-btn::after {
  content: '';
  position: absolute;
  inset: -8px;
  z-index: -2;
  border-radius: 18px;
  background: radial-gradient(circle, rgba(201, 100, 66, 0.32), transparent 62%);
  animation: cta-glow 2.1s ease-in-out infinite;
}

.form button:hover:not(:disabled) {
  filter: brightness(1.04);
  transform: translateY(-1px);
  box-shadow: rgba(201, 100, 66, 0.6) 0px 14px 28px -12px;
}

.form button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.toast {
  margin-top: 14px;
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(181, 51, 51, 0.08);
  border: 1px solid rgba(181, 51, 51, 0.35);
  color: var(--cl-error);
  font-size: 0.84rem;
  line-height: 1.65;
  letter-spacing: 0.01em;
  animation: toast-in 0.24s ease;
}

.cta-note {
  margin: 7px 0 0;
  color: #7a7368;
  font-size: 0.75rem;
  text-align: center;
  letter-spacing: 0.03em;
}

.preview-mask {
  position: fixed;
  inset: 0;
  z-index: 20;
  background: rgba(20, 18, 16, 0.38);
  backdrop-filter: blur(4px);
}

.preview-panel {
  position: fixed;
  z-index: 22;
  right: clamp(10px, 3vw, 28px);
  bottom: clamp(10px, 3vw, 28px);
  width: min(460px, calc(100vw - 20px));
  border: 1px solid rgba(229, 221, 204, 0.92);
  border-radius: 18px;
  background: rgba(252, 250, 245, 0.97);
  box-shadow:
    rgba(27, 20, 14, 0.22) 0 24px 48px -18px,
    inset 0 1px 0 rgba(255, 255, 255, 0.82);
  padding: 14px 14px 12px;
  animation: preview-in 0.24s ease;
}

.preview-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.preview-hd h3 {
  margin: 0;
  font-size: 1rem;
  letter-spacing: 0.03em;
}

.preview-close {
  width: auto;
  height: 30px;
  margin: 0;
  padding: 0 10px;
  border-radius: 10px;
  border: 1px solid rgba(164, 152, 129, 0.5);
  background: rgba(255, 255, 255, 0.75);
  box-shadow: none;
  color: #5e594f;
  font-size: 0.78rem;
}

.preview-carousel {
  margin-top: 10px;
  display: flex;
  gap: 10px;
  transition: transform 0.28s ease;
  touch-action: pan-x;
}

.preview-card {
  min-width: 100%;
  border-radius: 14px;
  border: 1px solid rgba(201, 100, 66, 0.24);
  background: linear-gradient(150deg, rgba(255, 255, 255, 0.95), rgba(248, 238, 225, 0.72));
  padding: 14px;
}

.preview-progress {
  margin-top: 10px;
  display: flex;
  justify-content: center;
  gap: 6px;
}

.preview-progress__dot {
  width: 18px;
  height: 4px;
  border-radius: 999px;
  background: rgba(155, 146, 127, 0.35);
  transition: all 0.2s ease;
}

.preview-progress__dot--active {
  width: 30px;
  background: rgba(201, 100, 66, 0.65);
}

.preview-card__kpi {
  margin: 0;
  color: #70695f;
  font-size: 0.74rem;
  letter-spacing: 0.1em;
}

.preview-card__v {
  margin: 6px 0 0;
  color: #332f29;
  font-size: 1.38rem;
  font-weight: 700;
}

.preview-card__desc {
  margin: 7px 0 0;
  color: #575248;
  font-size: 0.82rem;
  line-height: 1.6;
}

.preview-ft {
  margin-top: 10px;
}

.preview-enter {
  margin: 0;
  height: 42px;
  font-size: 0.85rem;
}

.bg-shape {
  position: absolute;
  z-index: 1;
  border-radius: 50%;
  pointer-events: none;
}

.bg-shape--left {
  width: 360px;
  height: 360px;
  left: -140px;
  top: -120px;
  background: radial-gradient(circle, rgba(201, 100, 66, 0.22), rgba(201, 100, 66, 0));
  animation: drift-left 12s ease-in-out infinite;
}

.bg-shape--right {
  width: 420px;
  height: 420px;
  right: -130px;
  bottom: -180px;
  background: radial-gradient(circle, rgba(94, 93, 89, 0.2), rgba(94, 93, 89, 0));
  animation: drift-right 16s ease-in-out infinite;
}

.bg-orbit {
  position: absolute;
  z-index: 1;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  pointer-events: none;
  background: rgba(201, 100, 66, 0.38);
  filter: blur(0.2px);
}

.bg-orbit--one {
  top: 22%;
  left: 26%;
  animation: orbit-a 10s linear infinite;
}

.bg-orbit--two {
  right: 20%;
  bottom: 18%;
  background: rgba(110, 108, 101, 0.35);
  animation: orbit-b 13s linear infinite;
}

@media (max-width: 980px) {
  .page {
    padding: 18px;
    padding-left: max(18px, env(safe-area-inset-left));
    padding-right: max(18px, env(safe-area-inset-right));
    padding-bottom: max(18px, env(safe-area-inset-bottom));
  }

  .page-container {
    min-height: auto;
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .hero {
    padding: 8px 4px;
  }

  .hero-metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }

  .metric {
    padding: 10px 8px;
  }

  .metric-v {
    font-size: 1rem;
  }

  .metric-k {
    font-size: 0.72rem;
  }

  .login-card {
    width: min(100%, 560px);
    max-width: calc(100vw - 36px);
    margin-left: auto;
    margin-right: auto;
  }
}

/* 手机竖屏：避免输入框聚焦时 iOS 自动放大、保证可滚动与触控面积 */
@media (max-width: 640px) {
  .page {
    min-height: 100svh;
    padding-top: max(16px, env(safe-area-inset-top));
    overflow-y: auto;
    overflow-x: hidden;
    touch-action: pan-y;
  }

  .page-container {
    gap: 14px;
    align-items: start;
    align-content: start;
    padding-bottom: max(24px, env(safe-area-inset-bottom));
  }

  h1 {
    font-size: clamp(1.45rem, 6.5vw, 1.85rem);
  }

  .hero-sub {
    font-size: 0.9rem;
    line-height: 1.75;
  }

  .hero-metrics {
    margin-top: 18px;
    grid-template-columns: 1fr;
    gap: 0;
    border: 1px solid rgba(201, 100, 66, 0.22);
    border-radius: 14px;
    overflow: hidden;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.62), rgba(248, 242, 232, 0.5));
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.78);
  }

  .hero-tags {
    margin-top: 12px;
    gap: 6px;
  }

  .hero-tags span {
    height: 26px;
    font-size: 0.72rem;
    letter-spacing: 0.04em;
  }

  .login-card {
    width: min(100%, 500px);
    max-width: calc(100vw - 20px);
    border-radius: 18px;
    padding: 18px 16px;
    backdrop-filter: blur(5px);
  }

  .metric {
    border: 0;
    border-bottom: 1px solid rgba(201, 100, 66, 0.18);
    border-radius: 0;
    background: transparent;
    box-shadow: none;
    padding: 11px 12px;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;
  }

  .metric:last-child {
    border-bottom: 0;
  }

  .metric-v {
    font-size: 1.02rem;
  }

  .metric-k {
    margin-top: 0;
    font-size: 0.76rem;
    text-align: right;
  }

  .card-hd h2 {
    font-size: 1.28rem;
  }

  input {
    height: 48px;
    font-size: 16px;
  }

  button {
    min-height: 48px;
    font-size: 16px;
  }

  .toast {
    font-size: 0.8rem;
  }

  .bg-grid {
    opacity: 0.15;
    background-size: 22px 22px;
  }

  .preview-panel {
    left: 10px;
    right: 10px;
    bottom: max(10px, env(safe-area-inset-bottom));
    width: auto;
    padding: 12px 12px 10px;
    border-radius: 16px;
  }

  .preview-carousel {
    gap: 8px;
  }

  .preview-card {
    padding: 12px;
  }

  .preview-card__v {
    font-size: 1.22rem;
  }
}

@media (max-width: 420px) {
  .hero-sub {
    font-size: 0.87rem;
  }

  .card-hd p {
    font-size: 0.78rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero,
  .login-card,
  .toast,
  .cta-btn::before,
  .cta-btn::after,
  .bg-shape--left,
  .bg-shape--right,
  .bg-orbit--one,
  .bg-orbit--two {
    animation: none !important;
  }
}

@keyframes hero-fade-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes card-pop-in {
  from {
    opacity: 0;
    transform: translateY(12px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes drift-left {
  0%,
  100% {
    transform: translate(0, 0) scale(1);
  }
  50% {
    transform: translate(16px, 10px) scale(1.06);
  }
}

@keyframes drift-right {
  0%,
  100% {
    transform: translate(0, 0) scale(1);
  }
  50% {
    transform: translate(-14px, -8px) scale(1.05);
  }
}

@keyframes orbit-a {
  0% {
    transform: translate(0, 0);
  }
  25% {
    transform: translate(18px, -14px);
  }
  50% {
    transform: translate(4px, -28px);
  }
  75% {
    transform: translate(-12px, -10px);
  }
  100% {
    transform: translate(0, 0);
  }
}

@keyframes orbit-b {
  0% {
    transform: translate(0, 0);
  }
  30% {
    transform: translate(-14px, 10px);
  }
  60% {
    transform: translate(-4px, 24px);
  }
  100% {
    transform: translate(0, 0);
  }
}

@keyframes cta-sweep {
  0% {
    transform: translateX(-120%);
  }
  45% {
    transform: translateX(120%);
  }
  100% {
    transform: translateX(120%);
  }
}

@keyframes cta-glow {
  0%,
  100% {
    opacity: 0.42;
    transform: scale(0.96);
  }
  50% {
    opacity: 0.75;
    transform: scale(1.03);
  }
}

@keyframes preview-in {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
