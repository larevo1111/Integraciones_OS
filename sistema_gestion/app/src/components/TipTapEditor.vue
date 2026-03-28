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
  </div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount, computed } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'

const props = defineProps({
  modelValue:  { type: String, default: '' },
  placeholder: { type: String, default: 'Escribe aquí...' },
  editable:    { type: Boolean, default: true },
})
const emit = defineEmits(['update:modelValue'])

const isFocused = ref(false)
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
  ],
  onUpdate({ editor: ed }) {
    clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      emit('update:modelValue', ed.getHTML())
    }, 1000)
  },
  onFocus() { isFocused.value = true },
  onBlur()  { isFocused.value = false },
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

@media (max-width: 600px) {
  .tiptap-content { min-height: 80px; padding: 8px 10px; }
  .tb-btn { width: 32px; height: 32px; }
}
</style>
