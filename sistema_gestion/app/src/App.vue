<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from 'src/stores/authStore'

const auth = useAuthStore()
onMounted(() => auth.inicializarTema())
</script>
