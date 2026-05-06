<template>
  <svg
    class="nav-svg"
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <g
      v-if="name === 'dashboard'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <rect x="3" y="3" width="7.5" height="7.5" rx="1.5" />
      <rect x="13.5" y="3" width="7.5" height="7.5" rx="1.5" />
      <rect x="3" y="13.5" width="7.5" height="7.5" rx="1.5" />
      <rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.5" />
    </g>
    <g
      v-else-if="name === 'basics'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <rect x="3" y="4" width="18" height="7" rx="1.5" />
      <rect x="3" y="13" width="18" height="7" rx="1.5" />
      <path d="M7 7.5h6M7 16.5h6" opacity="0.45" />
    </g>
    <g
      v-else-if="name === 'vehicles'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M4 11h12v6H4v-6z" />
      <path d="M16 11l2.5-3H21v9h-2.5" />
      <circle cx="7.5" cy="17.5" r="1.5" />
      <circle cx="16.5" cy="17.5" r="1.5" />
    </g>
    <g
      v-else-if="name === 'drivers'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <circle cx="12" cy="8" r="4" />
      <path d="M5 20v-1a5 5 0 0110 0v1" />
    </g>
    <g
      v-else-if="name === 'accounts'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <rect x="4" y="5" width="16" height="14" rx="2" />
      <circle cx="10" cy="11" r="2" />
      <path d="M7 16.5h6a3 3 0 00-6 0z" />
    </g>
    <g
      v-else-if="name === 'trips'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M12 21s-6.5-4.2-6.5-10a6.5 6.5 0 1113 0c0 5.8-6.5 10-6.5 10z" />
      <circle cx="12" cy="10.5" r="2.2" />
    </g>
    <g
      v-else-if="name === 'location'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M12 21s7-6.2 7-11a7 7 0 10-14 0c0 4.8 7 11 7 11z" opacity="0.35" />
      <circle cx="12" cy="10" r="2.8" />
      <path d="M12 3v2M12 19v2M3 12h2M19 12h2" opacity="0.4" />
    </g>
    <g
      v-else-if="name === 'approval'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <circle cx="5" cy="12" r="2.5" />
      <circle cx="12" cy="12" r="2.5" />
      <circle cx="19" cy="12" r="2.5" />
      <path d="M7.5 12h3M14.5 12h3" />
      <path d="M12 6v2.5M12 15.5V19" opacity="0.45" />
    </g>
    <g
      v-else-if="name === 'usage'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M8 4h8v4H8V4zM6 9h12v11H6V9z" />
      <path d="M9 13h6M9 16.5h4" opacity="0.5" />
    </g>
    <g
      v-else-if="name === 'maintenance'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l1.9-1.9a6 6 0 01-7.9 7.9l-6.9 6.9a2 2 0 01-2.8-2.8l6.9-6.9a6 6 0 017.9-7.9l-2 2z" />
    </g>
    <g
      v-else-if="name === 'insurance'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M12 4L5 7v6c0 4.5 3.2 8.7 7 10 3.8-1.3 7-5.5 7-10V7l-7-3z" />
      <path d="M9.5 12.5l2 2 4-4" />
    </g>
    <g
      v-else-if="name === 'inspection'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M8 4h10a2 2 0 012 2v12a2 2 0 01-2 2H8" />
      <path d="M4 8h4v10H4V8z" />
      <path d="M11 9h5M11 13h5M11 17h3" opacity="0.55" />
    </g>
    <g
      v-else-if="name === 'access'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M4 10h16M4 10v8h16v-8" />
      <path d="M9 10V6a3 3 0 016 0v4" />
      <circle cx="12" cy="15" r="1.8" />
    </g>
    <path
      v-else-if="name === 'fuel'"
      d="M12 2.5c2.5 4.5 6 7.8 6 11.5a6 6 0 11-12 0c0-3.7 3.5-7 6-11.5z"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <g
      v-else-if="name === 'expenses'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M3 10h18" />
      <path d="M7 15h4" />
    </g>
    <g
      v-else-if="name === 'reports'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M18 20V10M12 20V4M6 20v-6" />
    </g>
    <g
      v-else-if="name === 'aiAnalysis'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M4 18V6l5 4 4-5 4 4 3-3v12H4z" />
      <path d="M9 10l2 1.5L14 8" opacity="0.55" />
      <circle cx="17" cy="7" r="1.8" fill="currentColor" />
    </g>
    <g
      v-else-if="name === 'aiLearning'"
      stroke="currentColor"
      stroke-width="1.55"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M5 5.5L12 3l7 2.5v11L12 19l-7-2.5V5.5z" />
      <path d="M12 3v16" opacity="0.45" />
      <path d="M8.5 8h7M8.5 11h5" opacity="0.55" />
    </g>
  </svg>
</template>

<script setup lang="ts">
export type NavIconName =
  | 'dashboard'
  | 'basics'
  | 'vehicles'
  | 'drivers'
  | 'accounts'
  | 'trips'
  | 'location'
  | 'approval'
  | 'usage'
  | 'maintenance'
  | 'insurance'
  | 'inspection'
  | 'access'
  | 'fuel'
  | 'expenses'
  | 'reports'
  | 'aiAnalysis'
  | 'aiLearning'

defineProps<{ name: NavIconName }>()
</script>

<style scoped>
.nav-svg {
  display: block;
  flex-shrink: 0;
}
</style>
