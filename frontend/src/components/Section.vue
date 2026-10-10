<script setup lang="ts">
import { ref, useId } from 'vue'
const props = withDefaults(defineProps<{ title: string; startOpen?: boolean }>(), { startOpen: true })
const open = ref(props.startOpen)
const id = useId()
</script>

<template>
  <section class="sec">
    <h3>
      <button type="button" class="sec-btn" :aria-expanded="open" :aria-controls="id" @click="open = !open">
        <span class="chev" :class="{ rot: open }" aria-hidden="true">▸</span>{{ title }}
      </button>
    </h3>
    <div v-show="open" :id="id" class="sec-body"><slot /></div>
  </section>
</template>
