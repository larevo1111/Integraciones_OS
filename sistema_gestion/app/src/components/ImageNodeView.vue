<template>
  <node-view-wrapper class="image-nv-wrap" :class="{ selected: selected }">
    <img :src="node.attrs.src" :alt="node.attrs.alt || ''" />
    <button
      v-if="editor.isEditable"
      class="image-del-btn"
      title="Eliminar imagen"
      @mousedown.prevent.stop="deleteNode()"
    >
      <span class="material-icons">close</span>
    </button>
  </node-view-wrapper>
</template>

<script setup>
import { NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'

const props = defineProps(nodeViewProps)
</script>

<style scoped>
.image-nv-wrap {
  position: relative;
  display: block;
  max-width: 100%;
  margin: 8px 0;
}
.image-nv-wrap img {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-md);
  display: block;
}
.image-del-btn {
  position: absolute;
  top: 6px;
  right: 6px;
  display: none;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  border: none;
  color: #fff;
  cursor: pointer;
  padding: 0;
  z-index: 10;
  transition: background 100ms;
}
.image-del-btn:hover { background: rgba(200, 30, 30, 0.85); }
.image-del-btn .material-icons { font-size: 14px; }

/* Mostrar botón al hacer hover sobre el wrapper o cuando está seleccionado */
.image-nv-wrap:hover .image-del-btn,
.image-nv-wrap.selected .image-del-btn {
  display: flex;
}
</style>
