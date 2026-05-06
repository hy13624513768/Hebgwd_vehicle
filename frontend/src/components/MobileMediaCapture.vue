<template>
  <div class="stack mobile-capture">
    <section class="panel" :aria-label="panelAriaLabel">
      <div class="capture-block">
        <div class="hd">
          <h2>{{ photoHeading }}</h2>
        </div>
        <p class="hint">{{ photoHint }}</p>

        <input
          ref="photoInputRef"
          type="file"
          class="sr-only"
          accept="image/*"
          capture="environment"
          aria-hidden="true"
          tabindex="-1"
          @change="onPhotoSelected"
        />

        <div class="actions">
          <button type="button" class="primary btn" @click="openPhotoPicker">打开相机拍照</button>
          <button v-if="photoPreviewUrl" type="button" class="ghost btn" @click="clearPhoto">清除照片</button>
          <a
            v-if="photoPreviewUrl"
            class="ghost btn btn--link"
            :href="photoPreviewUrl"
            :download="photoDownloadName"
          >
            下载图片
          </a>
        </div>

        <div v-if="photoPreviewUrl" class="preview-wrap">
          <img :src="photoPreviewUrl" alt="照片预览" class="preview-img" />
          <p v-if="photoFileLabel" class="meta">{{ photoFileLabel }}</p>
        </div>
      </div>

      <template v-if="enableVideo">
        <div class="block-sep" role="separator" aria-hidden="true" />

        <div class="capture-block">
          <div class="hd">
            <h2>{{ videoHeading }}</h2>
          </div>
          <p class="hint">{{ videoHint }}</p>

          <input
            ref="videoInputRef"
            type="file"
            class="sr-only"
            accept="video/*"
            capture="environment"
            aria-hidden="true"
            tabindex="-1"
            @change="onVideoSelected"
          />

          <div class="actions">
            <button type="button" class="primary btn" @click="openVideoPicker">打开相机录像</button>
            <button v-if="videoPreviewUrl" type="button" class="ghost btn" @click="clearVideo">清除视频</button>
            <a
              v-if="videoPreviewUrl"
              class="ghost btn btn--link"
              :href="videoPreviewUrl"
              :download="videoDownloadName"
            >
              下载视频
            </a>
          </div>

          <div v-if="videoPreviewUrl" class="preview-wrap">
            <video
              :src="videoPreviewUrl"
              class="preview-video"
              controls
              playsinline
              preload="metadata"
            />
            <p v-if="videoFileLabel" class="meta">{{ videoFileLabel }}</p>
          </div>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onUnmounted, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    /** 整块面板的无障碍名称 */
    panelAriaLabel?: string
    photoHeading?: string
    videoHeading?: string
    enableVideo?: boolean
    photoHint?: string
    videoHint?: string
    /** 下载文件名前缀（无扩展名时自动补 .jpg / .mp4） */
    photoFileBase?: string
    videoFileBase?: string
  }>(),
  {
    panelAriaLabel: '移动端拍照与录像',
    photoHeading: '现场拍照',
    videoHeading: '现场录像',
    enableVideo: false,
    photoHint:
      '在手机浏览器中点击下方按钮将调起相机拍照（部分机型或桌面端会改为选择相册/文件）。照片仅在当前页面预览，不会自动上传服务器。',
    videoHint:
      '在手机浏览器中点击下方按钮可调起相机录像（是否出现录像界面因浏览器与机型而异，部分环境仅支持从相册选取视频）。视频仅在当前页面预览，不会自动上传服务器。',
    photoFileBase: 'capture_photo',
    videoFileBase: 'capture_video',
  },
)

const photoInputRef = ref<HTMLInputElement | null>(null)
const videoInputRef = ref<HTMLInputElement | null>(null)

const photoPreviewUrl = ref<string | null>(null)
const photoFileLabel = ref('')
const photoDownloadName = ref(`${props.photoFileBase}.jpg`)

const videoPreviewUrl = ref<string | null>(null)
const videoFileLabel = ref('')
const videoDownloadName = ref(`${props.videoFileBase}.mp4`)

function revokePhoto() {
  if (photoPreviewUrl.value) {
    URL.revokeObjectURL(photoPreviewUrl.value)
    photoPreviewUrl.value = null
  }
  photoFileLabel.value = ''
}

function revokeVideo() {
  if (videoPreviewUrl.value) {
    URL.revokeObjectURL(videoPreviewUrl.value)
    videoPreviewUrl.value = null
  }
  videoFileLabel.value = ''
}

function formatSize(n: number) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function sanitizeBaseName(name: string) {
  return name.replace(/[^\w.-]+/g, '_') || 'file'
}

function openPhotoPicker() {
  photoInputRef.value?.click()
}

function openVideoPicker() {
  videoInputRef.value?.click()
}

function onPhotoSelected(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !file.type.startsWith('image/')) return

  revokePhoto()
  photoFileLabel.value = file.name ? `${file.name} · ${formatSize(file.size)}` : formatSize(file.size)
  photoPreviewUrl.value = URL.createObjectURL(file)
  const base = sanitizeBaseName(file.name || props.photoFileBase)
  const lower = base.toLowerCase()
  photoDownloadName.value =
    lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.png') || lower.endsWith('.webp')
      ? base
      : `${sanitizeBaseName(props.photoFileBase)}.jpg`
}

function onVideoSelected(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !file.type.startsWith('video/')) return

  revokeVideo()
  videoFileLabel.value = file.name ? `${file.name} · ${formatSize(file.size)}` : formatSize(file.size)
  videoPreviewUrl.value = URL.createObjectURL(file)
  const base = sanitizeBaseName(file.name || props.videoFileBase)
  const lower = base.toLowerCase()
  videoDownloadName.value =
    lower.endsWith('.mp4') ||
    lower.endsWith('.webm') ||
    lower.endsWith('.mov') ||
    lower.endsWith('.m4v') ||
    lower.endsWith('.3gp')
      ? base
      : `${sanitizeBaseName(props.videoFileBase)}.mp4`
}

function clearPhoto() {
  revokePhoto()
}

function clearVideo() {
  revokeVideo()
}

onUnmounted(() => {
  revokePhoto()
  revokeVideo()
})
</script>

<style scoped>
.stack.mobile-capture {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.panel {
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-ivory);
  border-radius: 16px;
  padding: 14px;
  box-shadow: rgba(0, 0, 0, 0.05) 0px 4px 24px;
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
}

.capture-block {
  min-width: 0;
}

.block-sep {
  height: 1px;
  margin: 18px 0;
  background: rgba(142, 132, 109, 0.22);
}

.hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.hd h2 {
  margin: 0;
  font-size: 1.05rem;
  font-family: Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif;
  font-weight: 500;
}

.hint {
  margin: 0 0 14px;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--cl-olive, #5c5a52);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}

.btn {
  min-height: 44px;
  padding: 0.5rem 1rem;
  border-radius: 10px;
  font-size: 0.875rem;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.btn.primary {
  border: 1px solid rgba(201, 100, 66, 0.45);
  background: var(--cl-terracotta, #c96442);
  color: #fff;
}

.btn.ghost {
  border: 1px solid rgba(142, 132, 109, 0.35);
  background: rgba(255, 255, 255, 0.9);
  color: var(--cl-charcoal, #2c2b28);
}

.btn--link {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

.preview-wrap {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--cl-border-cream, rgba(142, 132, 109, 0.25));
  background: rgba(255, 255, 255, 0.6);
}

.preview-img {
  display: block;
  width: 100%;
  max-height: min(70vh, 520px);
  object-fit: contain;
  background: #f5f3ef;
}

.preview-video {
  display: block;
  width: 100%;
  max-height: min(70vh, 520px);
  background: #1a1a18;
}

.meta {
  margin: 0;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--cl-olive, #5c5a52);
}
</style>
