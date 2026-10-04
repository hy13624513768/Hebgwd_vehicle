<template>
  <main class="login-page" @keydown.enter.prevent="onSubmit">
    <div class="motion-layer" aria-hidden="true">
      <span class="ambient ambient--one" />
      <span class="ambient ambient--two" />
      <span class="pulse-wave pulse-wave--one" />
      <span class="pulse-wave pulse-wave--two" />
      <span class="screen-pulse screen-pulse--one" />
      <span class="screen-pulse screen-pulse--two" />
      <span class="screen-pulse screen-pulse--three" />
      <span class="energy-ribbon energy-ribbon--one" />
      <span class="energy-ribbon energy-ribbon--two" />
      <span class="route-line route-line--one"><i /></span>
      <span class="route-line route-line--two"><i /></span>
      <span class="motion-dot motion-dot--one" />
      <span class="motion-dot motion-dot--two" />
      <span class="motion-dot motion-dot--three" />
      <span class="spark-field">
        <i v-for="index in 12" :key="`spark-${index}`" />
      </span>
      <span class="particle-flow">
        <i v-for="index in 18" :key="`particle-${index}`" />
      </span>
    </div>

    <div class="login-shell">
      <header class="brand">
        <button
          type="button"
          class="brand__logo"
          :class="{ 'brand__logo--escaping': logoEscaping }"
          :style="logoEscapeStyle"
          aria-label="点击品牌标志查看彩蛋"
          @click="runLogoEasterEgg"
        >
          <span class="brand__logo-ring" />
          <span class="brand__logo-surface">
            <img :src="logoUrl" alt="" />
          </span>
        </button>
        <p class="brand__eyebrow">哈尔滨工务段</p>
        <h1>汽车管理信息系统</h1>
        <p class="brand__desc">车辆、驾驶员、油耗与维保业务统一入口</p>
        <span class="brand__rule" aria-hidden="true" />
      </header>

      <section class="login-card" aria-labelledby="login-title">
        <div class="login-card__head">
          <div>
            <h2 id="login-title">欢迎登录</h2>
            <p>请输入您的业务账号</p>
          </div>
          <span class="login-card__mark" aria-hidden="true">车辆管理</span>
        </div>

        <div v-if="toast" class="toast" role="alert" aria-live="polite">{{ toast }}</div>

        <form class="login-form" @submit.prevent="onSubmit">
          <label class="field">
            <span>用户名</span>
            <span class="field__control">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8c.7-3.2 3.4-5 7-5s6.3 1.8 7 5" />
              </svg>
              <input
                v-model.trim="username"
                type="text"
                autocomplete="username"
                placeholder="请输入用户名"
                enterkeyhint="next"
              />
            </span>
          </label>

          <label class="field">
            <span>密码</span>
            <span class="field__control">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <rect x="5" y="10" width="14" height="10" rx="2" />
                <path d="M8 10V7a4 4 0 0 1 8 0v3" />
              </svg>
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="请输入密码"
                enterkeyhint="go"
              />
              <button
                type="button"
                class="password-toggle"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                {{ showPassword ? '隐藏' : '显示' }}
              </button>
            </span>
          </label>

          <p class="password-hint">请输入当前账户密码</p>

          <button type="submit" class="submit-btn" :disabled="loading">
            <span v-if="loading" class="loading-dot" aria-hidden="true" />
            <span>{{ loading ? '正在登录' : '进入系统' }}</span>
            <svg v-if="!loading" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6" /></svg>
          </button>
        </form>
      </section>
    </div>

    <canvas
      v-show="fireworksActive"
      ref="fireworksCanvas"
      class="fireworks-canvas"
      aria-hidden="true"
    />

    <Transition name="easter-egg">
      <div v-if="showEasterEgg" class="easter-egg" role="status" aria-live="polite">
        <span aria-hidden="true">✦</span>
        <strong>上班快乐！</strong>
        <span aria-hidden="true">✦</span>
      </div>
    </Transition>
  </main>
</template>

<script setup lang="ts">
import axios from 'axios'
import { onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import logoUrl from '@/assets/harbin-railway-logo.jpg'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const toast = ref('')
const logoEscaping = ref(false)
const showEasterEgg = ref(false)
const fireworksActive = ref(false)
const fireworksCanvas = ref<HTMLCanvasElement | null>(null)
const logoEscapeStyle = ref<Record<string, string>>({})
let logoTimer: number | undefined
let eggTimer: number | undefined
let fireworkAnimationFrame: number | undefined

type TrailPoint = { x: number; y: number }
type Rocket = {
  startX: number
  startY: number
  targetX: number
  targetY: number
  delay: number
  duration: number
  hue: number
  curve: number
  exploded: boolean
  trail: TrailPoint[]
}
type Spark = {
  x: number
  y: number
  vx: number
  vy: number
  gravity: number
  drag: number
  life: number
  decay: number
  hue: number
  brightness: number
  size: number
  trail: TrailPoint[]
}
type Flash = { x: number; y: number; hue: number; life: number }

function playFireworks() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const canvas = fireworksCanvas.value
  if (!canvas) return

  if (fireworkAnimationFrame !== undefined) cancelAnimationFrame(fireworkAnimationFrame)
  const maybeContext = canvas.getContext('2d')
  if (!maybeContext) return
  const context: CanvasRenderingContext2D = maybeContext

  const width = window.innerWidth
  const height = window.innerHeight
  const ratio = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = Math.round(width * ratio)
  canvas.height = Math.round(height * ratio)
  canvas.style.width = `${width}px`
  canvas.style.height = `${height}px`
  context.setTransform(ratio, 0, 0, ratio, 0, 0)
  fireworksActive.value = true

  const startedAt = performance.now()
  const hues = [8, 203, 145, 34, 338]
  const rockets: Rocket[] = Array.from({ length: 5 }, (_, index) => ({
    startX: width * (0.2 + Math.random() * 0.6),
    startY: height + 28,
    targetX: width * (0.13 + Math.random() * 0.74),
    targetY: height * (0.13 + Math.random() * 0.34),
    delay: index * 390 + Math.random() * 130,
    duration: 760 + Math.random() * 300,
    hue: hues[index % hues.length],
    curve: (Math.random() - 0.5) * Math.min(92, width * 0.18),
    exploded: false,
    trail: [],
  }))
  const sparks: Spark[] = []
  const flashes: Flash[] = []
  let previousTime = startedAt

  function explode(rocket: Rocket) {
    flashes.push({ x: rocket.targetX, y: rocket.targetY, hue: rocket.hue, life: 1 })
    const count = width < 600 ? 72 : 92
    for (let index = 0; index < count; index += 1) {
      const angle = (Math.PI * 2 * index) / count + (Math.random() - 0.5) * 0.09
      const speed = 1.8 + Math.pow(Math.random(), 0.42) * 5.3
      sparks.push({
        x: rocket.targetX,
        y: rocket.targetY,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        gravity: 0.035 + Math.random() * 0.018,
        drag: 0.978 + Math.random() * 0.01,
        life: 1,
        decay: 0.007 + Math.random() * 0.005,
        hue: (rocket.hue + (Math.random() - 0.5) * 28 + 360) % 360,
        brightness: 58 + Math.random() * 28,
        size: 1.1 + Math.random() * 1.5,
        trail: [],
      })
    }
  }

  function drawTrail(points: TrailPoint[], color: string, widthPx: number) {
    if (points.length < 2) return
    context.beginPath()
    context.moveTo(points[0].x, points[0].y)
    for (let index = 1; index < points.length; index += 1) {
      context.lineTo(points[index].x, points[index].y)
    }
    context.strokeStyle = color
    context.lineWidth = widthPx
    context.lineCap = 'round'
    context.stroke()
  }

  function animate(now: number) {
    const step = Math.min(2, Math.max(0.45, (now - previousTime) / 16.67))
    previousTime = now
    context.clearRect(0, 0, width, height)
    context.globalCompositeOperation = 'lighter'

    rockets.forEach((rocket) => {
      const elapsed = now - startedAt - rocket.delay
      if (elapsed < 0 || rocket.exploded) return
      const progress = Math.min(1, elapsed / rocket.duration)
      const eased = 1 - Math.pow(1 - progress, 3)
      const x = rocket.startX + (rocket.targetX - rocket.startX) * eased + Math.sin(progress * Math.PI) * rocket.curve
      const y = rocket.startY + (rocket.targetY - rocket.startY) * eased
      rocket.trail.unshift({ x, y })
      if (rocket.trail.length > 16) rocket.trail.pop()

      drawTrail(rocket.trail, `hsla(${rocket.hue}, 100%, 61%, ${0.3 + progress * 0.55})`, 2.2)
      context.beginPath()
      context.arc(x, y, 2.6, 0, Math.PI * 2)
      context.fillStyle = '#fff'
      context.shadowBlur = 15
      context.shadowColor = `hsl(${rocket.hue}, 100%, 58%)`
      context.fill()
      context.shadowBlur = 0

      if (progress >= 1) {
        rocket.exploded = true
        explode(rocket)
      }
    })

    for (let index = sparks.length - 1; index >= 0; index -= 1) {
      const spark = sparks[index]
      spark.trail.unshift({ x: spark.x, y: spark.y })
      if (spark.trail.length > 9) spark.trail.pop()
      spark.vx *= Math.pow(spark.drag, step)
      spark.vy = spark.vy * Math.pow(spark.drag, step) + spark.gravity * step
      spark.x += spark.vx * step
      spark.y += spark.vy * step
      spark.life -= spark.decay * step

      if (spark.life <= 0) {
        sparks.splice(index, 1)
        continue
      }

      const alpha = Math.min(1, spark.life * 1.45)
      drawTrail(spark.trail, `hsla(${spark.hue}, 100%, ${spark.brightness}%, ${alpha * 0.54})`, spark.size)
      context.beginPath()
      context.arc(spark.x, spark.y, spark.size * Math.max(0.42, spark.life), 0, Math.PI * 2)
      context.fillStyle = `hsla(${spark.hue}, 100%, ${spark.brightness}%, ${alpha})`
      context.shadowBlur = 8
      context.shadowColor = `hsla(${spark.hue}, 100%, 65%, ${alpha})`
      context.fill()
      context.shadowBlur = 0
    }

    for (let index = flashes.length - 1; index >= 0; index -= 1) {
      const flash = flashes[index]
      flash.life -= 0.075 * step
      if (flash.life <= 0) {
        flashes.splice(index, 1)
        continue
      }
      const radius = (1 - flash.life) * 46 + 6
      const glow = context.createRadialGradient(flash.x, flash.y, 0, flash.x, flash.y, radius)
      glow.addColorStop(0, `hsla(${flash.hue}, 100%, 96%, ${flash.life})`)
      glow.addColorStop(0.28, `hsla(${flash.hue}, 100%, 65%, ${flash.life * 0.7})`)
      glow.addColorStop(1, `hsla(${flash.hue}, 100%, 50%, 0)`)
      context.fillStyle = glow
      context.fillRect(flash.x - radius, flash.y - radius, radius * 2, radius * 2)
    }

    const pendingRockets = rockets.some((rocket) => !rocket.exploded)
    if (pendingRockets || sparks.length > 0 || flashes.length > 0) {
      fireworkAnimationFrame = requestAnimationFrame(animate)
    } else {
      context.clearRect(0, 0, width, height)
      fireworksActive.value = false
      fireworkAnimationFrame = undefined
    }
  }

  fireworkAnimationFrame = requestAnimationFrame(animate)
}

function runLogoEasterEgg() {
  if (logoEscaping.value) return

  const maxX = Math.min(118, Math.max(54, window.innerWidth * 0.25))
  const maxY = Math.min(78, Math.max(38, window.innerHeight * 0.09))
  const directionX = Math.random() > 0.5 ? 1 : -1
  const directionY = Math.random() > 0.42 ? 1 : -1
  const escapeX = directionX * (maxX * (0.62 + Math.random() * 0.38))
  const escapeY = directionY * (maxY * (0.55 + Math.random() * 0.45))

  logoEscapeStyle.value = {
    '--escape-x': `${escapeX.toFixed(1)}px`,
    '--escape-y': `${escapeY.toFixed(1)}px`,
    '--escape-back-x': `${(escapeX * -0.12).toFixed(1)}px`,
    '--escape-back-y': `${(escapeY * -0.08).toFixed(1)}px`,
    '--escape-return-x': `${(escapeX * 0.82).toFixed(1)}px`,
    '--escape-return-y': `${(escapeY * 0.8).toFixed(1)}px`,
    '--escape-rotate': `${directionX * (15 + Math.random() * 18)}deg`,
  }
  logoEscaping.value = true
  showEasterEgg.value = true
  playFireworks()

  window.clearTimeout(logoTimer)
  window.clearTimeout(eggTimer)
  logoTimer = window.setTimeout(() => {
    logoEscaping.value = false
  }, 1050)
  eggTimer = window.setTimeout(() => {
    showEasterEgg.value = false
  }, 2100)
}

onBeforeUnmount(() => {
  window.clearTimeout(logoTimer)
  window.clearTimeout(eggTimer)
  if (fireworkAnimationFrame !== undefined) cancelAnimationFrame(fireworkAnimationFrame)
})

function showToast(message: string) {
  toast.value = message
  window.setTimeout(() => {
    toast.value = ''
  }, 2200)
}

async function onSubmit() {
  if (loading.value) return
  if (!username.value || !password.value) {
    showToast('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await user.login({ username: username.value, password: password.value })
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/app/dashboard'
    await router.replace(redirect || '/app/dashboard')
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status
      const detail = formatAxiosDetail(error.response?.data)
      if (status === 423) showToast(detail || '账号已锁定，请十分钟后重试')
      else if (status === 401) showToast(detail || '用户名或密码错误')
      else if (status === 400) showToast(detail || '请求参数错误')
      else showToast('登录失败，请稍后重试')
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
  if (!Array.isArray(detail)) return undefined
  return detail
    .map((item) => {
      if (item && typeof item === 'object' && 'msg' in item) return String((item as { msg: unknown }).msg)
      return String(item)
    })
    .join('；')
}
</script>

<style scoped>
.login-page {
  position: relative;
  display: grid;
  width: 100%;
  height: 100vh;
  height: 100dvh;
  min-height: 500px;
  place-items: center;
  overflow: hidden;
  padding:
    max(18px, env(safe-area-inset-top, 0px))
    max(18px, env(safe-area-inset-right, 0px))
    max(18px, env(safe-area-inset-bottom, 0px))
    max(18px, env(safe-area-inset-left, 0px));
  box-sizing: border-box;
  color: var(--cl-near-black, #2c2b28);
  background:
    radial-gradient(circle at 12% 14%, rgba(201, 100, 66, 0.12), transparent 34%),
    radial-gradient(circle at 88% 86%, rgba(107, 101, 88, 0.1), transparent 30%),
    var(--cl-parchment, #f4f0e6);
  isolation: isolate;
}

.motion-layer,
.motion-layer::before {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.motion-dot {
  position: absolute;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(201, 100, 66, 0.46);
  box-shadow: 0 0 0 7px rgba(201, 100, 66, 0.07);
  animation: dot-drift 7s ease-in-out infinite alternate;
}

.motion-dot--one {
  top: 18%;
  left: 14%;
}

.motion-dot--two {
  top: 72%;
  right: 12%;
  width: 5px;
  height: 5px;
  animation-delay: -2.4s;
  animation-duration: 9s;
}

.motion-dot--three {
  right: 20%;
  bottom: 14%;
  width: 4px;
  height: 4px;
  background: rgba(26, 139, 199, 0.38);
  box-shadow: 0 0 0 7px rgba(26, 139, 199, 0.06);
  animation-delay: -4.2s;
  animation-duration: 8s;
}

.motion-layer {
  z-index: -1;
  overflow: hidden;
}

.motion-layer::before {
  content: '';
  opacity: 0.34;
  background-image:
    linear-gradient(rgba(142, 132, 109, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(142, 132, 109, 0.08) 1px, transparent 1px);
  background-size: 32px 32px;
  mask-image: radial-gradient(circle at center, #000 24%, transparent 78%);
}

.ambient {
  position: absolute;
  width: 360px;
  height: 360px;
  border-radius: 50%;
  filter: blur(16px);
  opacity: 0.32;
}

.ambient--one {
  top: -190px;
  left: -120px;
  background: radial-gradient(circle, rgba(201, 100, 66, 0.34), transparent 68%);
  animation: ambient-one 13s ease-in-out infinite alternate;
}

.ambient--two {
  right: -170px;
  bottom: -210px;
  background: radial-gradient(circle, rgba(142, 132, 109, 0.25), transparent 70%);
  animation: ambient-two 16s ease-in-out infinite alternate;
}

.pulse-wave {
  position: absolute;
  width: min(72vw, 560px);
  aspect-ratio: 1;
  border: 1px solid rgba(169, 68, 39, 0.34);
  border-radius: 50%;
  opacity: 0;
  animation: pulse-wave 5.4s ease-out infinite;
}

.pulse-wave::after {
  content: '';
  position: absolute;
  inset: 16%;
  border: 1px solid rgba(23, 109, 152, 0.25);
  border-radius: inherit;
}

.pulse-wave--one {
  top: -19%;
  right: -15%;
}

.pulse-wave--two {
  bottom: -28%;
  left: -17%;
  animation-delay: -2.7s;
}

.screen-pulse {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 110vmax;
  height: 110vmax;
  border: 2px solid rgba(169, 68, 39, 0.34);
  border-radius: 50%;
  opacity: 0;
  box-shadow:
    0 0 22px rgba(169, 68, 39, 0.2),
    inset 0 0 22px rgba(169, 68, 39, 0.14);
  will-change: transform, opacity;
  animation: screen-pulse 7.2s cubic-bezier(0.18, 0.7, 0.22, 1) infinite;
}

.screen-pulse--two {
  border-color: rgba(23, 109, 152, 0.3);
  box-shadow:
    0 0 24px rgba(23, 109, 152, 0.18),
    inset 0 0 24px rgba(23, 109, 152, 0.12);
  animation-delay: -2.4s;
}

.screen-pulse--three {
  border-width: 3px;
  animation-delay: -4.8s;
}

.energy-ribbon {
  position: absolute;
  left: -28%;
  width: 156%;
  height: 78px;
  border-radius: 50%;
  opacity: 0;
  filter: blur(5px);
  background: linear-gradient(
    90deg,
    transparent 4%,
    rgba(169, 68, 39, 0.1) 24%,
    rgba(169, 68, 39, 0.42) 50%,
    rgba(23, 109, 152, 0.2) 72%,
    transparent 96%
  );
  animation: ribbon-breathe 6.4s ease-in-out infinite;
}

.energy-ribbon--one {
  top: 19%;
  transform: rotate(-10deg);
}

.energy-ribbon--two {
  bottom: 16%;
  transform: rotate(8deg);
  animation-delay: -3.2s;
  animation-duration: 7.2s;
}

.spark-field,
.particle-flow {
  position: absolute;
  inset: 0;
  display: block;
}

.spark-field i {
  position: absolute;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #b94f31;
  box-shadow: 0 0 9px 2px rgba(185, 79, 49, 0.48);
  opacity: 0.12;
  animation: spark-blink 3.2s ease-in-out infinite;
}

.spark-field i:nth-child(1) { top: 10%; left: 8%; animation-delay: -0.4s; }
.spark-field i:nth-child(2) { top: 18%; left: 74%; animation-delay: -2.1s; animation-duration: 4.1s; }
.spark-field i:nth-child(3) { top: 29%; left: 91%; animation-delay: -1.2s; }
.spark-field i:nth-child(4) { top: 37%; left: 12%; animation-delay: -2.7s; animation-duration: 3.8s; }
.spark-field i:nth-child(5) { top: 47%; left: 82%; animation-delay: -0.8s; }
.spark-field i:nth-child(6) { top: 57%; left: 6%; animation-delay: -1.9s; animation-duration: 4.4s; }
.spark-field i:nth-child(7) { top: 66%; left: 72%; animation-delay: -3.1s; }
.spark-field i:nth-child(8) { top: 76%; left: 20%; animation-delay: -1.5s; animation-duration: 3.7s; }
.spark-field i:nth-child(9) { top: 87%; left: 88%; animation-delay: -2.4s; }
.spark-field i:nth-child(10) { top: 91%; left: 43%; animation-delay: -0.9s; animation-duration: 4.2s; }
.spark-field i:nth-child(11) { top: 24%; left: 34%; animation-delay: -3.4s; }
.spark-field i:nth-child(12) { top: 69%; left: 94%; animation-delay: -1.1s; animation-duration: 3.9s; }

.spark-field i:nth-child(3n) {
  width: 6px;
  height: 6px;
  background: #176d98;
  box-shadow: 0 0 10px 3px rgba(23, 109, 152, 0.42);
}

.particle-flow {
  inset: -14% -22%;
  overflow: hidden;
  transform: rotate(-9deg);
}

.particle-flow i {
  --flow-y: 10%;
  --flow-duration: 9s;
  --flow-delay: 0s;
  --flow-size: 4px;
  position: absolute;
  top: var(--flow-y);
  left: -8%;
  width: var(--flow-size);
  height: var(--flow-size);
  border-radius: 50%;
  background: rgba(169, 68, 39, 0.86);
  box-shadow: -14px 0 18px rgba(169, 68, 39, 0.38), 0 0 9px rgba(169, 68, 39, 0.58);
  opacity: 0;
  animation: particle-stream var(--flow-duration) linear var(--flow-delay) infinite;
}

.particle-flow i:nth-child(1) { --flow-y: 7%; --flow-duration: 8.2s; --flow-delay: -4.1s; --flow-size: 3px; }
.particle-flow i:nth-child(2) { --flow-y: 13%; --flow-duration: 10.4s; --flow-delay: -8.7s; }
.particle-flow i:nth-child(3) { --flow-y: 19%; --flow-duration: 7.6s; --flow-delay: -1.9s; --flow-size: 6px; }
.particle-flow i:nth-child(4) { --flow-y: 25%; --flow-duration: 11.2s; --flow-delay: -6.3s; --flow-size: 3px; }
.particle-flow i:nth-child(5) { --flow-y: 31%; --flow-duration: 8.8s; --flow-delay: -3.5s; }
.particle-flow i:nth-child(6) { --flow-y: 38%; --flow-duration: 10.8s; --flow-delay: -9.2s; --flow-size: 5px; }
.particle-flow i:nth-child(7) { --flow-y: 44%; --flow-duration: 7.9s; --flow-delay: -5.4s; --flow-size: 3px; }
.particle-flow i:nth-child(8) { --flow-y: 50%; --flow-duration: 9.7s; --flow-delay: -2.2s; }
.particle-flow i:nth-child(9) { --flow-y: 56%; --flow-duration: 11.5s; --flow-delay: -7.8s; --flow-size: 6px; }
.particle-flow i:nth-child(10) { --flow-y: 62%; --flow-duration: 8.5s; --flow-delay: -4.8s; }
.particle-flow i:nth-child(11) { --flow-y: 68%; --flow-duration: 10.2s; --flow-delay: -0.7s; --flow-size: 3px; }
.particle-flow i:nth-child(12) { --flow-y: 74%; --flow-duration: 7.7s; --flow-delay: -6.9s; --flow-size: 5px; }
.particle-flow i:nth-child(13) { --flow-y: 80%; --flow-duration: 9.3s; --flow-delay: -3.1s; }
.particle-flow i:nth-child(14) { --flow-y: 86%; --flow-duration: 10.9s; --flow-delay: -9.8s; --flow-size: 3px; }
.particle-flow i:nth-child(15) { --flow-y: 92%; --flow-duration: 8.1s; --flow-delay: -5.9s; --flow-size: 6px; }
.particle-flow i:nth-child(16) { --flow-y: 16%; --flow-duration: 12s; --flow-delay: -10.6s; --flow-size: 2px; }
.particle-flow i:nth-child(17) { --flow-y: 47%; --flow-duration: 11.7s; --flow-delay: -7.1s; --flow-size: 2px; }
.particle-flow i:nth-child(18) { --flow-y: 83%; --flow-duration: 12.4s; --flow-delay: -2.8s; --flow-size: 2px; }

.particle-flow i:nth-child(3n) {
  background: rgba(23, 109, 152, 0.82);
  box-shadow: -14px 0 18px rgba(23, 109, 152, 0.34), 0 0 10px rgba(23, 109, 152, 0.52);
}

.route-line {
  position: absolute;
  left: -10vw;
  width: 120vw;
  height: 1px;
  overflow: hidden;
  background: linear-gradient(90deg, transparent, rgba(142, 132, 109, 0.18), transparent);
  transform-origin: center;
}

.route-line--one {
  top: 25%;
  transform: rotate(-7deg);
}

.route-line--two {
  bottom: 21%;
  transform: rotate(6deg);
  opacity: 0.68;
}

.route-line i {
  position: absolute;
  top: -2px;
  left: 0;
  width: 64px;
  height: 5px;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, rgba(201, 100, 66, 0.72), transparent);
  animation: route-run 8s linear infinite;
}

.route-line--two i {
  animation-delay: -3.6s;
  animation-duration: 10s;
}

.login-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  justify-items: center;
  gap: 20px;
  width: min(420px, 100%);
}

.brand {
  width: 100%;
  text-align: center;
  animation: brand-enter 0.62s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.brand__logo {
  position: relative;
  display: grid;
  width: 76px;
  height: 76px;
  margin: 0 auto 12px;
  place-items: center;
  padding: 0;
  border: 0;
  outline: 0;
  background: transparent;
  filter: drop-shadow(0 8px 14px rgba(79, 68, 58, 0.08));
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.brand__logo:focus-visible {
  border-radius: 25px;
  box-shadow: 0 0 0 4px rgba(201, 100, 66, 0.2);
}

.brand__logo--escaping {
  z-index: 5;
  animation: logo-escape 1.05s cubic-bezier(0.2, 0.84, 0.28, 1) both;
}

.brand__logo-ring {
  position: absolute;
  inset: 0;
  border: 1px solid rgba(201, 100, 66, 0.28);
  border-radius: 24px;
  animation: logo-ring 2.8s ease-in-out infinite;
}

.brand__logo-ring::after {
  content: '';
  position: absolute;
  inset: 7px;
  border: 1px solid rgba(26, 139, 199, 0.16);
  border-radius: 19px;
}

.brand__logo-surface {
  position: relative;
  display: grid;
  width: 62px;
  height: 62px;
  place-items: center;
  overflow: hidden;
  border: 1px solid rgba(142, 132, 109, 0.18);
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 10px 24px rgba(66, 58, 50, 0.12), inset 0 1px 0 #fff;
  will-change: transform;
  animation: logo-bounce 3.8s cubic-bezier(0.42, 0, 0.25, 1) infinite;
}

.brand__logo-surface::after {
  content: '';
  position: absolute;
  inset: -18% auto -18% -45%;
  width: 25%;
  transform: rotate(17deg);
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.88), transparent);
  animation: logo-sheen 4.2s ease-in-out infinite;
}

.brand__logo-surface img {
  display: block;
  width: 53px;
  height: 53px;
  object-fit: contain;
  mix-blend-mode: multiply;
}

.brand__eyebrow {
  margin: 0;
  color: var(--cl-terracotta, #c96442);
  font-size: 0.76rem;
  font-weight: 750;
  letter-spacing: 0.18em;
}

.brand h1 {
  margin: 9px 0 0;
  color: var(--cl-near-black, #2c2b28);
  font-family: 'Songti SC', 'STSong', Georgia, serif;
  font-size: clamp(1.8rem, 5vw, 2.35rem);
  font-weight: 600;
  line-height: 1.16;
  letter-spacing: 0.035em;
}

.brand__desc {
  margin: 8px 0 0;
  color: var(--cl-olive, #6b6558);
  font-size: 0.82rem;
  line-height: 1.5;
}

.brand__rule {
  display: block;
  width: 54px;
  height: 3px;
  margin: 13px auto 0;
  border-radius: 999px;
  background: linear-gradient(90deg, #c96442, #dda083);
  animation: rule-breathe 2.8s ease-in-out infinite alternate;
}

.login-card {
  position: relative;
  width: 100%;
  min-width: 0;
  padding: 25px;
  overflow: hidden;
  border: 1px solid var(--cl-border-cream, rgba(142, 132, 109, 0.24));
  border-radius: 18px;
  background: rgba(255, 253, 249, 0.96);
  box-shadow: 0 16px 42px rgba(50, 44, 38, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.86);
  box-sizing: border-box;
  animation: card-enter 0.66s 0.06s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.login-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 3px;
  background: linear-gradient(90deg, #bd5736, #d98968 65%, rgba(217, 137, 104, 0));
}

.login-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.login-card__head h2 {
  margin: 0;
  color: var(--cl-near-black, #2c2b28);
  font-size: 1.28rem;
  font-weight: 750;
}

.login-card__head p {
  margin: 6px 0 0;
  color: var(--cl-olive, #6b6558);
  font-size: 0.8rem;
}

.login-card__mark {
  flex: 0 0 auto;
  padding: 5px 8px;
  border-radius: 999px;
  background: rgba(201, 100, 66, 0.1);
  color: var(--cl-terracotta, #c96442);
  font-size: 0.68rem;
  font-weight: 700;
}

.login-form {
  display: grid;
  gap: 13px;
  margin-top: 19px;
}

.field {
  display: grid;
  gap: 6px;
}

.field > span:first-child {
  color: var(--cl-charcoal, #4f4b44);
  font-size: 0.78rem;
  font-weight: 700;
}

.field__control {
  display: grid;
  grid-template-columns: 21px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  height: 48px;
  padding: 0 12px;
  border: 1px solid var(--cl-border-warm, #d9d2c4);
  border-radius: 11px;
  background: var(--cl-white, #fff);
  box-sizing: border-box;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.field__control:focus-within {
  border-color: var(--cl-terracotta, #c96442);
  box-shadow: 0 0 0 3px rgba(201, 100, 66, 0.14);
  transform: translateY(-1px);
}

.field__control > svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: var(--cl-stone, #928a7c);
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: stroke 0.18s ease;
}

.field__control:focus-within > svg {
  stroke: var(--cl-terracotta, #c96442);
}

.field input {
  width: 100%;
  min-width: 0;
  height: 100%;
  padding: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--cl-near-black, #2c2b28);
  font: inherit;
  font-size: 16px;
}

.field input::placeholder {
  color: var(--cl-stone, #9a9387);
}

.password-toggle {
  min-width: 40px;
  min-height: 34px;
  padding: 0 4px;
  border: 0;
  background: transparent;
  color: var(--cl-olive, #6b6558);
  font: inherit;
  font-size: 0.72rem;
  cursor: pointer;
}

.password-hint {
  margin: -5px 0 0;
  color: var(--cl-olive, #6b6558);
  font-size: 0.7rem;
  line-height: 1.4;
}

.submit-btn {
  position: relative;
  display: flex;
  width: 100%;
  min-height: 48px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 3px;
  overflow: hidden;
  border: 0;
  border-radius: 11px;
  background: linear-gradient(135deg, #b95534, #c96442 64%, #d78161);
  color: #fff;
  font: inherit;
  font-weight: 750;
  letter-spacing: 0.08em;
  cursor: pointer;
  box-shadow: 0 11px 24px rgba(201, 100, 66, 0.25);
  transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease;
}

.submit-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, transparent 26%, rgba(255, 255, 255, 0.28) 47%, transparent 68%);
  transform: translateX(-130%);
  animation: button-sheen 5s ease-in-out infinite;
}

.submit-btn > * {
  position: relative;
  z-index: 1;
}

.submit-btn svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: transform 0.18s ease;
}

.submit-btn:hover:not(:disabled) {
  filter: brightness(1.04);
  transform: translateY(-1px);
  box-shadow: 0 15px 28px rgba(201, 100, 66, 0.31);
}

.submit-btn:hover:not(:disabled) svg {
  transform: translateX(3px);
}

.submit-btn:disabled {
  opacity: 0.64;
  cursor: default;
}

.loading-dot {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.toast {
  margin-top: 13px;
  padding: 9px 11px;
  border: 1px solid rgba(181, 51, 51, 0.28);
  border-radius: 10px;
  background: rgba(181, 51, 51, 0.07);
  color: #9b352f;
  font-size: 0.78rem;
  line-height: 1.45;
  animation: toast-enter 0.24s ease both;
}

.easter-egg {
  position: fixed;
  z-index: 20;
  top: max(20px, calc(env(safe-area-inset-top, 0px) + 12px));
  left: 50%;
  display: flex;
  min-height: 40px;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  border: 1px solid rgba(169, 68, 39, 0.28);
  border-radius: 999px;
  background: rgba(255, 253, 249, 0.94);
  color: #9e4028;
  font-size: 0.82rem;
  letter-spacing: 0.08em;
  box-shadow: 0 12px 30px rgba(72, 57, 45, 0.16), 0 0 24px rgba(201, 100, 66, 0.12);
  backdrop-filter: blur(10px);
  transform: translateX(-50%);
}

.easter-egg > span {
  color: #176d98;
  animation: egg-star 0.8s ease-in-out infinite alternate;
}

.easter-egg > span:last-child {
  animation-delay: -0.4s;
}

.easter-egg-enter-active,
.easter-egg-leave-active {
  transition: opacity 0.24s ease, transform 0.34s cubic-bezier(0.22, 1, 0.36, 1);
}

.easter-egg-enter-from,
.easter-egg-leave-to {
  opacity: 0;
  transform: translate(-50%, -16px) scale(0.9);
}

.fireworks-canvas {
  position: fixed;
  z-index: 18;
  inset: 0;
  display: block;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

@media (max-width: 560px) {
  .login-page {
    min-height: 480px;
    padding:
      max(13px, env(safe-area-inset-top, 0px))
      max(14px, env(safe-area-inset-right, 0px))
      max(13px, env(safe-area-inset-bottom, 0px))
      max(14px, env(safe-area-inset-left, 0px));
  }

  .login-shell {
    gap: 14px;
  }

  .brand__logo {
    width: 68px;
    height: 68px;
    margin-bottom: 9px;
  }

  .brand__logo-surface {
    width: 56px;
    height: 56px;
    border-radius: 16px;
  }

  .brand__logo-surface img {
    width: 48px;
    height: 48px;
  }

  .brand h1 {
    font-size: clamp(1.68rem, 7vw, 2rem);
  }

  .login-card {
    padding: 21px 18px;
    border-radius: 16px;
  }

  .login-card__mark {
    display: none;
  }

  .login-form {
    gap: 11px;
    margin-top: 16px;
  }
}

@media (max-height: 650px) {
  .login-shell {
    gap: 9px;
  }

  .brand h1 {
    margin-top: 5px;
  }

  .brand__logo {
    width: 54px;
    height: 54px;
    margin-bottom: 5px;
  }

  .brand__logo-surface {
    width: 46px;
    height: 46px;
    border-radius: 14px;
  }

  .brand__logo-surface img {
    width: 40px;
    height: 40px;
  }

  .brand__desc,
  .brand__rule {
    display: none;
  }

  .login-card {
    padding: 16px 18px;
  }

  .login-form {
    gap: 8px;
    margin-top: 11px;
  }

  .field__control,
  .submit-btn {
    min-height: 44px;
    height: 44px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ambient,
  .pulse-wave,
  .screen-pulse,
  .energy-ribbon,
  .route-line i,
  .motion-dot,
  .spark-field i,
  .particle-flow i,
  .brand,
  .brand__logo-ring,
  .brand__logo-surface,
  .brand__logo-surface::after,
  .brand__logo--escaping,
  .brand__rule,
  .login-card,
  .submit-btn::before,
  .loading-dot,
  .toast {
    animation: none !important;
  }

  .easter-egg > span {
    animation: none !important;
  }

  .fireworks-canvas {
    display: none !important;
  }

  .field__control,
  .submit-btn,
  .submit-btn svg {
    transition: none !important;
  }
}

@keyframes brand-enter {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes card-enter {
  from { opacity: 0; transform: translateY(18px) scale(0.985); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes ambient-one {
  to { transform: translate3d(42px, 28px, 0) scale(1.1); }
}

@keyframes ambient-two {
  to { transform: translate3d(-38px, -22px, 0) scale(1.08); }
}

@keyframes pulse-wave {
  0% { opacity: 0; transform: scale(0.52); }
  24% { opacity: 0.75; }
  72%, 100% { opacity: 0; transform: scale(1.18); }
}

@keyframes screen-pulse {
  0% { opacity: 0; transform: translate(-50%, -50%) scale(0.04); }
  12% { opacity: 0.8; }
  54% { opacity: 0.34; }
  86%, 100% { opacity: 0; transform: translate(-50%, -50%) scale(1.18); }
}

@keyframes spark-blink {
  0%, 100% { opacity: 0.08; transform: scale(0.55); }
  46% { opacity: 0.92; transform: scale(1.35); }
  58% { opacity: 0.32; transform: scale(0.82); }
  72% { opacity: 0.78; transform: scale(1.08); }
}

@keyframes particle-stream {
  0% { opacity: 0; transform: translate3d(0, 0, 0) scale(0.65); }
  8% { opacity: 0.82; }
  48% { opacity: 0.5; transform: translate3d(58vw, -14px, 0) scale(1); }
  92% { opacity: 0.76; }
  100% { opacity: 0; transform: translate3d(138vw, 18px, 0) scale(0.72); }
}

@keyframes ribbon-breathe {
  0%, 100% { opacity: 0.08; translate: -4% 8px; scale: 0.94; }
  46% { opacity: 0.72; }
  62% { opacity: 0.38; translate: 4% -6px; scale: 1.06; }
}

@keyframes logo-ring {
  0%, 12%, 100% { opacity: 0.64; transform: scale(0.92) rotate(-5deg); }
  38% { opacity: 1; transform: scale(1.1) rotate(4deg); box-shadow: 0 0 24px rgba(201, 100, 66, 0.2); }
  58% { opacity: 0.78; transform: scale(0.98) rotate(-2deg); }
}

@keyframes logo-bounce {
  0%, 8%, 100% { transform: translate3d(0, 0, 0) rotate(0) scale(1, 1); }
  17% { transform: translate3d(-7px, -13px, 0) rotate(-4deg) scale(0.97, 1.04); }
  26% { transform: translate3d(3px, 1px, 0) rotate(1deg) scale(1.06, 0.94); }
  35% { transform: translate3d(9px, -8px, 0) rotate(5deg) scale(0.98, 1.03); }
  44% { transform: translate3d(-2px, 2px, 0) rotate(-1deg) scale(1.04, 0.96); }
  55% { transform: translate3d(-5px, -5px, 0) rotate(-3deg) scale(0.99, 1.01); }
  65% { transform: translate3d(6px, -11px, 0) rotate(3deg) scale(0.97, 1.04); }
  75% { transform: translate3d(1px, 2px, 0) rotate(0) scale(1.05, 0.95); }
  84% { transform: translate3d(-3px, -4px, 0) rotate(-2deg) scale(0.99, 1.01); }
  92% { transform: translate3d(0, 0, 0) rotate(0) scale(1, 1); }
}

@keyframes logo-sheen {
  0%, 58% { left: -45%; opacity: 0; }
  66% { opacity: 0.92; }
  84%, 100% { left: 122%; opacity: 0; }
}

@keyframes logo-escape {
  0% { transform: translate3d(0, 0, 0) rotate(0) scale(1); }
  14% { transform: translate3d(var(--escape-back-x), var(--escape-back-y), 0) rotate(-5deg) scale(0.9); }
  46% { transform: translate3d(var(--escape-x), var(--escape-y), 0) rotate(var(--escape-rotate)) scale(1.12); }
  62% { transform: translate3d(var(--escape-return-x), var(--escape-return-y), 0) rotate(8deg) scale(0.96); }
  82% { transform: translate3d(-5px, -4px, 0) rotate(-4deg) scale(1.04); }
  100% { transform: translate3d(0, 0, 0) rotate(0) scale(1); }
}

@keyframes egg-star {
  to { opacity: 0.35; transform: rotate(45deg) scale(1.35); }
}

@keyframes dot-drift {
  to { transform: translate3d(16px, -18px, 0); opacity: 0.42; }
}

@keyframes route-run {
  from { transform: translateX(-90px); }
  to { transform: translateX(calc(120vw + 90px)); }
}

@keyframes rule-breathe {
  to { width: 88px; filter: brightness(1.08); }
}

@keyframes button-sheen {
  0%, 58% { transform: translateX(-130%); }
  78%, 100% { transform: translateX(130%); }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes toast-enter {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
