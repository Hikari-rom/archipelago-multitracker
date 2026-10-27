<script setup lang="ts">
// A Material Design icon (@mdi/js path), sized by the font and coloured by the text.
defineProps<{ path: string }>()
</script>

<template>
  <svg viewBox="0 0 24 24" class="size-[1.15em] shrink-0" aria-hidden="true" focusable="false"><path :d="path" fill="currentColor" /></svg>
</template>
