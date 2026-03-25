import { defineStore } from 'pinia'

const KEY_JWT     = 'gestion_jwt'
const KEY_USUARIO = 'gestion_usuario'
const KEY_EMPRESA = 'gestion_empresa'

export const useAuthStore = defineStore('auth', {
  state: () => {
    const token = localStorage.getItem(KEY_JWT) || null
    let usuario = JSON.parse(localStorage.getItem(KEY_USUARIO) || 'null')
    // Si hay token pero no hay usuario guardado, hidratarlo desde el payload JWT
    if (token && !usuario) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        if (payload.email) {
          usuario = { email: payload.email, nombre: payload.nombre, foto: payload.foto || '',
                      nivel: payload.nivel, tema: payload.tema || 'dark', perfil: payload.perfil || null }
          localStorage.setItem(KEY_USUARIO, JSON.stringify(usuario))
        }
      } catch (e) {}
    }
    return { token, usuario, empresa_activa: JSON.parse(localStorage.getItem(KEY_EMPRESA) || 'null') }
  },

  getters: {
    estaAutenticado: s => !!s.token,
    nivel:           s => s.usuario?.nivel || 1,
    tema:            s => s.usuario?.tema  || 'dark',
    perfil:          s => s.usuario?.perfil || null,
    esAdmin:         s => (s.usuario?.nivel || 1) >= 7
  },

  actions: {
    async autenticarGoogle(idToken) {
      const res  = await fetch('/api/gestion/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: idToken })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Error de autenticación')

      if (data.tipo === 'final') {
        this.establecerSesion(data.token, data.usuario, data.empresa)
        this._aplicarTema(data.usuario?.tema || 'dark')
      } else {
        // Temporal: guardar token Y usuario (para que esté disponible al seleccionar empresa)
        this.token   = data.token
        this.usuario = data.usuario || null
        localStorage.setItem(KEY_JWT,     data.token)
        localStorage.setItem(KEY_USUARIO, JSON.stringify(data.usuario || null))
      }
      return data
    },

    async seleccionarEmpresa(empresaUid) {
      const res  = await fetch('/api/gestion/auth/seleccionar_empresa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.token}` },
        body: JSON.stringify({ empresa_uid: empresaUid })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Error al seleccionar empresa')
      this.establecerSesion(data.token, data.usuario || this.usuario, data.empresa)
      return data
    },

    establecerSesion(token, usuario, empresa = null) {
      this.token          = token
      this.usuario        = usuario
      this.empresa_activa = empresa
      localStorage.setItem(KEY_JWT,     token)
      localStorage.setItem(KEY_USUARIO, JSON.stringify(usuario))
      if (empresa) localStorage.setItem(KEY_EMPRESA, JSON.stringify(empresa))
      else         localStorage.removeItem(KEY_EMPRESA)
    },

    async cambiarTema(tema) {
      if (!this.usuario) return
      this.usuario = { ...this.usuario, tema }
      localStorage.setItem(KEY_USUARIO, JSON.stringify(this.usuario))
      this._aplicarTema(tema)
      await fetch('/api/gestion/auth/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.token}` },
        body: JSON.stringify({ tema })
      }).catch(() => {})
    },

    _aplicarTema(tema) {
      document.documentElement.setAttribute('data-theme', tema)
    },

    inicializarTema() {
      this._aplicarTema(this.tema)
    },

    cerrarSesion() {
      this.token = null; this.usuario = null; this.empresa_activa = null
      localStorage.removeItem(KEY_JWT); localStorage.removeItem(KEY_USUARIO); localStorage.removeItem(KEY_EMPRESA)
    }
  }
})
