<script setup lang="ts">
import { computed } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { skyLayers } from '../lib/sky'

// Stars wider than this get a glow.
const GLOW_MIN_PX = 1.8

/** Fixed behind the page; each layer is 200 % high with every star twice, and slides by -50 %: no visible restart. */
const props = defineProps<{ animated: boolean }>()
const phone = useMediaQuery('(max-width: 699px)')
const layers = computed(() => skyLayers(phone.value))
</script>

<template>
  <div aria-hidden="true" class="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
    <div
      v-for="(l, li) in layers"
      :key="li"
      data-sky
      class="absolute top-0 left-0 h-[200%] w-full will-change-transform"
      :style="{ animation: props.animated ? `v2-drift ${l.duration}s linear infinite` : 'none' }"
    >
      <template v-for="(s, i) in l.stars" :key="i">
        <span
          v-for="off in [0, 50]"
          :key="off"
          data-star
          class="absolute rounded-full bg-[#EAEEF3]"
          :style="{
            left: s.x.toFixed(2) + '%',
            top: (s.y + off).toFixed(2) + '%',
            width: s.size + 'px',
            height: s.size + 'px',
            opacity: s.opacity,
            boxShadow: s.size > GLOW_MIN_PX ? '0 0 4px rgba(200,215,255,.7)' : 'none',
            animation: props.animated && s.twinkle ? `v2-twinkle ${s.dur.toFixed(1)}s ease-in-out ${s.delay.toFixed(1)}s infinite` : 'none',
          }"
        />
      </template>
    </div>
  </div>
</template>
