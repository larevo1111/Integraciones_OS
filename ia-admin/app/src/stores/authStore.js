import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token:   localStorage.getItem('ia_jwt') || null,
    usuario: JSON.parse(localStorage.getItem('ia_usuario') || 'null')
  }),

  getters: {
    estaAutenticado: s => !!s.token,
    esAdmin:         s => s.usuario?.rol === 'admin'
  },

  actions: {
    async autenticarGoogle(idToken) {
      const res = await fetch('/api/ia/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: idToken })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Error de autenticación')
      this.establecerSesion(data.token, data.usuario)
    },

    establecerSesion(token, usuario) {
      this.token   = token
      this.usuario = usuario
      localStorage.setItem('ia_jwt', token)
      localStorage.setItem('ia_usuario', JSON.stringify(usuario))
    },

    cerrarSesion() {
      this.token   = null
      this.usuario = null
      localStorage.removeItem('ia_jwt')
      localStorage.removeItem('ia_usuario')
    }
  }
})
