<template>
  <MobileMediaCapture
    panel-aria-label="加油凭证拍照与预览"
    photo-heading="现场拍照"
    :enable-video="false"
    photo-file-base="fuel_record_photo"
    photo-hint="在手机浏览器中点击下方按钮将调起相机拍照（部分机型或桌面端会改为选择相册/文件）。照片仅在当前页面预览，不会自动上传服务器。"
  />
</template>

<script setup lang="ts">
import MobileMediaCapture from '@/components/MobileMediaCapture.vue'
</script>
