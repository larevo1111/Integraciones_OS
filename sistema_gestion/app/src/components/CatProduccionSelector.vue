<template>
  <q-chip
    clickable dense
    icon="category"
    class="tf-chip"
    :class="{ 'tf-chip-filled': seleccionada }"
    :style="seleccionada ? { background: 'var(--accent-muted)', borderColor: 'var(--accent)', color: 'var(--accent)' } : {}"
  >
    <span>{{ seleccionada ? seleccionada.nombre : 'Cat. producción' }}</span>
    <q-menu class="tf-menu" anchor="top middle" self="bottom middle" :offset="[0, 6]">
      <q-list dense style="min-width:180px;max-height:300px;overflow-y:auto">
        <q-item
          v-for="cp in categorias" :key="cp.id"
          clickable v-close-popup
          :active="modelValue === cp.id"
          @click="$emit('update:modelValue', modelValue === cp.id ? null : cp.id)"
        >
          <q-item-section>{{ cp.nombre }}</q-item-section>
        </q-item>
      </q-list>
    </q-menu>
  </q-chip>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: [Number, null], default: null },
  categorias: { type: Array, default: () => [] }
})
defineEmits(['update:modelValue'])

const seleccionada = computed(() =>
  props.categorias.find(c => c.id === props.modelValue) || null
)
</script>
