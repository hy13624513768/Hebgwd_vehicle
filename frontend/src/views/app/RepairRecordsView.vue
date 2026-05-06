<template>
  <MobileMediaCapture
    panel-aria-label="维修现场拍照与录像"
    photo-heading="现场拍照（维修凭证）"
    video-heading="现场录像（维修凭证）"
    :enable-video="true"
    photo-file-base="repair_record_photo"
    video-file-base="repair_record_video"
  />
</template>

<script setup lang="ts">
import MobileMediaCapture from '@/components/MobileMediaCapture.vue'
</script>
