<template>
  <div class="tiptap-wrap" :class="{ 'tiptap-focused': isFocused, 'tiptap-readonly': !editable }">
    <!-- Mini toolbar — aparece al tener foco -->
    <div v-if="editable && isFocused && editor" class="tiptap-toolbar">
      <button
        v-for="btn in toolbarBtns"
        :key="btn.action"
        class="tb-btn"
        :class="{ active: btn.isActive?.() }"
        :title="btn.label"
        @mousedown.prevent="btn.run()"
      >
        <span class="material-icons" style="font-size:16px">{{ btn.icon }}</span>
      </button>
    </div>
    <editor-content :editor="editor" class="tiptap-content" />
    <!-- Input oculto para seleccionar archivos -->
    <input ref="fileInput" type="file" accept="image/*" style="display:none" @change="onFileSelected" />
  </div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount, computed } from 'vue'
import { useEditor, EditorContent, VueNodeViewRenderer } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import Image from '@tiptap/extension-image'
import { api } from 'src/services/api'
import ImageNodeView from './ImageNodeView.vue'

const props = defineProps({
  modelValue:  { type: String, default: '' },
  placeholder: { type: String, default: 'Escribe aquí...' },
  editable:    { type: Boolean, default: true },
  // Contexto para nombrar el archivo subido
  uploadTipo:   { type: String, default: 'general' },
  uploadItemId: { type: [Number, String], default: '' },
  uploadItemNombre: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const isFocused = ref(false)
const fileInput = ref(null)
let debounceTimer = null

const editor = useEditor({
  content: props.modelValue || '',
  editable: props.editable,
  extensions: [
    StarterKit.configure({
      heading: { levels: [2, 3] },
    }),
    Link.configure({ openOnClick: false, HTMLAttributes: { class: 'tiptap-link' } }),
    Placeholder.configure({ placeholder: props.placeholder }),
    Image.extend({
      addNodeView() { return VueNodeViewRenderer(ImageNodeView) },
    }).configure({ inline: false, allowBase64: false }),
  ],
  onUpdate({ editor: ed }) {
    clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      emit('update:modelValue', ed.getHTML())
    }, 1000)
  },
  onFocus() { isFocused.value = true },
  onBlur()  { isFocused.value = false },
  editorProps: {
    handleDrop(view, event) {
      const files = event.dataTransfer?.files
      if (files?.length && files[0].type.startsWith('image/')) {
        event.preventDefault()
        subirArchivo(files[0])
        return true
      }
      return false
    },
    handlePaste(view, event) {
      const items = event.clipboardData?.items
      if (!items) return false
      for (const item of items) {
        if (item.type.startsWith('image/')) {
          event.preventDefault()
          subirArchivo(item.getAsFile())
          return true
        }
      }
      return false
    },
  },
})

watch(() => props.modelValue, (val) => {
  if (!editor.value) return
  const current = editor.value.getHTML()
  if (val !== current) editor.value.commands.setContent(val || '', false)
})

watch(() => props.editable, (val) => {
  if (editor.value) editor.value.setEditable(val)
})

onBeforeUnmount(() => {
  clearTimeout(debounceTimer)
  editor.value?.destroy()
})

// ── Upload ──
async function subirArchivo(file) {
  if (!file || !file.type.startsWith('image/')) return
  if (file.size > 10 * 1024 * 1024) { alert('Imagen demasiado grande (máx 10 MB)'); return }

  const formData = new FormData()
  formData.append('file', file)
  formData.append('tipo', props.uploadTipo)
  formData.append('item_id', props.uploadItemId)
  formData.append('item_nombre', props.uploadItemNombre)

  try {
    const resp = await fetch('/api/gestion/upload', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('gestion_jwt')}` },
      body: formData,
    })
    const data = await resp.json()
    if (data.url && editor.value) {
      editor.value.chain().focus().setImage({ src: data.url }).run()
    }
  } catch (e) { console.error('Error subiendo imagen:', e) }
}

function abrirSelectorArchivo() {
  fileInput.value?.click()
}

function onFileSelected(e) {
  const file = e.target.files?.[0]
  if (file) subirArchivo(file)
  e.target.value = '' // reset para poder subir el mismo archivo otra vez
}

const toolbarBtns = computed(() => {
  if (!editor.value) return []
  const e = editor.value
  return [
    { action: 'bold', icon: 'format_bold', label: 'Negrita', run: () => e.chain().focus().toggleBold().run(), isActive: () => e.isActive('bold') },
    { action: 'italic', icon: 'format_italic', label: 'Cursiva', run: () => e.chain().focus().toggleItalic().run(), isActive: () => e.isActive('italic') },
    { action: 'h2', icon: 'title', label: 'Título', run: () => e.chain().focus().toggleHeading({ level: 2 }).run(), isActive: () => e.isActive('heading', { level: 2 }) },
    { action: 'h3', icon: 'format_size', label: 'Subtítulo', run: () => e.chain().focus().toggleHeading({ level: 3 }).run(), isActive: () => e.isActive('heading', { level: 3 }) },
    { action: 'bullet', icon: 'format_list_bulleted', label: 'Lista', run: () => e.chain().focus().toggleBulletList().run(), isActive: () => e.isActive('bulletList') },
    { action: 'ordered', icon: 'format_list_numbered', label: 'Lista numerada', run: () => e.chain().focus().toggleOrderedList().run(), isActive: () => e.isActive('orderedList') },
    { action: 'blockquote', icon: 'format_quote', label: 'Cita', run: () => e.chain().focus().toggleBlockquote().run(), isActive: () => e.isActive('blockquote') },
    { action: 'code', icon: 'code', label: 'Código', run: () => e.chain().focus().toggleCodeBlock().run(), isActive: () => e.isActive('codeBlock') },
    { action: 'image', icon: 'image', label: 'Imagen', run: () => abrirSelectorArchivo() },
  ]
})
</script>

<style scoped>
.tiptap-wrap {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  transition: border-color 150ms;
  overflow: hidden;
}
.tiptap-wrap.tiptap-focused { border-color: var(--accent); }
.tiptap-wrap.tiptap-readonly { border-color: transparent; background: transparent; }

/* Toolbar */
.tiptap-toolbar {
  display: flex; gap: 2px; padding: 4px 6px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-card-hover);
  flex-wrap: wrap;
}
.tb-btn {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; border-radius: var(--radius-sm);
  border: none; background: transparent; color: var(--text-tertiary);
  cursor: pointer; transition: all 80ms;
}
.tb-btn:hover { background: var(--bg-row-hover); color: var(--text-primary); }
.tb-btn.active { color: var(--accent); background: var(--accent-muted); }

/* Editor content */
.tiptap-content { padding: 10px 12px; min-height: 120px; }
.tiptap-content :deep(.tiptap) {
  outline: none;
  font-size: 13px; line-height: 1.6;
  color: var(--text-primary);
  font-family: var(--font-sans);
}
.tiptap-content :deep(.tiptap p) { margin: 0 0 8px; }
.tiptap-content :deep(.tiptap p:last-child) { margin-bottom: 0; }
.tiptap-content :deep(.tiptap h2) { font-size: 17px; font-weight: 600; margin: 16px 0 6px; color: var(--text-primary); }
.tiptap-content :deep(.tiptap h3) { font-size: 14px; font-weight: 600; margin: 12px 0 4px; color: var(--text-primary); }
.tiptap-content :deep(.tiptap ul),
.tiptap-content :deep(.tiptap ol) { padding-left: 20px; margin: 4px 0 8px; }
.tiptap-content :deep(.tiptap li) { margin: 2px 0; }
.tiptap-content :deep(.tiptap blockquote) {
  border-left: 3px solid var(--accent); padding-left: 12px; margin: 8px 0;
  color: var(--text-secondary); font-style: italic;
}
.tiptap-content :deep(.tiptap code) {
  background: var(--bg-card-hover); padding: 2px 5px; border-radius: 3px;
  font-size: 12px; font-family: monospace; color: var(--accent);
}
.tiptap-content :deep(.tiptap pre) {
  background: var(--bg-card-hover); padding: 10px 12px; border-radius: var(--radius-md);
  font-size: 12px; font-family: monospace; overflow-x: auto; margin: 8px 0;
  color: var(--text-secondary);
}
.tiptap-content :deep(.tiptap a),
.tiptap-content :deep(.tiptap .tiptap-link) { color: var(--accent); text-decoration: underline; }
.tiptap-content :deep(.tiptap .is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left; color: var(--text-tertiary); pointer-events: none; height: 0;
  font-style: italic;
}
.tiptap-content :deep(.tiptap strong) { font-weight: 600; }

/* Imágenes dentro del editor */
.tiptap-content :deep(.tiptap img) {
  max-width: 100%; height: auto; border-radius: var(--radius-md);
  margin: 8px 0; display: block;
}

@media (max-width: 600px) {
  .tiptap-content { min-height: 80px; padding: 8px 10px; }
  .tb-btn { width: 32px; height: 32px; }
}
</style>
