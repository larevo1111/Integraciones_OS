import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token:          localStorage.getItem('ia_jwt') || null,
    usuario:        JSON.parse(localStorage.getItem('ia_usuario') || 'null'),
    empresa_activa: JSON.parse(localStorage.getItem('ia_empresa') || 'null')
    // empresa_activa = {uid, nombre, siglas, rol_empresa}
  }),

  getters: {
    estaAutenticado: s => !!s.token,
    esAdmin:         s => (s.empresa_activa?.rol_empresa || s.usuario?.rol) === 'admin',
    rolActual:       s => s.empresa_activa?.rol_empresa || s.usuario?.rol || 'viewer',
    nivel:           s => s.usuario?.nivel || 1,
    puedeVer:        s => (nivelMin) => (s.usuario?.nivel || 1) >= nivelMin
  },

  actions: {
    /**
     * Paso 1: auth con Google.
     * Retorna {tipo:'final'} si hay 1 empresa (sesión lista),
     * o {tipo:'temporal', empresas:[...]} si hay múltiples (hay que seleccionar).
     */
    async autenticarGoogle(idToken) {
      const res = await fetch('/api/ia/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: idToken })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Error de autenticación')

      if (data.tipo === 'final') {
        this.establecerSesion(data.token, data.usuario, {
          uid:        data.empresa?.uid,
          nombre:     data.empresa?.nombre,
          siglas:     data.empresa?.siglas,
          rol_empresa: data.rol_empresa
        })
      } else {
        // Temporal: guardar solo el token temporal (sin empresa aún)
        this.token = data.token
        localStorage.setItem('ia_jwt', data.token)
      }

      return data // caller decide qué hacer según data.tipo
    },

    /**
     * Paso 2 (solo si hay múltiples empresas): seleccionar empresa.
     */
    async seleccionarEmpresa(empresaUid) {
      const res = await fetch('/api/ia/auth/seleccionar_empresa', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.token}`
        },
        body: JSON.stringify({ empresa_uid: empresaUid })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Error al seleccionar empresa')

      this.establecerSesion(data.token, this.usuario, {
        uid:         data.empresa?.uid,
        nombre:      data.empresa?.nombre,
        siglas:      data.empresa?.siglas,
        rol_empresa: data.rol_empresa
      })
      return data
    },

    establecerSesion(token, usuario, empresa = null) {
      this.token          = token
      this.usuario        = usuario
      this.empresa_activa = empresa
      localStorage.setItem('ia_jwt',     token)
      localStorage.setItem('ia_usuario', JSON.stringify(usuario))
      if (empresa) {
        localStorage.setItem('ia_empresa', JSON.stringify(empresa))
      } else {
        localStorage.removeItem('ia_empresa')
      }
    },

    establecerEmpresa(empresa) {
      this.empresa_activa = empresa
      if (empresa) {
        localStorage.setItem('ia_empresa', JSON.stringify(empresa))
      } else {
        localStorage.removeItem('ia_empresa')
      }
    },

    cerrarSesion() {
      this.token          = null
      this.usuario        = null
      this.empresa_activa = null
      localStorage.removeItem('ia_jwt')
      localStorage.removeItem('ia_usuario')
      localStorage.removeItem('ia_empresa')
    }
  }
})
