import { defineStore } from 'pinia'
import { api } from 'src/services/api'

export const useJornadaStore = defineStore('jornada', {
  state: () => ({
    jornada: null,       // jornada del día (con pausas[])
    tiposPausa: [],      // catálogo de tipos
    cargando: false,
    _timerInterval: null,
    timerSegundos: 0      // segundos trabajados (sin pausas cerradas)
  }),

  getters: {
    // Estado derivado: 1=sin jornada, 2=trabajando, 3=en pausa
    estado(s) {
      if (!s.jornada || !s.jornada.hora_inicio) return 1
      if (s.jornada.hora_fin) return 0 // finalizada
      const pausaActiva = (s.jornada.pausas || []).find(p => !p.hora_fin)
      return pausaActiva ? 3 : 2
    },
    pausaActiva(s) {
      if (!s.jornada) return null
      return (s.jornada.pausas || []).find(p => !p.hora_fin) || null
    },
    jornadaFinalizada(s) {
      return s.jornada && !!s.jornada.hora_fin
    }
  },

  actions: {
    async cargarHoy() {
      this.cargando = true
      try {
        const data = await api('/api/gestion/jornadas/hoy')
        this.jornada = data.jornada
        this._actualizarTimer()
      } finally { this.cargando = false }
    },

    async cargarTiposPausa() {
      const data = await api('/api/gestion/tipos-pausa')
      this.tiposPausa = data.tipos
    },

    async iniciarJornada() {
      const data = await api('/api/gestion/jornadas/iniciar', { method: 'POST' })
      this.jornada = data.jornada
      this._actualizarTimer()
      return data.jornada
    },

    async finalizarJornada() {
      if (!this.jornada) return
      const data = await api(`/api/gestion/jornadas/${this.jornada.id}/finalizar`, { method: 'PUT' })
      this.jornada = { ...this.jornada, ...data.jornada }
      this._detenerTimer()
      return data.jornada
    },

    async editarJornada(campos) {
      if (!this.jornada) return
      const data = await api(`/api/gestion/jornadas/${this.jornada.id}/editar`, {
        method: 'PUT',
        body: JSON.stringify(campos)
      })
      this.jornada = { ...this.jornada, ...data.jornada }
      this._actualizarTimer()
    },

    async iniciarPausa(tipos, observaciones) {
      if (!this.jornada) return
      const data = await api(`/api/gestion/jornadas/${this.jornada.id}/pausas/iniciar`, {
        method: 'POST',
        body: JSON.stringify({ tipos, observaciones: observaciones || null })
      })
      this.jornada.pausas = [...(this.jornada.pausas || []), data.pausa]
      this._detenerTimer()
      return data.pausa
    },

    async reanudar(pausaId) {
      if (!this.jornada) return
      const data = await api(`/api/gestion/jornadas/${this.jornada.id}/pausas/${pausaId}/reanudar`, { method: 'PUT' })
      const idx = this.jornada.pausas.findIndex(p => p.id === pausaId)
      if (idx >= 0) this.jornada.pausas[idx] = data.pausa
      this._actualizarTimer()
      return data.pausa
    },

    // --- Timer ---
    _actualizarTimer() {
      this._detenerTimer()
      if (this.estado !== 2) return // solo corre si está trabajando

      const calcular = () => {
        if (!this.jornada) return
        const inicio = new Date(this.jornada.hora_inicio).getTime()
        const ahora = Date.now()
        // Restar pausas cerradas
        let pausaMs = 0
        for (const p of (this.jornada.pausas || [])) {
          if (p.hora_fin) {
            pausaMs += new Date(p.hora_fin).getTime() - new Date(p.hora_inicio).getTime()
          }
        }
        this.timerSegundos = Math.max(0, Math.floor((ahora - inicio - pausaMs) / 1000))
      }

      calcular()
      this._timerInterval = setInterval(calcular, 1000)
    },

    _detenerTimer() {
      if (this._timerInterval) {
        clearInterval(this._timerInterval)
        this._timerInterval = null
      }
    }
  }
})
