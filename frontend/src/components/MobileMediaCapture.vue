<template>
  <div class="stack mobile-capture" :class="{ 'mobile-capture--compact': compact }">
    <section class="panel" :aria-label="panelAriaLabel">
      <div v-if="enablePhoto" class="capture-block" :class="{ 'capture-block--single-photo': singlePhoto }">
        <div v-if="photoHeading || photoItems.length" class="hd">
          <h2 v-if="photoHeading">{{ photoHeading }}</h2>
          <span v-if="photoItems.length" class="ready-badge">已选择 {{ photoItems.length }} 张</span>
        </div>
        <p v-if="photoHint" class="hint">{{ photoHint }}</p>

        <input
          ref="photoInputRef"
          type="file"
          class="sr-only"
          accept="image/jpeg,image/png,image/webp"
          :capture="photoCaptureAttr"
          :multiple="effectiveMaxPhotos > 1"
          aria-hidden="true"
          tabindex="-1"
          @change="onPhotoSelected"
        />
        <p v-if="photoError" class="selection-error" role="alert">{{ photoError }}</p>

        <div v-if="photoItems.length" class="preview-grid" :class="{ 'preview-grid--multi': effectiveMaxPhotos > 1 }">
          <article v-for="(item, index) in photoItems" :key="item.url" class="preview-wrap">
            <img :src="item.url" :alt="`照片预览 ${index + 1}`" class="preview-img" />
            <div class="preview-meta">
              <p class="meta">{{ item.label }}</p>
              <div class="preview-meta__actions">
                <a v-if="showPhotoDownload" class="preview-link" :href="item.url" :download="item.downloadName">下载</a>
                <button type="button" class="preview-link preview-link--danger" @click="removePhoto(index)">移除</button>
              </div>
            </div>
          </article>
        </div>

        <div class="actions">
          <button type="button" class="primary btn" :disabled="photoItems.length >= effectiveMaxPhotos" @click="openPhotoPicker">
            {{ photoPrimaryLabel }}
          </button>
          <button v-if="photoItems.length" type="button" class="ghost btn" @click="clearPhoto">
            {{ effectiveMaxPhotos > 1 ? '清除全部' : '清除照片' }}
          </button>
        </div>
      </div>

      <template v-if="enableVideo">
        <div v-if="enablePhoto" class="block-sep" role="separator" aria-hidden="true" />

        <div class="capture-block" :class="{ 'capture-block--single-photo': singleVideo }">
          <div v-if="videoHeading || videoPreviewUrl" class="hd">
            <h2 v-if="videoHeading">{{ videoHeading }}</h2>
            <span v-if="videoPreviewUrl" class="ready-badge">已选择</span>
          </div>
          <p v-if="videoHint" class="hint">{{ videoHint }}</p>

          <input
            ref="videoInputRef"
            type="file"
            class="sr-only"
            accept="video/mp4,video/webm,video/quicktime"
            :capture="videoCaptureAttr"
            aria-hidden="true"
            tabindex="-1"
            @change="onVideoSelected"
          />
          <p v-if="videoError" class="selection-error" role="alert">{{ videoError }}</p>

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

          <div class="actions">
            <button type="button" class="primary btn" @click="openVideoPicker">
              {{ videoPrimaryLabel }}
            </button>
            <button v-if="videoPreviewUrl" type="button" class="ghost btn" @click="clearVideo">清除视频</button>
            <a
              v-if="videoPreviewUrl && showVideoDownload"
              class="ghost btn btn--link"
              :href="videoPreviewUrl"
              :download="videoDownloadName"
            >
              下载视频
            </a>
          </div>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    /** 整块面板的无障碍名称 */
    panelAriaLabel?: string
    photoHeading?: string
    videoHeading?: string
    enablePhoto?: boolean
    enableVideo?: boolean
    photoHint?: string
    videoHint?: string
    /** 下载文件名前缀（无扩展名时自动补 .jpg / .mp4） */
    photoFileBase?: string
    videoFileBase?: string
    /** 是否展示照片「下载图片」链接（加油单张模式可关闭） */
    showPhotoDownload?: boolean
    /** 为 true 时强制优先打开后置相机；false 时允许拍照或从相册选择。 */
    photoInputCapture?: boolean
    /** 是否展示视频「下载视频」链接 */
    showVideoDownload?: boolean
    /**
     * 单张照片模式：预览在按钮上方、隐藏下载；已有照片时主按钮文案为「重新拍照」。
     * 再次选择文件会替换当前照片（仍仅保留一张）。
     */
    singlePhoto?: boolean
    /**
     * 单段视频模式：与 singlePhoto 类似；主按钮为「录像或上传视频」/「重新选择视频」。
     * 不设 capture 时（videoInputCapture=false）多数手机可在系统面板中选择录像或相册文件。
     */
    singleVideo?: boolean
    /** 为 true 时在视频 input 上加 capture=environment，更倾向直接调起后置相机（可能弱化相册入口） */
    videoInputCapture?: boolean
    /** 与后端 MAX_UPLOAD_MB 保持一致的单文件上限。 */
    maxFileMb?: number
    /** 可选择的照片数量上限；singlePhoto=true 时始终限制为 1 张。 */
    maxPhotos?: number
    /** 紧凑台账样式：去掉嵌套卡片底色，并缩小操作按钮。 */
    compact?: boolean
  }>(),
  {
    panelAriaLabel: '移动端拍照与录像',
    photoHeading: '现场拍照',
    videoHeading: '现场录像',
    enablePhoto: true,
    enableVideo: false,
    photoHint:
      '在手机浏览器中点击下方按钮将调起相机拍照（部分机型或桌面端会改为选择相册/文件）。照片仅在当前页面预览，不会自动上传服务器。',
    videoHint:
      '在手机浏览器中点击下方按钮可调起相机录像（是否出现录像界面因浏览器与机型而异，部分环境仅支持从相册选取视频）。视频仅在当前页面预览，不会自动上传服务器。',
    photoFileBase: 'capture_photo',
    videoFileBase: 'capture_video',
    showPhotoDownload: true,
    photoInputCapture: true,
    showVideoDownload: true,
    singlePhoto: false,
    singleVideo: false,
    videoInputCapture: false,
    maxFileMb: 50,
    maxPhotos: 1,
    compact: false,
  },
)

const photoInputRef = ref<HTMLInputElement | null>(null)
const videoInputRef = ref<HTMLInputElement | null>(null)

type PhotoItem = { file: File; url: string; label: string; downloadName: string }

const photoItems = ref<PhotoItem[]>([])
const photoError = ref('')
const photoCaptureAttr = computed(() => (props.photoInputCapture ? 'environment' : undefined))
const effectiveMaxPhotos = computed(() => (props.singlePhoto ? 1 : Math.max(1, Math.floor(props.maxPhotos))))

const photoPrimaryLabel = computed(() => {
  const count = photoItems.value.length
  const max = effectiveMaxPhotos.value
  if (max > 1) {
    if (count >= max) return `已达到 ${max} 张上限`
    if (count > 0) return `继续添加照片（${count}/${max}）`
    return props.compact ? `拍照 / 选择图片（最多${max}张）` : `添加照片（最多${max}张）`
  }
  return props.singlePhoto && count ? '更换图片' : props.compact ? '拍照 / 选择图片' : '打开相机拍照'
})

const videoCaptureAttr = computed(() => (props.videoInputCapture ? 'environment' : undefined))

const videoPreviewUrl = ref<string | null>(null)
const videoFileRef = ref<File | null>(null)
const videoFileLabel = ref('')
const videoError = ref('')
const videoDownloadName = ref(`${props.videoFileBase}.mp4`)

const videoPrimaryLabel = computed(() =>
  props.singleVideo && videoPreviewUrl.value
    ? '更换视频'
    : props.compact
      ? '录像 / 选择视频'
      : '录像或上传视频',
)

function revokePhoto() {
  for (const item of photoItems.value) URL.revokeObjectURL(item.url)
  photoItems.value = []
}

function revokeVideo() {
  if (videoPreviewUrl.value) {
    URL.revokeObjectURL(videoPreviewUrl.value)
    videoPreviewUrl.value = null
  }
  videoFileRef.value = null
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
  const selectedFiles = Array.from(input.files ?? [])
  input.value = ''
  photoError.value = ''
  if (!selectedFiles.length) return

  const validFiles: File[] = []
  let invalidType = false
  let oversized = false
  for (const file of selectedFiles) {
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      invalidType = true
      continue
    }
    if (file.size > props.maxFileMb * 1024 * 1024) {
      oversized = true
      continue
    }
    validFiles.push(file)
  }

  if (effectiveMaxPhotos.value === 1) revokePhoto()
  const remaining = effectiveMaxPhotos.value - photoItems.value.length
  const accepted = validFiles.slice(0, Math.max(0, remaining))
  const startIndex = photoItems.value.length
  photoItems.value.push(
    ...accepted.map((file, index) => {
      const base = sanitizeBaseName(file.name || `${props.photoFileBase}_${startIndex + index + 1}`)
      const lower = base.toLowerCase()
      return {
        file,
        url: URL.createObjectURL(file),
        label: file.name ? `${file.name} · ${formatSize(file.size)}` : formatSize(file.size),
        downloadName:
          lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.png') || lower.endsWith('.webp')
            ? base
            : `${sanitizeBaseName(props.photoFileBase)}.jpg`,
      }
    }),
  )

  const messages: string[] = []
  if (invalidType) messages.push('部分文件不是 JPG、PNG 或 WebP 图片')
  if (oversized) messages.push(`部分图片超过 ${props.maxFileMb} MB`)
  if (validFiles.length > accepted.length) messages.push(`最多只能上传 ${effectiveMaxPhotos.value} 张照片`)
  photoError.value = messages.join('；')
}

function removePhoto(index: number) {
  const [removed] = photoItems.value.splice(index, 1)
  if (removed) URL.revokeObjectURL(removed.url)
  photoError.value = ''
}

function onVideoSelected(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  videoError.value = ''
  if (!file) return
  if (!['video/mp4', 'video/webm', 'video/quicktime'].includes(file.type)) {
    videoError.value = '仅支持 MP4、WebM 或 MOV 视频。'
    return
  }
  if (file.size > props.maxFileMb * 1024 * 1024) {
    videoError.value = `视频不能超过 ${props.maxFileMb} MB。`
    return
  }

  revokeVideo()
  videoFileRef.value = file
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
  photoError.value = ''
}

function clearVideo() {
  revokeVideo()
  videoError.value = ''
}

onUnmounted(() => {
  revokePhoto()
  revokeVideo()
})

defineExpose({
  /** 当前选中的加油/现场照片文件（未选则为 null） */
  getPhotoFile: () => photoItems.value[0]?.file ?? null,
  /** 当前选中的全部照片文件。 */
  getPhotoFiles: () => photoItems.value.map((item) => item.file),
  clearPhoto,
  getVideoFile: () => videoFileRef.value,
  clearVideo,
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

.ready-badge {
  flex: 0 0 auto;
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  background: rgba(46, 125, 76, 0.12);
  color: #25633c;
  font-size: 0.75rem;
  font-weight: 700;
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
  margin-bottom: 0;
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

.btn:disabled {
  opacity: 0.55;
  cursor: default;
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
  margin-bottom: 14px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--cl-border-cream, rgba(142, 132, 109, 0.25));
  background: rgba(255, 255, 255, 0.6);
}

.preview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

.preview-grid--multi {
  grid-template-columns: repeat(auto-fit, minmax(min(140px, 100%), 1fr));
}

.preview-grid .preview-wrap {
  min-width: 0;
  margin: 0;
}

.capture-block--single-photo .preview-wrap {
  margin-bottom: 18px;
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

.preview-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
}

.preview-meta .meta {
  min-width: 0;
  overflow: hidden;
  padding: 0;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-meta__actions {
  display: inline-flex;
  flex: 0 0 auto;
  gap: 8px;
}

.preview-link {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--cl-terracotta, #c96442);
  font: inherit;
  font-size: 0.72rem;
  text-decoration: none;
  cursor: pointer;
}

.preview-link--danger {
  color: #9b352b;
}

.selection-error {
  margin: -4px 0 12px;
  color: #9b352b;
  font-size: 0.8125rem;
  font-weight: 600;
}

.mobile-capture--compact .panel {
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.mobile-capture--compact .hd {
  justify-content: flex-start;
  margin-bottom: 6px;
}

.mobile-capture--compact .hd h2 {
  color: var(--cl-olive, #5c5a52);
  font-family: inherit;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.mobile-capture--compact .hint {
  max-width: 40rem;
  margin-bottom: 6px;
  line-height: 1.4;
}

.mobile-capture--compact .actions {
  gap: 8px;
}

.mobile-capture--compact .btn {
  width: auto;
  min-width: 0;
  min-height: 40px;
  padding: 0.45rem 0.85rem;
  border-radius: 9px;
  font-size: 0.8125rem;
  font-weight: 650;
}

.mobile-capture--compact .block-sep {
  margin: 10px 0;
}

@media (max-width: 559px) {
  .panel {
    padding: 12px;
    border-radius: 14px;
    box-shadow: none;
  }

  .mobile-capture--compact .panel {
    padding: 0;
    border-radius: 0;
  }

  .hd {
    margin-bottom: 6px;
  }

  .hd h2 {
    font-family: inherit;
    font-size: 0.95rem;
    font-weight: 700;
  }

  .hint {
    margin-bottom: 12px;
    font-size: 0.8125rem;
  }
}
</style>
