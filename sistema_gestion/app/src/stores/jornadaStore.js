import { defineStore } from 'pinia'
import { api } from 'src/services/api'

export const useJornadaStore = defineStore('jornada', {
  state: () => ({
    jornada: null,       // jornada del día (con pausas[])
    tiposPausa: [],      // catálogo de tipos
    cargando: false
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
      } finally { this.cargando = false }
    },

    async cargarTiposPausa() {
      const data = await api('/api/gestion/tipos-pausa')
      this.tiposPausa = data.tipos
    },

    async iniciarJornada(horaInicio) {
      const body = horaInicio ? JSON.stringify({ hora_inicio: horaInicio }) : undefined
      const data = await api('/api/gestion/jornadas/iniciar', { method: 'POST', body })
      this.jornada = data.jornada
      return data.jornada
    },

    async finalizarJornada(horaFin) {
      if (!this.jornada) return null
      const body = horaFin ? JSON.stringify({ hora_fin: horaFin }) : undefined
      const data = await api(`/api/gestion/jornadas/${this.jornada.id}/finalizar`, { method: 'PUT', body })
      this.jornada = { ...this.jornada, ...data.jornada }
      return { jornada: data.jornada, tareasPausadas: data.tareas_pausadas || [] }
    },

    async reabrirJornada() {
      if (!this.jornada) return
      const data = await api(`/api/gestion/jornadas/${this.jornada.id}/reabrir`, { method: 'PUT' })
      this.jornada = data.jornada
      return data.jornada
    },

    async editarJornada(campos) {
      if (!this.jornada) return
      const data = await api(`/api/gestion/jornadas/${this.jornada.id}/editar`, {
        method: 'PUT',
        body: JSON.stringify(campos)
      })
      this.jornada = { ...this.jornada, ...data.jornada }
    },

    async iniciarPausa(tipos, observaciones, horaInicio, horaFin) {
      if (!this.jornada) return
      const body = { tipos, observaciones: observaciones || null }
      if (horaInicio) body.hora_inicio = horaInicio
      if (horaFin)    body.hora_fin    = horaFin
      const data = await api(`/api/gestion/jornadas/${this.jornada.id}/pausas/iniciar`, {
        method: 'POST', body: JSON.stringify(body)
      })
      this.jornada.pausas = [...(this.jornada.pausas || []), data.pausa]
      return data.pausa
    },

    async reanudar(pausaId, horaFin) {
      if (!this.jornada) return
      const body = horaFin ? JSON.stringify({ hora_fin: horaFin }) : undefined
      const data = await api(`/api/gestion/jornadas/${this.jornada.id}/pausas/${pausaId}/reanudar`, { method: 'PUT', body })
      const idx = this.jornada.pausas.findIndex(p => p.id === pausaId)
      if (idx >= 0) this.jornada.pausas[idx] = data.pausa
      return data.pausa
    }
  }
})
