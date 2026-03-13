<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1 class="page-title">Usuarios</h1>
      <p class="page-subtitle">Personas con acceso al panel de administración</p>
    </div>

    <div class="page-content">
      <div class="tabla-wrap" style="max-width:700px">
        <div class="tabla-header">
          <span class="tabla-titulo">{{ usuarios.length }} usuarios</span>
          <button class="btn btn-primary" @click="abrirNuevo">
            <PlusIcon :size="13" /> Agregar
          </button>
        </div>

        <div v-if="cargando" class="empty-state"><p>Cargando...</p></div>
        <table v-else class="os-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Nombre</th>
              <th>Rol</th>
              <th>Activo</th>
              <th>Creado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in usuarios" :key="u.email">
              <td>{{ u.email }}</td>
              <td><strong>{{ u.nombre }}</strong></td>
              <td>
                <span class="badge" :class="u.rol === 'admin' ? 'badge-info' : 'badge-neutral'">{{ u.rol }}</span>
              </td>
              <td>
                <label class="toggle" @click.stop>
                  <input type="checkbox" :checked="u.activo" @change="toggleActivo(u)" />
                  <div class="toggle-track"></div>
                  <div class="toggle-thumb"></div>
                </label>
              </td>
              <td class="mono" style="font-size:12px;color:var(--text-tertiary)">{{ fechaCorta(u.created_at) }}</td>
              <td>
                <button class="btn-icon" @click="seleccionar(u)" title="Editar">
                  <PencilIcon :size="13" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Nota sobre Cloudflare -->
      <div class="card" style="max-width:700px;margin-top:16px;background:var(--color-info-bg);border-color:rgba(37,99,235,0.15)">
        <div style="display:flex;gap:10px;align-items:flex-start">
          <ShieldCheckIcon :size="16" style="color:var(--color-info);margin-top:2px;flex-shrink:0" />
          <div>
            <div style="font-size:13px;font-weight:600;color:var(--color-info);margin-bottom:4px">Autenticación vía Cloudflare Access</div>
            <div style="font-size:13px;color:var(--text-secondary);line-height:1.6">
              El acceso al sitio está protegido por Cloudflare Access (Zero Trust). Solo los emails
              en la política de Cloudflare pueden ingresar — esta tabla es solo para nombres y roles dentro de la app.
              Si un email pasa Cloudflare pero no está aquí, se le asigna rol <strong>viewer</strong> automáticamente.
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Overlay -->
    <transition name="overlay">
      <div v-if="seleccionado" class="overlay" @click="cerrar" />
    </transition>

    <!-- Panel lateral -->
    <transition name="panel">
      <div v-if="seleccionado" class="side-panel" style="width:360px">
        <div class="side-panel-header">
          <span class="side-panel-title">{{ esNuevo ? 'Nuevo usuario' : seleccionado.email }}</span>
          <button class="btn-icon" @click="cerrar"><XIcon :size="15" /></button>
        </div>
        <div class="side-panel-body">
          <div class="input-group">
            <label class="input-label">Email *</label>
            <input class="input-field" v-model="form.email" placeholder="nombre@origensilvestre.com" :readonly="!esNuevo" />
          </div>
          <div class="input-group">
            <label class="input-label">Nombre *</label>
            <input class="input-field" v-model="form.nombre" placeholder="Santiago" />
          </div>
          <div class="input-group">
            <label class="input-label">Rol</label>
            <select class="input-field" v-model="form.rol">
              <option value="admin">admin — acceso completo</option>
              <option value="viewer">viewer — solo lectura</option>
            </select>
          </div>
          <div class="input-group" style="display:flex;align-items:center;gap:10px;margin-top:4px">
            <label class="toggle">
              <input type="checkbox" v-model="form.activo" />
              <div class="toggle-track"></div>
              <div class="toggle-thumb"></div>
            </label>
            <span class="input-label" style="margin:0">Activo</span>
          </div>
        </div>
        <div class="side-panel-footer">
          <button v-if="!esNuevo" class="btn btn-danger" @click="eliminar">Eliminar</button>
          <button class="btn btn-secondary" @click="cerrar">Cancelar</button>
          <button class="btn btn-primary" @click="guardar" :disabled="guardando">
            {{ guardando ? 'Guardando...' : 'Guardar' }}
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { PlusIcon, PencilIcon, XIcon, ShieldCheckIcon } from 'lucide-vue-next'

const usuarios = ref([])
const cargando = ref(true)
const seleccionado = ref(null)
const esNuevo = ref(false)
const form = ref({})
const guardando = ref(false)

async function cargar() {
  cargando.value = true
  try {
    const res = await fetch('/api/ia/usuarios')
    usuarios.value = await res.json()
  } catch (e) { usuarios.value = [] }
  cargando.value = false
}

function seleccionar(u) {
  esNuevo.value = false
  seleccionado.value = u
  form.value = { ...u, activo: !!u.activo }
}

function abrirNuevo() {
  esNuevo.value = true
  seleccionado.value = { email: '' }
  form.value = { email: '', nombre: '', rol: 'viewer', activo: true }
}

function cerrar() { seleccionado.value = null; form.value = {} }

async function toggleActivo(u) {
  try {
    await fetch(`/api/ia/usuarios/${encodeURIComponent(u.email)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ activo: !u.activo })
    })
    u.activo = !u.activo
  } catch (e) { alert('Error') }
}

async function guardar() {
  guardando.value = true
  try {
    const url = esNuevo.value ? '/api/ia/usuarios' : `/api/ia/usuarios/${encodeURIComponent(form.value.email)}`
    const method = esNuevo.value ? 'POST' : 'PUT'
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value)
    })
    if (!res.ok) throw new Error(await res.text())
    cerrar(); await cargar()
  } catch (e) { alert('Error: ' + e.message) }
  guardando.value = false
}

async function eliminar() {
  if (!confirm(`¿Eliminar usuario "${seleccionado.value.email}"?`)) return
  try {
    await fetch(`/api/ia/usuarios/${encodeURIComponent(seleccionado.value.email)}`, { method: 'DELETE' })
    cerrar(); await cargar()
  } catch (e) { alert('Error') }
}

function fechaCorta(ts) {
  if (!ts) return '—'
  return new Date(ts).toLocaleDateString('es-CO')
}

onMounted(cargar)
</script>
