<template>
  <!-- LOGIN -->
  <div v-if="!autenticado" class="inv-login">
    <div class="inv-login-card">
      <div class="inv-login-logo">I</div>
      <h1 class="inv-login-title">Inventario OS</h1>
      <p class="inv-login-subtitle">Conteo de inventario físico</p>
      <div id="google-signin-btn" class="inv-login-btn-wrap"></div>
      <p v-if="loginError" class="inv-login-error">{{ loginError }}</p>
      <p v-if="loginCargando" class="inv-login-loading">Autenticando...</p>
    </div>
  </div>

  <!-- APP -->
  <div v-else class="inv-app" :class="{ 'panel-open': panelAbierto }">

    <!-- SIDE PANEL RETRÁCTIL — Inventarios -->
    <aside class="inv-panel" :class="{ open: panelAbierto }">
      <div class="inv-panel-header">
        <span class="inv-panel-title">Inventarios</span>
        <button v-if="puede('nuevo_inventario')" class="inv-panel-add" @click="mostrarNuevoInv = true" title="Nuevo inventario">
          <span class="material-icons" style="font-size:14px">add</span>
        </button>
        <button class="action-btn" @click="panelAbierto = false"><span class="material-icons" style="font-size:18px">chevron_left</span></button>
      </div>
      <div class="inv-panel-list">
        <div v-for="f in fechasInventario" :key="f.fecha_inventario" class="inv-panel-item" :class="{ active: FECHA === f.fecha_inventario }">
          <div class="inv-panel-item-main" @click="cambiarFecha(f.fecha_inventario)">
            <div class="inv-panel-item-fecha">{{ formatFechaCorta(f.fecha_inventario) }}</div>
            <div class="inv-panel-item-stats">
              <span>{{ f.inventariables }} artículos</span>
              <span class="inv-panel-item-pct">{{ f.contados }}/{{ f.inventariables }}</span>
            </div>
          </div>
          <div v-if="puede('cerrar_conteo') && FECHA === f.fecha_inventario" class="inv-panel-item-actions">
            <button v-if="puede('nuevo_inventario')" class="inv-panel-action" :class="{ 'inv-panel-action-spin': calculandoTeorico }" :disabled="calculandoTeorico || estadoCierre.inventario_cerrado" @click.stop="calcularTeorico" :title="estadoTeorico && estadoTeorico.calculado ? 'Recalcular teórico (' + formatFechaHora(estadoTeorico.calculado_en) + ')' : 'Calcular inventario teórico'">
              <span class="material-icons" :class="{ spin: calculandoTeorico }" style="font-size:13px">analytics</span>
            </button>
            <button v-if="puede('cerrar_conteo') && !estadoCierre.conteo_cerrado" class="inv-panel-action" @click.stop="confirmarCerrarConteo" title="Cerrar conteo físico">
              <span class="material-icons" style="font-size:13px">lock</span>
            </button>
            <button v-if="puede('reabrir_conteo') && estadoCierre.conteo_cerrado && !estadoCierre.inventario_cerrado" class="inv-panel-action" @click.stop="confirmarReabrirConteo" title="Reabrir conteo físico">
              <span class="material-icons" style="font-size:13px">lock_open</span>
            </button>
            <button v-if="puede('cerrar_inventario') && estadoCierre.conteo_cerrado && !estadoCierre.inventario_cerrado" class="inv-panel-action inv-panel-action-warn" @click.stop="confirmarCerrarInventario" title="Cerrar inventario completo">
              <span class="material-icons" style="font-size:13px">verified</span>
            </button>
            <button v-if="puede('reiniciar_inventario') && !estadoCierre.conteo_cerrado" class="inv-panel-action inv-panel-action-danger" @click.stop="confirmarReiniciar" title="Reiniciar conteos (borra TODO — solo Admin)">
              <span class="material-icons" style="font-size:13px">restart_alt</span>
            </button>
            <button v-if="puede('eliminar_inventario') && !estadoCierre.inventario_cerrado" class="inv-panel-action inv-panel-action-danger" @click.stop="confirmarEliminar" title="Eliminar inventario">
              <span class="material-icons" style="font-size:13px">delete_outline</span>
            </button>
          </div>
        </div>
        <div v-if="!fechasInventario.length" class="inv-panel-empty">Sin inventarios</div>
      </div>
      <div class="inv-panel-logout" @click="cerrarSesion">
        <span class="material-icons" style="font-size:15px">logout</span>
        Cerrar sesión
      </div>
    </aside>

    <!-- MODAL NUEVO INVENTARIO -->
    <div v-if="mostrarNuevoInv" class="inv-overlay" @click.self="mostrarNuevoInv = false">
      <div class="inv-modal inv-modal-sm">
        <div class="inv-modal-header">
          <span>Nuevo inventario</span>
          <button class="action-btn" @click="mostrarNuevoInv = false"><span class="material-icons">close</span></button>
        </div>
        <div class="inv-modal-body">
          <label class="inv-form-label">Fecha de corte del inventario</label>
          <input v-model="nuevaFechaInv" type="date" class="inv-form-input">
          <p class="inv-form-hint">Se generarán los artículos inventariables con el stock teórico a esta fecha.</p>
          <button class="inv-btn-primary" :disabled="!nuevaFechaInv || creandoInv" @click="crearInventario">
            {{ creandoInv ? 'Creando...' : 'Crear inventario' }}
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL CONFIRMAR REINICIAR (con doble confirmación) -->
    <div v-if="mostrarConfirmReiniciar" class="inv-overlay" @click.self="cerrarModalReiniciar">
      <div class="inv-modal inv-modal-sm">
        <div class="inv-modal-header inv-modal-header-warn">
          <span class="material-icons" style="font-size:18px;color:#f87171">warning</span>
          <span>Reiniciar inventario</span>
          <button class="action-btn" @click="cerrarModalReiniciar"><span class="material-icons">close</span></button>
        </div>
        <div class="inv-modal-body">
          <p class="alerta-mensaje" style="color:#f87171"><strong>⚠️ Acción destructiva e irreversible</strong></p>
          <p class="alerta-mensaje">Se borrarán <strong>TODOS los conteos físicos</strong>, notas y fotos del inventario <strong>{{ fechaDisplay }}</strong>. Los artículos se mantienen pero todos los valores vuelven a pendiente.</p>
          <p class="alerta-mensaje" style="color:var(--text-tertiary);font-size:11px">Para confirmar, escribí <strong style="color:#f87171">REINICIAR</strong> abajo:</p>
          <input v-model="textoConfirmReiniciar" type="text" placeholder="Escribir REINICIAR" class="inv-form-input" style="margin-bottom:10px;text-align:center;font-weight:600;letter-spacing:2px">
          <div class="alerta-btns">
            <button class="alerta-btn-confirmar" @click="cerrarModalReiniciar">Cancelar</button>
            <button class="inv-btn-danger" :disabled="textoConfirmReiniciar !== 'REINICIAR'" @click="ejecutarReiniciar">Reiniciar conteos</button>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL CONFIRMAR CERRAR -->
    <!-- MODAL: Cerrar conteo físico -->
    <div v-if="mostrarConfirmCerrarConteo" class="inv-overlay" @click.self="mostrarConfirmCerrarConteo = false">
      <div class="inv-modal inv-modal-sm">
        <div class="inv-modal-header">
          <span class="material-icons" style="font-size:18px;color:var(--accent)">lock</span>
          <span>Cerrar conteo físico</span>
          <button class="action-btn" @click="mostrarConfirmCerrarConteo = false"><span class="material-icons">close</span></button>
        </div>
        <div class="inv-modal-body">
          <p class="alerta-mensaje">Se bloquea la edición de conteos físicos. La pestaña <strong>Gestión</strong> sigue funcionando para analizar y resolver inconsistencias.</p>
          <p class="alerta-mensaje" style="color:var(--text-tertiary);font-size:11px">Podés reabrir el conteo después si fuera necesario.</p>
          <div class="alerta-btns">
            <button class="alerta-btn-confirmar" @click="mostrarConfirmCerrarConteo = false">Cancelar</button>
            <button class="inv-btn-primary" @click="ejecutarCerrarConteo">Cerrar conteo</button>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL: Cerrar inventario completo -->
    <div v-if="mostrarConfirmCerrarInventario" class="inv-overlay" @click.self="mostrarConfirmCerrarInventario = false">
      <div class="inv-modal inv-modal-sm">
        <div class="inv-modal-header inv-modal-header-warn">
          <span class="material-icons" style="font-size:18px;color:#fbbf24">verified</span>
          <span>Cerrar inventario completo</span>
          <button class="action-btn" @click="mostrarConfirmCerrarInventario = false"><span class="material-icons">close</span></button>
        </div>
        <div class="inv-modal-body">
          <p class="alerta-mensaje"><strong>Esta acción cierra TODO el inventario.</strong></p>
          <p class="alerta-mensaje" style="color:var(--text-tertiary);font-size:11px">Ya no se podrá modificar ningún dato: ni conteos, ni gestión de inconsistencias, ni resoluciones, ni ajustes. Solo se podrá ver el informe final.</p>
          <div class="alerta-btns">
            <button class="alerta-btn-confirmar" @click="mostrarConfirmCerrarInventario = false">Cancelar</button>
            <button class="inv-btn-primary" style="background:#fbbf24" @click="ejecutarCerrarInventario">Cerrar inventario completo</button>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL: Reabrir conteo -->
    <div v-if="mostrarConfirmReabrirConteo" class="inv-overlay" @click.self="mostrarConfirmReabrirConteo = false">
      <div class="inv-modal inv-modal-sm">
        <div class="inv-modal-header">
          <span class="material-icons" style="font-size:18px;color:var(--accent)">lock_open</span>
          <span>Reabrir conteo físico</span>
          <button class="action-btn" @click="mostrarConfirmReabrirConteo = false"><span class="material-icons">close</span></button>
        </div>
        <div class="inv-modal-body">
          <p class="alerta-mensaje">Se permitirá editar conteos físicos nuevamente.</p>
          <div class="alerta-btns">
            <button class="alerta-btn-confirmar" @click="mostrarConfirmReabrirConteo = false">Cancelar</button>
            <button class="inv-btn-primary" @click="ejecutarReabrirConteo">Reabrir conteo</button>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL CONFIRMAR ELIMINAR -->
    <div v-if="mostrarConfirmEliminar" class="inv-overlay" @click.self="mostrarConfirmEliminar = false">
      <div class="inv-modal inv-modal-sm">
        <div class="inv-modal-header inv-modal-header-warn">
          <span class="material-icons" style="font-size:18px;color:var(--color-error)">delete_forever</span>
          <span>Eliminar inventario</span>
          <button class="action-btn" @click="mostrarConfirmEliminar = false"><span class="material-icons">close</span></button>
        </div>
        <div class="inv-modal-body">
          <p class="alerta-mensaje">Se eliminarán TODOS los registros del inventario {{ fechaDisplay }}, incluyendo conteos, notas y fotos. Esta acción es irreversible.</p>
          <div class="alerta-btns">
            <button class="alerta-btn-confirmar" @click="mostrarConfirmEliminar = false">Cancelar</button>
            <button class="inv-btn-danger" @click="ejecutarEliminar">Eliminar inventario</button>
          </div>
        </div>
      </div>
    </div>

    <!-- MAIN CONTENT -->
    <div class="inv-content">

      <!-- HEADER -->
      <div class="inv-header">
        <div class="inv-header-left">
          <button v-if="!panelAbierto" class="inv-panel-toggle" @click="panelAbierto = true" title="Inventarios">
            <span class="material-icons" style="font-size:18px">menu</span>
          </button>
          <div class="inv-avatar">{{ iniciales }}</div>
          <div class="inv-user-info">
            <span class="inv-user-name">{{ usuario }}</span>
            <span class="inv-title">
              Inventario {{ fechaDisplay }}
              <span v-if="estadoCierre.inventario_cerrado" class="cierre-badge cierre-badge-full" title="Inventario cerrado completamente">
                <span class="material-icons" style="font-size:11px">verified</span> CERRADO
              </span>
              <span v-else-if="estadoCierre.conteo_cerrado" class="cierre-badge cierre-badge-conteo" title="Conteo físico cerrado">
                <span class="material-icons" style="font-size:11px">lock</span> CONTEO CERRADO
              </span>
            </span>
          </div>
        </div>
        <div class="inv-header-right">
          <div class="inv-clock" id="inv-clock"></div>
          <div class="inv-progress-wrap">
            <div class="inv-progress-track">
              <div class="inv-progress-ok" :style="{ width: pctOk + '%' }"></div>
              <div class="inv-progress-diff" :style="{ width: pctDiff + '%' }"></div>
            </div>
            <span class="inv-progress-text">{{ resumen.contados || 0 }} / {{ resumen.total || 0 }}</span>
          </div>
        </div>
      </div>

      <!-- TOOLBAR -->
      <div class="inv-toolbar">
        <div class="inv-search-box">
          <span class="material-icons inv-search-icon">search</span>
          <input v-model="busqueda" class="inv-search-input" type="text" placeholder="Buscar por nombre o código..." @input="debounceSearch">
        </div>
        <button v-if="puede('asignar_articulo')" class="inv-btn-sync" :class="{ syncing: syncEstado === 'exportando' || syncEstado === 'importando' }" :disabled="syncEstado === 'exportando' || syncEstado === 'importando'" @click="syncEffi" :title="syncMensaje || 'Actualizar catálogo de artículos desde Effi'">
          <span class="material-icons" :class="{ 'spin': syncEstado === 'exportando' || syncEstado === 'importando' }" style="font-size:16px">sync</span>
          <span>{{ syncTexto }}</span>
        </button>
        <button class="inv-btn-scan">
          <span class="material-icons" style="font-size:16px">qr_code_scanner</span>
          Escanear
        </button>
      </div>

      <!-- TAB SWITCHER -->
      <div v-if="puede('ver_gestion')" class="inv-tabs">
        <button class="inv-tab" :class="{ active: vistaActiva === 'conteo' }" @click="vistaActiva = 'conteo'">
          <span class="material-icons" style="font-size:15px">inventory_2</span> Conteo
        </button>
        <button class="inv-tab" :class="{ active: vistaActiva === 'gestion' }" @click="vistaActiva = 'gestion'; cargarGestion()">
          <span class="material-icons" style="font-size:15px">analytics</span> Gestión
        </button>
        <button class="inv-tab" :class="{ active: vistaActiva === 'costos' }" @click="vistaActiva = 'costos'; cargarCostos()">
          <span class="material-icons" style="font-size:15px">attach_money</span> Costos
        </button>
      </div>

      <!-- ═══ VISTA CONTEO ═══ -->
      <template v-if="vistaActiva === 'conteo'">

      <!-- FILTROS + BODEGAS -->
      <div class="inv-filters-row">
        <!-- Filtros estado -->
        <button v-for="f in filtros" :key="f.key" class="inv-pill" :class="{ active: filtroActivo === f.key }" @click="filtroActivo = f.key; cargarArticulos()">
          {{ f.label }}<span class="inv-pill-count">{{ f.count }}</span>
        </button>

        <span class="inv-separator"></span>

        <!-- Bodegas label + chips -->
        <span class="inv-bodegas-label">Bodegas</span>
        <button class="inv-pill inv-pill-bodega" :class="{ active: bodegaActiva === null }" @click="seleccionarBodega(null)">
          Todas
        </button>
        <button
          v-for="b in bodegasConStock"
          :key="b.bodega"
          class="inv-pill inv-pill-bodega"
          :class="{ active: bodegaActiva === b.bodega }"
          @click="seleccionarBodega(b.bodega)"
        >
          {{ b.bodega }}<span class="inv-pill-count">{{ b.total }}</span>
        </button>

        <!-- + para más bodegas -->
        <div class="inv-bodega-add-wrap">
          <button class="inv-bodega-add-btn" @click.stop="mostrarListaBodegas = !mostrarListaBodegas" title="Más bodegas">
            <span class="material-icons" style="font-size:14px">add</span>
          </button>
          <div v-if="mostrarListaBodegas" class="inv-bodega-dropdown" @click.stop>
            <div class="inv-bodega-dropdown-title">Otras bodegas</div>
            <div v-for="b in bodegasSinStock" :key="b.bodega" class="inv-bodega-dropdown-item" @click="seleccionarBodega(b.bodega); mostrarListaBodegas = false">
              {{ b.bodega }}
            </div>
            <div v-if="!bodegasSinStock.length" class="inv-bodega-dropdown-empty">Todas las bodegas con stock ya están visibles</div>
          </div>
        </div>
      </div>

    <!-- TABLA -->
    <div class="inv-table-container">
      <table class="inv-table">
        <colgroup>
          <col class="col-status">
          <col class="col-id">
          <col class="col-articulo">
          <col class="col-categoria">
          <col class="col-conteo">
        </colgroup>
        <thead>
          <tr>
            <th class="th th-nosort"></th>
            <th v-for="col in columns" :key="col.key" class="th"
                :class="{ 'th-sorted': sortKey === col.key, 'th-filtered': hasFilter(col.key), 'th-popup-open': colPopup === col.key }"
                @click.stop="openColPopup(col.key, $event)">
              <div class="th-inner">
                <span class="th-label">{{ col.label }}</span>
                <span v-if="sortKey === col.key" class="material-icons sort-icon">{{ sortDir === 'asc' ? 'keyboard_arrow_up' : 'keyboard_arrow_down' }}</span>
                <span v-if="hasFilter(col.key)" class="th-filter-dot"></span>
              </div>
            </th>
            <th class="th th-nosort th-conteo">Conteo</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in sortedRows" :key="a.id" :class="clasesFila(a)">
            <td class="td td-center"><span class="status-dot" :class="claseDot(a)"></span></td>
            <td class="td cell-id">{{ a.id_effi }}</td>
            <td class="td cell-articulo">
              <div class="articulo-line1">
                <span class="articulo-nombre">{{ a.nombre }}</span>
                <span v-if="a.unidad" class="unit-tag">{{ a.unidad }}</span>
              </div>
              <div class="articulo-teorico-movil">TEO {{ fmtNum(a.inventario_teorico) }}</div>
            </td>
            <td class="td cell-categoria" :title="grupoNombre(a.grupo)">
              <span class="grupo-tag grupo-tag-full" :class="'grupo-' + (a.grupo || 'MP').toLowerCase()">{{ grupoNombre(a.grupo) }}</span>
              <span class="grupo-tag grupo-tag-short" :class="'grupo-' + (a.grupo || 'MP').toLowerCase()">{{ grupoCorto(a.grupo) }}</span>
            </td>
            <td class="td">
              <div class="conteo-cell">
                <div class="teorico-block">
                  <span class="teorico-label">Teo</span>
                  <span class="teorico-value">{{ fmtNum(a.inventario_teorico) }}</span>
                </div>
                <div class="stepper" :class="{ 'stepper-bloqueado': conteoBloqueado }">
                  <button class="stepper-btn stepper-down" :disabled="conteoBloqueado" @click="ajustarConteo(a, -1)" tabindex="-1">
                    <span class="material-icons" style="font-size:12px">remove</span>
                  </button>
                  <input class="count-input" :class="claseInput(a)" :readonly="conteoBloqueado" type="text" inputmode="decimal" placeholder="—" :value="displayConteo(a)" @blur="onConteoConValidacion(a, $event)" @input="onInputDebounce(a, $event)" @keyup.enter="$event.target.blur()">
                  <button class="stepper-btn stepper-up" :disabled="conteoBloqueado" @click="ajustarConteo(a, 1)" tabindex="-1">
                    <span class="material-icons" style="font-size:12px">add</span>
                  </button>
                </div>
                <div class="diff-col">
                  <span class="diff-badge" :class="claseBadge(a)">{{ textoBadge(a) }}</span>
                  <span v-if="a.contado_por" class="contador-chip">{{ a.contado_por.substring(0, 3).toUpperCase() }}</span>
                </div>
                <div class="action-menu-wrap">
                  <button class="action-btn" :class="{ 'has-note': a.notas || a.foto }" @click.stop="toggleMenu(a.id)">
                    <span class="material-icons" style="font-size:16px">more_vert</span>
                  </button>
                  <div v-if="menuAbierto === a.id" class="action-menu" @click.stop>
                    <div class="action-menu-item" @click="abrirNotas(a); menuAbierto = null">
                      <span class="material-icons" style="font-size:14px">edit_note</span>
                      <span>{{ a.notas ? 'Editar nota' : 'Agregar nota' }}</span>
                    </div>
                    <div class="action-menu-item" @click="tomarFoto(a); menuAbierto = null">
                      <span class="material-icons" style="font-size:14px">photo_camera</span>
                      <span>Tomar foto</span>
                    </div>
                    <div v-if="a.foto" class="action-menu-item" @click="verFoto(a); menuAbierto = null">
                      <span class="material-icons" style="font-size:14px">image</span>
                      <span>Ver foto</span>
                    </div>
                    <div v-if="a.id_effi?.startsWith('NM-') && puede('asignar_articulo')" class="action-menu-item" @click="abrirAsignar(a); menuAbierto = null">
                      <span class="material-icons" style="font-size:14px">link</span>
                      <span>Asignar artículo</span>
                    </div>
                  </div>
                </div>
              </div>
            </td>
          </tr>
          <tr v-if="!articulos.length && !cargando">
            <td colspan="5" class="td td-empty">
              <span class="material-icons" style="font-size:24px;opacity:0.3">inbox</span>
              <span>{{ busqueda ? 'Sin resultados para "' + busqueda + '"' : 'No hay artículos' }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

      </template><!-- /VISTA CONTEO -->

      <!-- ═══ VISTA GESTIÓN ═══ -->
      <template v-if="vistaActiva === 'gestion'">
      <!-- Sub-pestañas de Gestión -->
      <div class="ges-subtabs">
        <button class="ges-subtab" :class="{ active: gesSubtab === 'dashboard' }" @click="gesSubtab = 'dashboard'">
          <span class="material-icons" style="font-size:14px">dashboard</span> Dashboard
        </button>
        <button class="ges-subtab" :class="{ active: gesSubtab === 'auditoria' }" @click="gesSubtab = 'auditoria'; cargarOpsRevisar()">
          <span class="material-icons" style="font-size:14px">fact_check</span> Auditoría OPs
          <span v-if="opsResumen.sospechosas > 0" class="ges-subtab-badge">{{ opsResumen.sospechosas }}</span>
        </button>
      </div>

      <div class="ges-scroll-container" v-if="gesSubtab === 'dashboard'">

        <!-- DASHBOARD KPIs -->
        <div class="ges-dashboard" v-if="gesDash">
          <div class="ges-kpis">
            <div class="ges-kpi">
              <div class="ges-kpi-label">Valor Teórico</div>
              <div class="ges-kpi-value">${{ fmtMoney(gesDash.valor_teorico) }}</div>
            </div>
            <div class="ges-kpi">
              <div class="ges-kpi-label">Valor Físico</div>
              <div class="ges-kpi-value">${{ fmtMoney(gesDash.valor_fisico) }}</div>
            </div>
            <div class="ges-kpi ges-kpi-impacto" :class="gesDash.impacto_total < 0 ? 'neg' : 'pos'">
              <div class="ges-kpi-label">Impacto</div>
              <div class="ges-kpi-value">${{ fmtMoney(gesDash.impacto_total) }}</div>
            </div>
            <div class="ges-kpi">
              <div class="ges-kpi-label">Con diferencia</div>
              <div class="ges-kpi-value">{{ gesDash.con_diferencia }} <small>/ {{ gesDash.total_articulos }}</small></div>
            </div>
          </div>

          <!-- Severidad mini cards -->
          <div class="ges-severidad-row">
            <div class="ges-sev-card ges-sev-critica" @click="gesFiltroSev = gesFiltroSev === 'critica' ? null : 'critica'; cargarGesArticulos()">
              <span class="ges-sev-count">{{ gesDash.por_severidad?.critica?.count || 0 }}</span>
              <span class="ges-sev-label">Críticas</span>
            </div>
            <div class="ges-sev-card ges-sev-significativa" @click="gesFiltroSev = gesFiltroSev === 'significativa' ? null : 'significativa'; cargarGesArticulos()">
              <span class="ges-sev-count">{{ gesDash.por_severidad?.significativa?.count || 0 }}</span>
              <span class="ges-sev-label">Significativas</span>
            </div>
            <div class="ges-sev-card ges-sev-menor" @click="gesFiltroSev = gesFiltroSev === 'menor' ? null : 'menor'; cargarGesArticulos()">
              <span class="ges-sev-count">{{ gesDash.por_severidad?.menor?.count || 0 }}</span>
              <span class="ges-sev-label">Menores</span>
            </div>
          </div>

        </div><!-- /dashboard -->

        <!-- FILTROS GESTIÓN -->
        <div class="inv-filters-row">
          <span class="inv-bodegas-label">Severidad</span>
          <button class="inv-pill" :class="{ active: !gesFiltroSev }" @click="gesFiltroSev = null; cargarGesArticulos()">Todas</button>
          <button class="inv-pill ges-pill-critica" :class="{ active: gesFiltroSev === 'critica' }" @click="gesFiltroSev = gesFiltroSev === 'critica' ? null : 'critica'; cargarGesArticulos()">Críticas</button>
          <button class="inv-pill ges-pill-significativa" :class="{ active: gesFiltroSev === 'significativa' }" @click="gesFiltroSev = gesFiltroSev === 'significativa' ? null : 'significativa'; cargarGesArticulos()">Significativas</button>
          <button class="inv-pill ges-pill-menor" :class="{ active: gesFiltroSev === 'menor' }" @click="gesFiltroSev = gesFiltroSev === 'menor' ? null : 'menor'; cargarGesArticulos()">Menores</button>

          <span class="inv-separator"></span>

          <span class="inv-bodegas-label">Estado</span>
          <button class="inv-pill" :class="{ active: !gesFiltroEstado }" @click="gesFiltroEstado = null; cargarGesArticulos()">Todos</button>
          <button class="inv-pill" :class="{ active: gesFiltroEstado === 'pendiente' }" @click="gesFiltroEstado = gesFiltroEstado === 'pendiente' ? null : 'pendiente'; cargarGesArticulos()">Pendientes</button>
          <button class="inv-pill" :class="{ active: gesFiltroEstado === 'analizado' }" @click="gesFiltroEstado = gesFiltroEstado === 'analizado' ? null : 'analizado'; cargarGesArticulos()">Analizados</button>
          <button class="inv-pill" :class="{ active: gesFiltroEstado === 'justificada' }" @click="gesFiltroEstado = gesFiltroEstado === 'justificada' ? null : 'justificada'; cargarGesArticulos()">Justificadas</button>
          <button class="inv-pill" :class="{ active: gesFiltroEstado === 'requiere_ajuste' }" @click="gesFiltroEstado = gesFiltroEstado === 'requiere_ajuste' ? null : 'requiere_ajuste'; cargarGesArticulos()">Req. ajuste</button>
        </div>

        <!-- BARRA ACCIONES GESTIÓN -->
        <div class="ges-actions-bar">
          <button class="ges-action-btn" :disabled="gesAnalizando || gestionBloqueada" @click="lanzarAnalisis">
            <span class="material-icons" :class="{ spin: gesAnalizando }" style="font-size:15px">psychology</span>
            {{ gesAnalizando ? `Analizando ${gesProgreso}/${gesTotal}...` : 'Analizar inconsistencias' }}
          </button>
          <span class="ges-accion-info">{{ gesTotalFiltrados }} artículos</span>
          <button class="ges-action-btn-sec" @click="expandirTodos">Expandir todos</button>
          <button class="ges-action-btn-sec" @click="colapsarTodos">Colapsar todos</button>
        </div>

        <!-- ACORDEONES POR GRUPO -->
        <div class="ges-acordeones" v-if="gesDash?.por_grupo">
          <div v-for="g in gesDash.por_grupo.filter(x => x.total > 0)" :key="g.grupo" class="ges-grupo-acordeon">
            <!-- Encabezado grupo (siempre visible) -->
            <div class="ges-grupo-header" @click="toggleGrupoExpandido(g.grupo)">
              <span class="material-icons ges-chevron" :class="{ expandido: gesGruposExpandidos[g.grupo] }">chevron_right</span>
              <span class="grupo-tag" :class="'grupo-' + (g.grupo || 'mp').toLowerCase()">{{ g.grupo }}</span>
              <span class="ges-grupo-nombre">{{ grupoNombre(g.grupo) }}</span>
              <span class="ges-grupo-count">{{ articulosPorGrupo(g.grupo).length }} / {{ g.total }}</span>
              <div class="ges-grupo-metricas">
                <div class="ges-metrica">
                  <span class="ges-metrica-label">Teórico</span>
                  <span class="ges-metrica-value">${{ fmtMoney(g.valor_teorico) }}</span>
                </div>
                <div class="ges-metrica">
                  <span class="ges-metrica-label">Físico</span>
                  <span class="ges-metrica-value">${{ fmtMoney(g.valor_fisico) }}</span>
                </div>
                <div class="ges-metrica">
                  <span class="ges-metrica-label">Impacto</span>
                  <span class="ges-metrica-value" :class="g.impacto < 0 ? 'text-red' : g.impacto > 0 ? 'text-green' : ''">${{ fmtMoney(g.impacto) }}</span>
                </div>
                <div class="ges-metrica">
                  <span class="ges-metrica-label">Exact.</span>
                  <span class="ges-metrica-value">{{ g.pct_exactitud }}%</span>
                </div>
              </div>
            </div>

            <!-- Contenido expandido: tabla de artículos del grupo -->
            <div v-if="gesGruposExpandidos[g.grupo]" class="ges-grupo-body">
              <table class="inv-table ges-table-grupo">
                <thead>
                  <tr>
                    <th class="th" style="width:30px">Sev</th>
                    <th class="th" style="width:50px">ID</th>
                    <th class="th">Artículo</th>
                    <th class="th text-right" style="width:70px">Teórico</th>
                    <th class="th text-right" style="width:70px">Físico</th>
                    <th class="th text-right" style="width:60px">Dif</th>
                    <th class="th text-right" style="width:100px">Impacto $</th>
                    <th class="th" style="width:200px">Causa IA</th>
                    <th class="th" style="width:100px">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="a in articulosPorGrupo(g.grupo)" :key="a.id" class="ges-row" @click="abrirDetalleGestion(a)">
                    <td class="td td-center"><span class="ges-sev-dot" :class="'sev-' + a.severidad" :title="a.severidad"></span></td>
                    <td class="td">{{ a.id_effi }}</td>
                    <td class="td">
                      <span>{{ a.nombre }}</span>
                      <span v-if="a.unidad" class="unit-tag">{{ a.unidad }}</span>
                    </td>
                    <td class="td text-right">{{ a.total_teorico }}</td>
                    <td class="td text-right">{{ a.total_fisico }}</td>
                    <td class="td text-right" :class="a.total_diferencia < 0 ? 'text-red' : a.total_diferencia > 0 ? 'text-green' : ''">{{ a.total_diferencia }}</td>
                    <td class="td text-right" :class="a.impacto_economico < 0 ? 'text-red' : 'text-green'">${{ fmtMoney(a.impacto_economico) }}</td>
                    <td class="td">
                      <div v-if="a.causa_ia" class="ges-causa">
                        <span class="ges-causa-text">{{ a.causa_ia }}</span>
                        <span class="ges-conf-badge" :class="a.confianza_ia >= 80 ? 'conf-alta' : a.confianza_ia >= 50 ? 'conf-media' : 'conf-baja'">{{ a.confianza_ia }}%</span>
                      </div>
                      <span v-else class="ges-sin-causa">—</span>
                    </td>
                    <td class="td">
                      <span class="ges-estado-chip" :class="'est-' + a.estado">{{ gesEstadoLabel(a.estado) }}</span>
                    </td>
                  </tr>
                  <tr v-if="articulosPorGrupo(g.grupo).length === 0">
                    <td colspan="9" class="td td-empty" style="padding:12px">
                      <span style="font-size:11px;opacity:0.5">Sin artículos con los filtros actuales</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

      </div><!-- /ges-scroll-container -->

      <!-- ═══ SUB-PESTAÑA: AUDITORÍA OPs ═══ -->
      <div class="ges-scroll-container" v-if="gesSubtab === 'auditoria'">
        <div class="ges-dashboard">
          <!-- Header con resumen -->
          <div class="ops-header">
            <div class="ops-resumen-cards">
              <div class="ops-card">
                <div class="ops-card-num">{{ opsResumen.total || 0 }}</div>
                <div class="ops-card-label">Total OPs</div>
              </div>
              <div class="ops-card ops-card-incluidas">
                <div class="ops-card-num">{{ opsResumen.incluidas || 0 }}</div>
                <div class="ops-card-label">Incluidas (Generadas)</div>
              </div>
              <div class="ops-card ops-card-excluidas">
                <div class="ops-card-num">{{ opsResumen.excluidas || 0 }}</div>
                <div class="ops-card-label">Excluidas (Procesadas)</div>
              </div>
              <div class="ops-card ops-card-sospechosas">
                <div class="ops-card-num">{{ opsResumen.sospechosas || 0 }}</div>
                <div class="ops-card-label">Sospechosas (±6h)</div>
              </div>
              <div class="ops-card ops-card-revisadas">
                <div class="ops-card-num">{{ opsResumen.revisadas || 0 }}</div>
                <div class="ops-card-label">Revisadas</div>
              </div>
            </div>
          </div>

          <!-- Filtros -->
          <div class="inv-filters-row" style="padding:8px 0 12px 0">
            <span class="inv-bodegas-label">Inclusión</span>
            <button class="inv-pill" :class="{ active: !opsFiltroInc }" @click="opsFiltroInc = null; cargarOpsRevisar()">Todas</button>
            <button class="inv-pill" :class="{ active: opsFiltroInc === 'incluidas' }" @click="opsFiltroInc = opsFiltroInc === 'incluidas' ? null : 'incluidas'; cargarOpsRevisar()">Incluidas</button>
            <button class="inv-pill" :class="{ active: opsFiltroInc === 'excluidas' }" @click="opsFiltroInc = opsFiltroInc === 'excluidas' ? null : 'excluidas'; cargarOpsRevisar()">Excluidas</button>

            <span class="inv-separator"></span>

            <span class="inv-bodegas-label">Sospecha</span>
            <button class="inv-pill" :class="{ active: !opsFiltroSos }" @click="opsFiltroSos = null; cargarOpsRevisar()">Todas</button>
            <button class="inv-pill ges-pill-critica" :class="{ active: opsFiltroSos === 'sospechosas' }" @click="opsFiltroSos = opsFiltroSos === 'sospechosas' ? null : 'sospechosas'; cargarOpsRevisar()">Sospechosas</button>
            <button class="inv-pill" :class="{ active: opsFiltroSos === 'normales' }" @click="opsFiltroSos = opsFiltroSos === 'normales' ? null : 'normales'; cargarOpsRevisar()">Normales</button>

            <span class="inv-separator"></span>

            <span class="inv-bodegas-label">Revisión</span>
            <button class="inv-pill" :class="{ active: !opsFiltroRev }" @click="opsFiltroRev = null; cargarOpsRevisar()">Todas</button>
            <button class="inv-pill" :class="{ active: opsFiltroRev === 'pendientes' }" @click="opsFiltroRev = opsFiltroRev === 'pendientes' ? null : 'pendientes'; cargarOpsRevisar()">Pendientes</button>
            <button class="inv-pill" :class="{ active: opsFiltroRev === 'revisadas' }" @click="opsFiltroRev = opsFiltroRev === 'revisadas' ? null : 'revisadas'; cargarOpsRevisar()">Revisadas</button>
          </div>

          <!-- Tabla de OPs -->
          <div class="ops-table-wrap">
            <table class="inv-table ops-table">
              <thead>
                <tr>
                  <th class="th" style="width:30px"></th>
                  <th class="th" style="width:60px">ID</th>
                  <th class="th">Descripción</th>
                  <th class="th" style="width:90px">Estado corte</th>
                  <th class="th text-center" style="width:70px">Incluida</th>
                  <th class="th" style="width:130px">Evento</th>
                  <th class="th text-right" style="width:90px">Δ corte</th>
                  <th class="th text-center" style="width:70px">Mat/Prod</th>
                  <th class="th text-center" style="width:90px">Estado</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="op in opsRevisar" :key="op.id" class="ops-row" :class="{ 'ops-row-sospechosa': op.sospechosa, 'ops-row-revisada': op.revisada }" @click="abrirDetalleOp(op)">
                  <td class="td td-center">
                    <span v-if="op.sospechosa" class="ops-dot ops-dot-sospechosa" title="Sospechosa: cambio dentro de ±6h del corte"></span>
                    <span v-else class="ops-dot ops-dot-normal" title="Normal"></span>
                  </td>
                  <td class="td">{{ op.id_orden }}</td>
                  <td class="td">{{ op.descripcion }}</td>
                  <td class="td">
                    <span class="ops-estado-chip" :class="op.estado_al_corte === 'Generada' ? 'est-generada' : 'est-procesada'">{{ op.estado_al_corte }}</span>
                  </td>
                  <td class="td td-center">
                    <span v-if="op.incluida_en_calculo" class="material-icons" style="font-size:14px;color:#4ade80">check</span>
                    <span v-else class="material-icons" style="font-size:14px;color:#6b7280">close</span>
                  </td>
                  <td class="td" style="font-size:11px">
                    <div v-if="op.fecha_cambio_procesada">P: {{ formatFechaCorta2(op.fecha_cambio_procesada) }}</div>
                    <div v-else>C: {{ formatFechaCorta2(op.fecha_creacion) }}</div>
                  </td>
                  <td class="td text-right" :class="op.sospechosa ? 'text-red' : ''">{{ formatDelta(op.minutos_del_corte) }}</td>
                  <td class="td text-center">{{ op.materiales_count }} / {{ op.productos_count }}</td>
                  <td class="td td-center">
                    <span v-if="op.revisada" class="ops-rev-chip ops-rev-yes">Revisada</span>
                    <span v-else class="ops-rev-chip ops-rev-no">Pendiente</span>
                  </td>
                </tr>
                <tr v-if="!opsRevisar.length">
                  <td colspan="9" class="td td-empty">
                    <span class="material-icons" style="font-size:24px;opacity:0.3">inbox</span>
                    <span>No hay OPs con los filtros seleccionados</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      </template><!-- /VISTA GESTIÓN -->

      <!-- ═══ VISTA COSTOS ═══ -->
      <template v-if="vistaActiva === 'costos'">
        <div class="costos-container">
          <OsDataTable
            :rows="costosRows"
            :columns="costosColumns"
            :loading="costosLoading"
            title="Valorización de Inventario"
          />
        </div>
      </template><!-- /VISTA COSTOS -->

    </div><!-- /inv-content -->

    <!-- FAB -->
    <button v-if="puede('agregar_articulo') && !conteoBloqueado" class="inv-fab" @click="mostrarAgregar = true"><span class="material-icons">add</span></button>

    <!-- POPUP COLUMNA — idéntico a GestionTable -->
    <Teleport to="body">
      <div v-if="colPopup" class="col-popup-overlay" @click="colPopup = null">
        <div class="col-popup" :style="colPopupStyle" @click.stop>
          <div class="cp-section">
            <label class="cp-label">Filtrar</label>
            <div class="cp-filter-row">
              <select class="cp-select" :value="getFilterOp(colPopup)" @change="setFilterOp(colPopup, $event.target.value)">
                <option value="eq">Igual a</option>
                <option value="contains">Contiene</option>
                <option value="gt">Mayor que</option>
                <option value="lt">Menor que</option>
                <option value="gte">Mayor o igual</option>
                <option value="lte">Menor o igual</option>
                <option value="between">Entre</option>
              </select>
            </div>
            <div class="cp-filter-inputs">
              <input ref="colFilterInput" class="cp-input" :placeholder="getFilterOp(colPopup) === 'between' ? 'Desde' : 'Valor'" :value="getFilterVal(colPopup)" @input="setFilterVal(colPopup, $event.target.value)" @keyup.enter="colPopup = null" @keyup.escape="colPopup = null">
              <input v-if="getFilterOp(colPopup) === 'between'" class="cp-input" placeholder="Hasta" :value="getFilterVal2(colPopup)" @input="setFilterVal2(colPopup, $event.target.value)">
            </div>
          </div>
          <div class="cp-section">
            <label class="cp-label">Ordenar</label>
            <div class="cp-sort-btns">
              <button class="cp-sort-btn" :class="{ active: sortKey === colPopup && sortDir === 'asc' }" @click="setSort(colPopup, 'asc')">
                <span class="material-icons" style="font-size:12px">keyboard_arrow_up</span> Ascendente
              </button>
              <button class="cp-sort-btn" :class="{ active: sortKey === colPopup && sortDir === 'desc' }" @click="setSort(colPopup, 'desc')">
                <span class="material-icons" style="font-size:12px">keyboard_arrow_down</span> Descendente
              </button>
            </div>
          </div>
          <div v-if="hasFilter(colPopup) || sortKey === colPopup" class="cp-footer">
            <button class="cp-clear-btn" @click="clearColumn(colPopup)">Limpiar todo</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- MODAL AGREGAR -->
    <div v-if="mostrarAgregar" class="inv-overlay" @click.self="cerrarModalAgregar">
      <div class="inv-modal" :class="{ 'inv-modal-expanded': tabAgregar === 'manual' }">
        <div class="inv-modal-header">
          <span>Agregar artículo</span>
          <button class="action-btn" @click="cerrarModalAgregar"><span class="material-icons">close</span></button>
        </div>

        <!-- Tabs -->
        <div class="inv-modal-tabs">
          <button class="inv-modal-tab" :class="{ active: tabAgregar === 'buscar' }" @click="tabAgregar = 'buscar'">Buscar</button>
          <button class="inv-modal-tab" :class="{ active: tabAgregar === 'excluidos' }" @click="tabAgregar = 'excluidos'; cargarExcluidos()">Excluidos</button>
          <button class="inv-modal-tab" :class="{ active: tabAgregar === 'manual' }" @click="tabAgregar = 'manual'">No matriculado</button>
        </div>

        <div class="inv-modal-body">
          <!-- TAB BUSCAR -->
          <template v-if="tabAgregar === 'buscar'">
            <input v-model="busquedaAgregar" class="inv-modal-search" type="text" placeholder="Buscar artículo por nombre o código..." @input="buscarParaAgregar">
            <div class="inv-modal-results">
              <div v-for="r in resultadosAgregar" :key="r.id" class="inv-modal-result-item" @click="agregarArticulo(r)">
                <span class="inv-modal-result-name">{{ r.nombre }}</span>
                <span class="inv-modal-result-id">{{ r.id }}</span>
              </div>
              <div v-if="busquedaAgregar && !resultadosAgregar.length" class="inv-modal-empty">Sin resultados</div>
            </div>
          </template>

          <!-- TAB EXCLUIDOS -->
          <template v-if="tabAgregar === 'excluidos'">
            <input v-model="busquedaExcluidos" class="inv-modal-search" type="text" placeholder="Filtrar excluidos...">
            <div class="inv-modal-results">
              <div v-for="e in excluidosFiltrados" :key="e.id" class="inv-modal-result-item" @click="reactivarExcluido(e)">
                <div class="inv-modal-result-name">{{ e.nombre }}</div>
                <div class="inv-modal-result-sub">{{ e.razon_exclusion }}</div>
              </div>
              <div v-if="!excluidosFiltrados.length" class="inv-modal-empty">
                {{ busquedaExcluidos ? 'Sin resultados' : 'No hay artículos excluidos' }}
              </div>
            </div>
          </template>

          <!-- TAB NO MATRICULADO -->
          <template v-if="tabAgregar === 'manual'">
            <div class="inv-form-group">
              <label class="inv-form-label">Nombre del artículo *</label>
              <input v-model="manualNombre" class="inv-form-input" type="text" placeholder="Ej: Producto nuevo sin código">
            </div>
            <div class="inv-form-row">
              <div class="inv-form-group inv-form-half">
                <label class="inv-form-label">Cantidad *</label>
                <input v-model="manualCantidad" class="inv-form-input" type="text" inputmode="decimal" placeholder="0">
              </div>
              <div class="inv-form-group inv-form-half">
                <label class="inv-form-label">Unidad *</label>
                <select v-model="manualUnidad" class="inv-form-input">
                  <option value="UND">UND</option>
                  <option value="KG">KG</option>
                  <option value="GRS">GRS</option>
                  <option value="LT">LT</option>
                  <option value="ML">ML</option>
                </select>
              </div>
            </div>
            <div class="inv-form-group">
              <label class="inv-form-label">Costo unitario</label>
              <input v-model="manualCosto" class="inv-form-input" type="text" inputmode="decimal" placeholder="Opcional">
            </div>
            <div class="inv-form-group">
              <label class="inv-form-label">Observaciones</label>
              <textarea v-model="manualNotas" class="inv-nota-textarea" rows="2" placeholder="Por qué no está matriculado, dónde se encontró..."></textarea>
            </div>
            <div class="inv-form-group">
              <label class="inv-form-label">Foto</label>
              <button class="inv-btn-outline" @click="$refs.manualFotoInput.click()">
                <span class="material-icons" style="font-size:14px">photo_camera</span>
                {{ manualFotoNombre || 'Tomar foto' }}
              </button>
              <input ref="manualFotoInput" type="file" accept="image/*" capture="environment" style="display:none" @change="onManualFoto">
            </div>
            <button class="inv-btn-primary" :disabled="!manualNombre || !manualCantidad || !manualUnidad" @click="agregarNoMatriculado">
              Agregar artículo
            </button>
          </template>
        </div>
      </div>
    </div>

    <!-- MODAL NOTAS -->
    <div v-if="mostrarNotas" class="inv-overlay" @click.self="cerrarNotas">
      <div class="inv-modal inv-modal-sm">
        <div class="inv-modal-header">
          <span>Nota — {{ articuloNota?.nombre }}</span>
          <button class="action-btn" @click="cerrarNotas"><span class="material-icons">close</span></button>
        </div>
        <div class="inv-modal-body">
          <textarea v-model="textoNota" class="inv-nota-textarea" rows="4" placeholder="Observaciones del conteo..."></textarea>
          <button class="inv-btn-primary" @click="guardarNota">Guardar nota</button>
        </div>
      </div>
    </div>

    <!-- MODAL VER FOTO -->
    <div v-if="mostrarFoto" class="inv-overlay" @click.self="mostrarFoto = false">
      <div class="inv-modal">
        <div class="inv-modal-header">
          <span>Foto — {{ articuloFoto?.nombre }}</span>
          <button class="action-btn" @click="mostrarFoto = false"><span class="material-icons">close</span></button>
        </div>
        <div class="inv-modal-body" style="padding:0">
          <img :src="API + '/api/inventario/fotos/' + articuloFoto?.foto" class="inv-foto-preview">
        </div>
      </div>
    </div>

    <!-- MODAL DETALLE OP REVISAR -->
    <div v-if="opDetalleVisible && opDetalleData" class="inv-overlay" @click.self="opDetalleVisible = false">
      <div class="inv-modal ges-modal-detalle" style="width:680px;max-width:90vw">
        <div class="inv-modal-header" :class="{ 'inv-modal-header-warn': opDetalleData.op.sospechosa }">
          <span>OP {{ opDetalleData.op.id_orden }} — {{ opDetalleData.op.descripcion }}</span>
          <button class="action-btn" @click="opDetalleVisible = false"><span class="material-icons">close</span></button>
        </div>
        <div class="inv-modal-body ges-detalle-body">
          <!-- Resumen -->
          <div class="ges-detalle-info">
            <span class="ops-estado-chip" :class="opDetalleData.op.estado_al_corte === 'Generada' ? 'est-generada' : 'est-procesada'">{{ opDetalleData.op.estado_al_corte }} al corte</span>
            <span v-if="opDetalleData.op.incluida_en_calculo" style="font-size:11px;color:#4ade80">✓ Incluida en cálculo</span>
            <span v-else style="font-size:11px;color:#9ca3af">✗ No incluida</span>
            <span v-if="opDetalleData.op.sospechosa" class="cierre-badge cierre-badge-conteo" style="margin-left:auto">⚠ Sospechosa</span>
          </div>

          <!-- Fechas -->
          <div class="ges-detalle-section">
            <div class="ges-detalle-label">Fechas</div>
            <div class="ops-fechas">
              <div><strong>Creada:</strong> {{ opDetalleData.op.fecha_creacion || '—' }}</div>
              <div><strong>Procesada:</strong> {{ opDetalleData.op.fecha_cambio_procesada || '—' }} <span style="font-size:10px;color:var(--text-tertiary)">(en COT, ya con offset aplicado)</span></div>
              <div v-if="opDetalleData.op.fecha_anulacion"><strong>Anulada:</strong> {{ opDetalleData.op.fecha_anulacion }}</div>
              <div><strong>Δ del corte:</strong> {{ formatDelta(opDetalleData.op.minutos_del_corte) }}</div>
            </div>
          </div>

          <!-- Cambios de estado -->
          <div class="ges-detalle-section" v-if="opDetalleData.cambios_estado.length">
            <div class="ges-detalle-label">Cambios de estado ({{ opDetalleData.cambios_estado.length }}) <span style="font-size:10px;color:var(--text-tertiary)">— UTC</span></div>
            <table class="ges-table-mini">
              <tbody>
                <tr v-for="(c, i) in opDetalleData.cambios_estado" :key="i">
                  <td>{{ c.f_cambio_de_estado }}</td>
                  <td><strong>{{ c.nuevo_estado }}</strong></td>
                  <td style="font-size:10px;color:var(--text-tertiary)">{{ c.responsable_cambio_de_estado }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Materiales -->
          <div class="ges-detalle-section" v-if="opDetalleData.materiales.length">
            <div class="ges-detalle-label">Materiales ({{ opDetalleData.materiales.length }})</div>
            <table class="ges-table-mini">
              <thead><tr><th>Cód</th><th>Material</th><th class="text-right">Cant</th></tr></thead>
              <tbody>
                <tr v-for="(m, i) in opDetalleData.materiales" :key="i">
                  <td>{{ m.cod_material }}</td>
                  <td>{{ m.descripcion_material }}</td>
                  <td class="text-right">{{ m.cantidad }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Productos -->
          <div class="ges-detalle-section" v-if="opDetalleData.productos.length">
            <div class="ges-detalle-label">Productos ({{ opDetalleData.productos.length }})</div>
            <table class="ges-table-mini">
              <thead><tr><th>Cód</th><th>Producto</th><th class="text-right">Cant</th></tr></thead>
              <tbody>
                <tr v-for="(p, i) in opDetalleData.productos" :key="i">
                  <td>{{ p.cod_articulo }}</td>
                  <td>{{ p.descripcion_articulo_producido }}</td>
                  <td class="text-right">{{ p.cantidad }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Revisión -->
          <div class="ges-detalle-section">
            <div class="ges-detalle-label">Revisión</div>
            <textarea v-model="opNotaRevision" class="ges-textarea" rows="2" placeholder="Nota de revisión (opcional)..."></textarea>
            <div style="display:flex;gap:8px;margin-top:8px">
              <button v-if="!opDetalleData.op.revisada" class="inv-btn-primary" :disabled="opGuardando" @click="marcarOpRevisada(true)">{{ opGuardando ? 'Guardando...' : 'Marcar como revisada' }}</button>
              <button v-else class="inv-btn-secondary" :disabled="opGuardando" @click="marcarOpRevisada(false)">Desmarcar revisada</button>
            </div>
            <div v-if="opDetalleData.op.revisada" style="margin-top:6px;font-size:10px;color:var(--text-tertiary)">
              Revisada por {{ opDetalleData.op.revisada_por }} el {{ opDetalleData.op.fecha_revision }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL DETALLE GESTIÓN -->
    <div v-if="gesDetalleVisible && gesDetalleData" class="inv-overlay" @click.self="gesDetalleVisible = false">
      <div class="inv-modal ges-modal-detalle">
        <div class="inv-modal-header">
          <span>{{ gesDetalleData.gestion.nombre }}</span>
          <button class="action-btn" @click="gesDetalleVisible = false"><span class="material-icons">close</span></button>
        </div>
        <div class="inv-modal-body ges-detalle-body">
          <!-- Info del artículo -->
          <div class="ges-detalle-info">
            <span class="grupo-tag" :class="'grupo-' + (gesDetalleData.gestion.grupo || 'mp').toLowerCase()">{{ gesDetalleData.gestion.grupo }}</span>
            <span class="unidad-tag">{{ gesDetalleData.gestion.unidad }}</span>
            <span class="ges-detalle-costo">Costo: ${{ Number(gesDetalleData.gestion.costo_manual).toLocaleString() }}</span>
            <span class="ges-sev-dot" :class="'sev-' + gesDetalleData.gestion.severidad" style="margin-left:auto"></span>
            <span style="font-size:11px;color:var(--text-tertiary)">{{ gesDetalleData.gestion.severidad }}</span>
          </div>

          <!-- Conteos por bodega -->
          <div class="ges-detalle-section">
            <div class="ges-detalle-label">Conteos por bodega</div>
            <table class="ges-table-mini">
              <thead><tr><th>Bodega</th><th class="text-right">Teórico</th><th class="text-right">Físico</th><th class="text-right">Diferencia</th><th>Contado por</th></tr></thead>
              <tbody>
                <tr v-for="c in gesDetalleData.conteos" :key="c.bodega">
                  <td>{{ c.bodega }}</td>
                  <td class="text-right">{{ c.inventario_teorico }}</td>
                  <td class="text-right">{{ c.inventario_fisico }}</td>
                  <td class="text-right" :class="(c.diferencia || 0) < 0 ? 'text-red' : (c.diferencia || 0) > 0 ? 'text-green' : ''">{{ c.diferencia }}</td>
                  <td style="font-size:11px;color:var(--text-tertiary)">{{ c.contado_por }}</td>
                </tr>
              </tbody>
            </table>
            <div class="ges-detalle-totales">
              Impacto: <strong :class="gesDetalleData.gestion.impacto_economico < 0 ? 'text-red' : 'text-green'">${{ Number(gesDetalleData.gestion.impacto_economico).toLocaleString() }}</strong>
            </div>
          </div>

          <!-- Análisis IA -->
          <div v-if="gesDetalleData.gestion.causa_ia" class="ges-detalle-section ges-detalle-ia">
            <div class="ges-detalle-label">
              <span class="material-icons" style="font-size:14px;vertical-align:middle">psychology</span> Análisis automático
            </div>
            <div class="ges-ia-causa">
              <span>{{ gesDetalleData.gestion.causa_ia }}</span>
              <span class="ges-conf-badge" :class="gesDetalleData.gestion.confianza_ia >= 80 ? 'conf-alta' : gesDetalleData.gestion.confianza_ia >= 50 ? 'conf-media' : 'conf-baja'">
                {{ gesDetalleData.gestion.confianza_ia }}%
              </span>
            </div>
            <div class="ges-ia-explicacion">{{ gesDetalleData.gestion.explicacion_ia }}</div>
            <div v-if="gesDetalleData.gestion.evidencia_ia" class="ges-ia-evidencias">
              <div v-for="(ev, i) in parseEvidencia(gesDetalleData.gestion.evidencia_ia)" :key="i" class="ges-ia-ev-item">
                <span class="material-icons" style="font-size:12px">arrow_right</span>
                <span>{{ ev.detalle }}</span>
              </div>
            </div>
          </div>
          <div v-else class="ges-detalle-section ges-sin-analisis">
            <span class="material-icons" style="font-size:16px;opacity:0.3">psychology</span>
            Sin análisis. Presiona "Analizar inconsistencias" en la barra de acciones.
          </div>

          <!-- Resolución -->
          <div class="ges-detalle-section">
            <div class="ges-detalle-label">Resolución</div>
            <div class="ges-resolucion-form">
              <div class="ges-form-row">
                <label>Estado</label>
                <select v-model="gesFormEstado" class="ges-select">
                  <option value="pendiente">Pendiente</option>
                  <option value="analizado">Analizado</option>
                  <option value="justificada">Justificada</option>
                  <option value="requiere_ajuste">Requiere ajuste</option>
                  <option value="ajustada">Ajustada</option>
                </select>
              </div>
              <div class="ges-form-row">
                <label>Causa</label>
                <select v-model="gesFormCausa" class="ges-select">
                  <option value="">— Seleccionar —</option>
                  <option v-for="c in gesDetalleData.causas_disponibles" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>
              <div class="ges-form-row">
                <label>Observaciones</label>
                <textarea v-model="gesFormObs" class="ges-textarea" rows="3" placeholder="Notas de la revisión..."></textarea>
              </div>
              <button class="inv-btn-primary" @click="guardarResolucion" :disabled="gesGuardando || gestionBloqueada" style="margin-top:8px">
                {{ gesGuardando ? 'Guardando...' : (gestionBloqueada ? 'Inventario cerrado' : 'Guardar') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL ASIGNAR ARTÍCULO -->
    <div v-if="mostrarAsignar" class="inv-overlay" @click.self="cerrarAsignar">
      <div class="inv-modal">
        <div class="inv-modal-header">
          <span>Asignar artículo de Effi</span>
          <button class="action-btn" @click="cerrarAsignar"><span class="material-icons">close</span></button>
        </div>
        <div class="inv-modal-body">
          <!-- Artículo NM actual -->
          <div class="asignar-origen">
            <div class="asignar-label">Artículo no matriculado</div>
            <div class="asignar-nombre">{{ articuloAsignar?.nombre }}</div>
            <span class="asignar-unidad-tag">{{ articuloAsignar?.unidad || 'UND' }}</span>
          </div>

          <div class="asignar-flecha">
            <span class="material-icons" style="font-size:20px;color:var(--text-tertiary)">arrow_downward</span>
          </div>

          <!-- Búsqueda -->
          <input v-model="busquedaAsignar" class="inv-modal-search" type="text" placeholder="Buscar artículo en Effi por nombre o código..." @input="buscarParaAsignar">

          <!-- Resultados -->
          <div v-if="!effiSeleccionado" class="inv-modal-results">
            <div v-for="r in resultadosAsignar" :key="r.id" class="inv-modal-result-item" @click="seleccionarEffi(r)">
              <div>
                <span class="inv-modal-result-name">{{ r.nombre }}</span>
                <span class="asignar-unidad-tag asignar-unidad-sm" style="margin-left:6px">{{ r.unidad }}</span>
              </div>
              <span class="inv-modal-result-id">{{ r.id }}</span>
            </div>
            <div v-if="busquedaAsignar && !resultadosAsignar.length" class="inv-modal-empty">Sin resultados</div>
          </div>

          <!-- Artículo seleccionado -->
          <div v-if="effiSeleccionado" class="asignar-destino">
            <div class="asignar-label">Artículo Effi seleccionado</div>
            <div class="asignar-nombre">{{ effiSeleccionado.nombre }}</div>
            <div class="asignar-meta">ID: {{ effiSeleccionado.id }} · Cat: {{ effiSeleccionado.categoria || '—' }}</div>

            <!-- Comparación de unidades -->
            <div class="asignar-comparacion" :class="unidadesCoinciden ? 'asignar-match' : 'asignar-mismatch'">
              <span class="material-icons" style="font-size:16px">{{ unidadesCoinciden ? 'check_circle' : 'warning' }}</span>
              <span>{{ articuloAsignar?.unidad || 'UND' }}</span>
              <span class="material-icons" style="font-size:14px">arrow_forward</span>
              <span>{{ effiSeleccionado.unidad }}</span>
              <span class="asignar-comparacion-msg">{{ unidadesCoinciden ? 'Unidades coinciden' : '¡Unidades diferentes!' }}</span>
            </div>

            <div class="asignar-btns">
              <button class="inv-btn-secondary" @click="effiSeleccionado = null; busquedaAsignar = ''">Cambiar</button>
              <button class="inv-btn-primary" @click="confirmarAsignacion">Confirmar asignación</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ALERTA DE RANGO -->
    <div v-if="alertaRango" class="inv-overlay" @click.self="alertaRango = null">
      <div class="inv-modal inv-modal-sm">
        <div class="inv-modal-header inv-modal-header-warn">
          <span class="material-icons" style="font-size:18px;color:var(--color-warning)">warning</span>
          <span>Valor inusual</span>
          <button class="action-btn" @click="alertaRango = null"><span class="material-icons">close</span></button>
        </div>
        <div class="inv-modal-body">
          <p class="alerta-articulo">{{ alertaRango.articulo.nombre }}</p>
          <p class="alerta-mensaje">{{ alertaRango.mensaje }}</p>
          <div class="alerta-btns">
            <button v-if="alertaRango.sugerencia != null" class="inv-btn-primary" @click="corregirAlerta">
              Corregir a {{ alertaRango.sugerencia }}
            </button>
            <button class="alerta-btn-confirmar" @click="confirmarAlerta">
              Confirmar {{ alertaRango.valor }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- INPUT OCULTO PARA CÁMARA -->
    <input ref="fotoInput" type="file" accept="image/*" capture="environment" style="display:none" @change="onFotoCapturada">

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import OsDataTable from './components/OsDataTable.vue'

const API = window.location.origin
const AUTH_API = 'https://gestion.oscomunidad.com'
const GOOGLE_CLIENT_ID = '290093919454-j2l1el0p624v65cada556pdc3r2gm6k7.apps.googleusercontent.com'
const KEY_JWT = 'inv_jwt'
const KEY_USUARIO = 'inv_usuario'
const FECHA = ref('2026-03-30')

// Auth
const autenticado = ref(false)
const loginError = ref('')
const loginCargando = ref(false)

const usuario = ref('Santiago')
const iniciales = ref('SS')
const bodegas = ref([])
const bodegaActiva = ref('Principal')
const articulos = ref([])
const resumen = ref({})
const busqueda = ref('')
const filtroActivo = ref(null)
const cargando = ref(false)
const mostrarAgregar = ref(false)
const tabAgregar = ref('buscar')
const busquedaAgregar = ref('')
const resultadosAgregar = ref([])
const busquedaExcluidos = ref('')
const excluidos = ref([])
const manualNombre = ref('')
const manualCantidad = ref('')
const manualUnidad = ref('UND')
const manualCosto = ref('')
const manualNotas = ref('')
const manualFoto = ref(null)
const manualFotoNombre = ref('')
const manualFotoInput = ref(null)
const mostrarNotas = ref(false)
const articuloNota = ref(null)
const textoNota = ref('')
const panelAbierto = ref(false)
const menuAbierto = ref(null)
const nivelUsuario = ref(1)
const politicas = ref({ acciones: {} })
const mostrarNuevoInv = ref(false)
const nuevaFechaInv = ref('')
const creandoInv = ref(false)
const mostrarConfirmReiniciar = ref(false)
const textoConfirmReiniciar = ref('')
const mostrarConfirmEliminar = ref(false)
const estadoTeorico = ref(null)
// Asignar artículo NM
const mostrarAsignar = ref(false)
const articuloAsignar = ref(null)
const busquedaAsignar = ref('')
const resultadosAsignar = ref([])
const effiSeleccionado = ref(null)
// Vista activa
const vistaActiva = ref('conteo')
// Costos
const costosRows = ref([])
const costosLoading = ref(false)
const costosColumns = ref([
  { key: 'id_effi', label: 'Cód', visible: true, nowrap: true },
  { key: 'nombre', label: 'Artículo', visible: true },
  { key: 'categoria', label: 'Categoría', visible: true,
    options: [] },
  { key: 'grupo', label: 'Tipo', visible: true,
    options: [
      { value: 'MP', label: 'Materia Prima' },
      { value: 'INS', label: 'Insumos' },
      { value: 'PP', label: 'Producto en Proceso' },
      { value: 'PT', label: 'Producto Terminado' },
      { value: 'DS', label: 'Desechable' },
      { value: 'DES', label: 'Desperdicio' },
      { value: 'NM', label: 'No Matriculado' },
    ] },
  { key: 'bodega', label: 'Bodega', visible: false,
    options: [] },
  { key: 'costo_manual', label: 'Costo Unit.', visible: true, nowrap: true },
  { key: 'teorico', label: 'Cant. Teórica', visible: true, nowrap: true },
  { key: 'fisico', label: 'Cant. Física', visible: true, nowrap: true },
  { key: 'diferencia', label: 'Diferencia', visible: true, nowrap: true },
  { key: 'valor_teorico', label: 'Val. Teórico', visible: true, nowrap: true },
  { key: 'valor_fisico', label: 'Val. Físico', visible: true, nowrap: true },
  { key: 'impacto', label: 'Impacto $', visible: true, nowrap: true },
])
// Sub-pestaña de Gestión
const gesSubtab = ref('dashboard')
// Auditoría OPs
const opsRevisar = ref([])
const opsResumen = ref({})
const opsFiltroInc = ref(null)
const opsFiltroSos = ref(null)
const opsFiltroRev = ref(null)
const opDetalleVisible = ref(false)
const opDetalleData = ref(null)
const opNotaRevision = ref('')
const opGuardando = ref(false)
// Estado de cierres
const estadoCierre = ref({ conteo_cerrado: false, inventario_cerrado: false })
const conteoBloqueado = computed(() => estadoCierre.value.conteo_cerrado || estadoCierre.value.inventario_cerrado)
const gestionBloqueada = computed(() => estadoCierre.value.inventario_cerrado)
const mostrarConfirmCerrarConteo = ref(false)
const mostrarConfirmCerrarInventario = ref(false)
const mostrarConfirmReabrirConteo = ref(false)
// Gestión
const gesDash = ref(null)
const gesArticulos = ref([])
const gesFiltroSev = ref(null)
const gesFiltroEstado = ref(null)
const gesFiltroGrupo = ref(null)
const gesAnalizando = ref(false)
const gesProgreso = ref(0)
const gesTotal = ref(0)
const gesDetalleVisible = ref(false)
const gesDetalleData = ref(null)
const gesGruposExpandidos = ref({})
const gesFormEstado = ref('')
const gesFormCausa = ref('')
const gesFormObs = ref('')
const gesGuardando = ref(false)
// Sync Effi
const syncEstado = ref('idle')
const syncMensaje = ref('')
const calculandoTeorico = ref(false)
const mostrarFoto = ref(false)
const articuloFoto = ref(null)
const fotoInput = ref(null)
const articuloParaFoto = ref(null)
const alertaRango = ref(null) // { articulo, valor, sugerencia, mensaje }
const fechasInventario = ref([])
const mostrarListaBodegas = ref(false)

// Columns definition
const columns = [
  { key: 'id_effi', label: 'ID' },
  { key: 'nombre', label: 'Artículo' },
  { key: 'grupo', label: 'Categ' },
]

// ── Reloj (DOM directo, sin reactivity para no re-renderizar la tabla) ──
let clockInterval
function actualizarReloj() {
  const el = document.getElementById('inv-clock')
  if (!el) return
  const now = new Date()
  const dias = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb']
  const meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
  const h = String(now.getHours()).padStart(2,'0')
  const m = String(now.getMinutes()).padStart(2,'0')
  const s = String(now.getSeconds()).padStart(2,'0')
  el.textContent = `${dias[now.getDay()]} ${now.getDate()} ${meses[now.getMonth()]} ${now.getFullYear()} · ${h}:${m}:${s}`
}

const fechaDisplay = computed(() => {
  const d = new Date(FECHA.value + 'T12:00:00')
  const meses = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
  return `${meses[d.getMonth()]} ${d.getDate()} ${d.getFullYear()}`
})

function formatFechaCorta(f) {
  const d = new Date(f + 'T12:00:00')
  const meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
  return `${d.getDate()} ${meses[d.getMonth()]} ${d.getFullYear()}`
}
function formatFechaHora(ts) {
  if (!ts) return ''
  const d = new Date(ts.replace(' ', 'T'))
  const h = d.getHours(), m = String(d.getMinutes()).padStart(2, '0')
  const ampm = h >= 12 ? 'pm' : 'am'
  return `${d.getDate()}/${d.getMonth()+1} ${h % 12 || 12}:${m}${ampm}`
}

function cambiarFecha(f) {
  FECHA.value = f
  bodegaActiva.value = 'Principal'
  filtroActivo.value = null
  busqueda.value = ''
  columnFilters.value = {}
  sortKey.value = ''
  cargarBodegas(); cargarResumen(); cargarArticulos(); cargarEstadoTeorico(); cargarEstadoCierre()
  panelAbierto.value = false
}

// ── Bodegas ──
const bodegasConStock = computed(() => bodegas.value.filter(b => b.total > 0))
const bodegasSinStock = computed(() => bodegas.value.filter(b => b.total === 0))

// ── Filtros estado ──
const filtros = computed(() => [
  { key: null, label: 'Todos', count: resumen.value.total || 0 },
  { key: 'pendientes', label: 'Pendientes', count: resumen.value.pendientes || 0 },
  { key: 'contados', label: 'Contados', count: resumen.value.contados || 0 },
  { key: 'diferencias', label: 'Diferencias', count: resumen.value.con_diferencia || 0 },
])

const pctOk = computed(() => resumen.value.total ? ((resumen.value.ok || 0) / resumen.value.total) * 100 : 0)
const pctDiff = computed(() => resumen.value.total ? ((resumen.value.con_diferencia || 0) / resumen.value.total) * 100 : 0)

// ── Filtros por columna (patrón GestionTable) ──
const columnFilters = ref({})
function getFilterOp(key) { return columnFilters.value[key]?.op || 'eq' }
function getFilterVal(key) { return columnFilters.value[key]?.val || '' }
function getFilterVal2(key) { return columnFilters.value[key]?.val2 || '' }
function setFilterOp(key, op) { columnFilters.value = { ...columnFilters.value, [key]: { ...(columnFilters.value[key] || { op:'eq', val:'', val2:'' }), op } } }
function setFilterVal(key, val) { columnFilters.value = { ...columnFilters.value, [key]: { ...(columnFilters.value[key] || { op:'eq', val:'', val2:'' }), val } } }
function setFilterVal2(key, val2) { columnFilters.value = { ...columnFilters.value, [key]: { ...(columnFilters.value[key] || { op:'eq', val:'', val2:'' }), val2 } } }
function hasFilter(key) { return !!(columnFilters.value[key]?.val?.trim()) }

// ── Filtrado local ──
const filteredRows = computed(() => {
  const keys = Object.keys(columnFilters.value).filter(k => hasFilter(k))
  if (!keys.length) return articulos.value
  return articulos.value.filter(row => keys.every(key => {
    const f = columnFilters.value[key]
    const fv = f.val.trim()
    const raw = row[key]
    const n = v => parseFloat(String(v).replace(',', '.'))
    const val = String(raw ?? '').toLowerCase()
    switch (f.op) {
      case 'eq': return val === fv.toLowerCase()
      case 'contains': return val.includes(fv.toLowerCase())
      case 'gt': return !isNaN(n(raw)) && n(raw) > n(fv)
      case 'lt': return !isNaN(n(raw)) && n(raw) < n(fv)
      case 'gte': return !isNaN(n(raw)) && n(raw) >= n(fv)
      case 'lte': return !isNaN(n(raw)) && n(raw) <= n(fv)
      case 'between': { const fv2 = f.val2?.trim(); return !isNaN(n(raw)) && n(raw) >= n(fv) && (!fv2 || n(raw) <= n(fv2)) }
      default: return val.includes(fv.toLowerCase())
    }
  }))
})

// ── Ordenamiento ──
const sortKey = ref('')
const sortDir = ref('asc')
function setSort(key, dir) {
  if (sortKey.value === key && sortDir.value === dir) { sortKey.value = '' }
  else { sortKey.value = key; sortDir.value = dir }
}
const sortedRows = computed(() => {
  if (!sortKey.value) return filteredRows.value
  return [...filteredRows.value].sort((a, b) => {
    const av = a[sortKey.value], bv = b[sortKey.value]
    const n = v => parseFloat(String(v).replace(',', '.'))
    const r = isNaN(n(av)) ? String(av ?? '').localeCompare(String(bv ?? '')) : n(av) - n(bv)
    const primary = sortDir.value === 'asc' ? r : -r
    // Segundo nivel: siempre alfabético por nombre
    if (primary === 0) return String(a.nombre ?? '').localeCompare(String(b.nombre ?? ''))
    return primary
  })
})

// ── Popup columna ──
const colPopup = ref(null)
const colPopupStyle = ref({})
const colFilterInput = ref(null)

function openColPopup(key, event) {
  if (colPopup.value === key) { colPopup.value = null; return }
  const th = event.currentTarget
  const rect = th.getBoundingClientRect()
  colPopupStyle.value = {
    top: (rect.bottom + 4) + 'px',
    left: Math.max(4, Math.min(rect.left, window.innerWidth - 230)) + 'px',
  }
  colPopup.value = key
  nextTick(() => { if (colFilterInput.value) colFilterInput.value.focus() })
}

function clearColumn(key) {
  const cf = { ...columnFilters.value }; delete cf[key]; columnFilters.value = cf
  if (sortKey.value === key) sortKey.value = ''
  colPopup.value = null
}

// ── API ──
function authHeaders() {
  const t = localStorage.getItem(KEY_JWT)
  return t ? { 'Authorization': `Bearer ${t}` } : {}
}
async function fetchApi(path) { return (await fetch(API + path, { headers: authHeaders() })).json() }

async function cargarFechas() { fechasInventario.value = await fetchApi('/api/inventario/fechas') }
async function cargarBodegas() { bodegas.value = await fetchApi(`/api/inventario/bodegas/todas?fecha=${FECHA.value}`) }
async function cargarResumen() {
  let url = `/api/inventario/resumen?fecha=${FECHA.value}`
  if (bodegaActiva.value) url += `&bodega=${encodeURIComponent(bodegaActiva.value)}`
  resumen.value = await fetchApi(url)
}

async function cargarArticulos() {
  cargando.value = true
  let url = `/api/inventario/articulos?fecha=${FECHA.value}`
  if (bodegaActiva.value) url += `&bodega=${encodeURIComponent(bodegaActiva.value)}`
  if (filtroActivo.value) url += `&filtro=${filtroActivo.value}`
  if (busqueda.value) url += `&busqueda=${encodeURIComponent(busqueda.value)}`
  articulos.value = await fetchApi(url)
  cargando.value = false
}

function seleccionarBodega(nombre) {
  bodegaActiva.value = nombre
  filtroActivo.value = null
  busqueda.value = ''
  columnFilters.value = {}
  sortKey.value = ''
  cargarArticulos()
  cargarResumen()
}

let searchTimeout
function debounceSearch() { clearTimeout(searchTimeout); searchTimeout = setTimeout(() => cargarArticulos(), 300) }

// ── Conteo ──
function onConteoConValidacion(articulo, event) {
  const valor = parseDecimal(event.target.value)
  if (isNaN(valor)) { event.target.value = displayConteo(articulo); return }

  // 0 siempre permitido
  if (valor === 0) { guardarConteo(articulo, valor); return }

  const min = articulo.rango_min
  const max = articulo.rango_max
  const factor = articulo.factor_error

  if (min != null && max != null && (valor < min || valor > max)) {
    let sugerencia = null
    let mensaje = ''

    if (factor && valor > max * 10) {
      sugerencia = +(valor / factor).toFixed(2)
      const unidad = articulo.unidad || 'UND'
      mensaje = `${valor} ${unidad} parece un error. ¿Quisiste decir ${sugerencia} ${unidad}?`
    } else if (valor < min && valor > 0) {
      mensaje = `${valor} es menor al mínimo esperado (${min}). ¿Estás seguro?`
    } else {
      mensaje = `${valor} está fuera del rango esperado (${min} — ${max}). ¿Confirmas?`
    }

    alertaRango.value = { articulo, valor, sugerencia, mensaje }
    return
  }

  guardarConteo(articulo, valor)
}

// Debounce para guardar al escribir (backup de @blur)
const _debounceTimers = {}
function onInputDebounce(articulo, event) {
  clearTimeout(_debounceTimers[articulo.id])
  _debounceTimers[articulo.id] = setTimeout(() => {
    const raw = event.target.value
    const valor = parseDecimal(raw)
    if (!isNaN(valor)) guardarConteo(articulo, valor)
  }, 1500)
}

async function guardarConteo(articulo, valor) {
  // Actualizar inmediatamente en memoria para que Vue no borre el input
  articulo.inventario_fisico = valor
  articulo.estado = 'contado'
  try {
    const res = await fetch(API + `/api/inventario/articulos/${articulo.id}/conteo`, {
      method: 'PUT', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ inventario_fisico: valor, contado_por: usuario.value })
    })
    if (!res.ok) throw new Error(`Error ${res.status}`)
    const data = await res.json()
    articulo.diferencia = data.diferencia
    cargarResumen()
    cargarBodegas()
  } catch (e) {
    articulo.estado = 'pendiente'
    console.error('Error guardando conteo:', e)
    alert('Error guardando conteo de ' + articulo.nombre + '. Verificar conexión.')
  }
}

function confirmarAlerta() {
  if (!alertaRango.value) return
  guardarConteo(alertaRango.value.articulo, alertaRango.value.valor)
  alertaRango.value = null
}

function corregirAlerta() {
  if (!alertaRango.value?.sugerencia) return
  guardarConteo(alertaRango.value.articulo, alertaRango.value.sugerencia)
  alertaRango.value = null
}

function ajustarConteo(articulo, delta) {
  const actual = articulo.inventario_fisico != null ? articulo.inventario_fisico : (articulo.inventario_teorico || 0)
  const nuevo = Math.max(0, actual + delta)
  guardarConteo(articulo, nuevo)
}

// ── Notas ──
function abrirNotas(a) { articuloNota.value = a; textoNota.value = a.notas || ''; mostrarNotas.value = true }
function cerrarNotas() { mostrarNotas.value = false; articuloNota.value = null }
async function guardarNota() {
  if (!articuloNota.value) return
  await fetch(API + `/api/inventario/articulos/${articuloNota.value.id}/nota`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notas: textoNota.value, usuario: usuario.value })
  })
  articuloNota.value.notas = textoNota.value
  cerrarNotas()
}

// ── Agregar ──
let agregarTimeout
function buscarParaAgregar() {
  clearTimeout(agregarTimeout)
  agregarTimeout = setTimeout(async () => {
    if (!busquedaAgregar.value || busquedaAgregar.value.length < 2) { resultadosAgregar.value = []; return }
    resultadosAgregar.value = await fetchApi(`/api/inventario/articulos/buscar?q=${encodeURIComponent(busquedaAgregar.value)}`)
  }, 300)
}
async function agregarArticulo(art) {
  await fetch(API + `/api/inventario/articulos/agregar`, {
    method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ fecha_inventario: FECHA.value, bodega: bodegaActiva.value || 'Principal', id_effi: art.id, contado_por: usuario.value })
  })
  cerrarModalAgregar()
  cargarArticulos(); cargarResumen(); cargarBodegas()
}

function cerrarModalAgregar() {
  mostrarAgregar.value = false
  tabAgregar.value = 'buscar'
  busquedaAgregar.value = ''; resultadosAgregar.value = []
  busquedaExcluidos.value = ''; excluidos.value = []
  manualNombre.value = ''; manualCantidad.value = ''; manualUnidad.value = 'UND'
  manualCosto.value = ''; manualNotas.value = ''; manualFoto.value = null; manualFotoNombre.value = ''
}

// ── Asignar artículo NM ──
function abrirAsignar(a) {
  articuloAsignar.value = a
  busquedaAsignar.value = ''
  resultadosAsignar.value = []
  effiSeleccionado.value = null
  mostrarAsignar.value = true
}

function cerrarAsignar() {
  mostrarAsignar.value = false
  articuloAsignar.value = null
  effiSeleccionado.value = null
  busquedaAsignar.value = ''
  resultadosAsignar.value = []
}

let _timerAsignar = null
function buscarParaAsignar() {
  clearTimeout(_timerAsignar)
  if (!busquedaAsignar.value || busquedaAsignar.value.length < 2) { resultadosAsignar.value = []; return }
  _timerAsignar = setTimeout(async () => {
    resultadosAsignar.value = await fetchApi(`/api/inventario/articulos/buscar?q=${encodeURIComponent(busquedaAsignar.value)}`)
  }, 300)
}

function seleccionarEffi(art) {
  effiSeleccionado.value = art
}

const unidadesCoinciden = computed(() => {
  if (!articuloAsignar.value || !effiSeleccionado.value) return true
  return (articuloAsignar.value.unidad || 'UND') === effiSeleccionado.value.unidad
})

async function confirmarAsignacion() {
  if (!effiSeleccionado.value || !articuloAsignar.value) return
  await fetch(API + '/api/inventario/articulos/asignar', {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({
      conteo_id: articuloAsignar.value.id,
      id_effi_nuevo: effiSeleccionado.value.id,
      nombre_effi: effiSeleccionado.value.nombre,
      categoria_effi: effiSeleccionado.value.categoria || '',
      cod_barras: effiSeleccionado.value.cod_barras || '',
      usuario: usuario.value
    })
  })
  cerrarAsignar()
  cargarArticulos(); cargarResumen()
}

// ── Sync Effi ──
const syncTexto = computed(() => {
  if (syncEstado.value === 'exportando') return 'Descargando...'
  if (syncEstado.value === 'importando') return 'Importando...'
  return 'Sync Effi'
})

let _syncPoll = null
async function syncEffi() {
  try {
    await fetch(API + '/api/inventario/sync-effi', { method: 'POST', headers: authHeaders() })
    syncEstado.value = 'exportando'
    syncMensaje.value = 'Descargando inventario de Effi...'
    _syncPoll = setInterval(pollSync, 3000)
  } catch { syncEstado.value = 'error'; syncMensaje.value = 'Error al iniciar sync' }
}

async function pollSync() {
  try {
    const res = await fetchApi('/api/inventario/sync-effi/estado')
    syncEstado.value = res.estado
    syncMensaje.value = res.mensaje
    if (res.estado === 'ok' || res.estado === 'error') {
      clearInterval(_syncPoll)
      if (res.estado === 'ok') {
        setTimeout(() => { syncEstado.value = 'idle'; syncMensaje.value = '' }, 5000)
      }
    }
  } catch { clearInterval(_syncPoll) }
}

// ── Costos ──
async function cargarCostos() {
  costosLoading.value = true
  try {
    const data = await fetchApi(`/api/inventario/costos?fecha=${FECHA.value}`)
    costosRows.value = data

    // Generar opciones dinámicas para filtro categoría y bodega
    const cats = [...new Set(data.map(r => r.categoria).filter(Boolean))].sort()
    const bods = [...new Set(data.map(r => r.bodega).filter(Boolean))].sort()
    const catCol = costosColumns.value.find(c => c.key === 'categoria')
    const bodCol = costosColumns.value.find(c => c.key === 'bodega')
    if (catCol) catCol.options = cats.map(c => ({ value: c, label: c }))
    if (bodCol) bodCol.options = bods.map(b => ({ value: b, label: b }))
  } catch (e) {
    console.error('Error cargando costos:', e)
  } finally {
    costosLoading.value = false
  }
}

// ── Gestión ──
function fmtMoney(val) {
  if (val == null) return '0'
  const n = Math.abs(val)
  if (n >= 1000000) return (val < 0 ? '-' : '') + (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (val < 0 ? '-' : '') + (n / 1000).toFixed(0) + 'K'
  return val.toFixed(0)
}

function gesEstadoLabel(est) {
  const map = { pendiente: 'Pendiente', analizado: 'Analizado', justificada: 'Justificada', requiere_ajuste: 'Req. ajuste', ajustada: 'Ajustada' }
  return map[est] || est
}

async function cargarGestion() {
  await cargarGesDashboard()
  await cargarGesArticulos()
}

async function cargarGesDashboard() {
  gesDash.value = await fetchApi(`/api/inventario/gestion/dashboard?fecha=${FECHA.value}`)
  if (gesDash.value?.vacio) {
    // Poblar si no existe
    await fetch(API + '/api/inventario/gestion/calcular', {
      method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ fecha_inventario: FECHA.value, usuario: usuario.value })
    })
    gesDash.value = await fetchApi(`/api/inventario/gestion/dashboard?fecha=${FECHA.value}`)
  }
}

async function cargarGesArticulos() {
  let url = `/api/inventario/gestion?fecha=${FECHA.value}`
  if (gesFiltroSev.value) url += `&severidad=${gesFiltroSev.value}`
  if (gesFiltroEstado.value) url += `&estado=${gesFiltroEstado.value}`
  if (gesFiltroGrupo.value) url += `&grupo=${gesFiltroGrupo.value}`
  gesArticulos.value = await fetchApi(url)
}

let _analisisPoll = null
async function lanzarAnalisis() {
  gesAnalizando.value = true
  gesProgreso.value = 0; gesTotal.value = 0
  await fetch(API + '/api/inventario/gestion/analizar', {
    method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ fecha_inventario: FECHA.value, usuario: usuario.value })
  })
  _analisisPoll = setInterval(pollAnalisis, 2000)
}

async function pollAnalisis() {
  try {
    const res = await fetchApi('/api/inventario/gestion/analisis-estado')
    gesProgreso.value = res.progreso
    gesTotal.value = res.total
    if (res.estado === 'ok' || res.estado === 'error') {
      clearInterval(_analisisPoll)
      gesAnalizando.value = false
      await cargarGestion()
    }
  } catch { clearInterval(_analisisPoll); gesAnalizando.value = false }
}

function toggleGrupoExpandido(grupo) {
  gesGruposExpandidos.value = { ...gesGruposExpandidos.value, [grupo]: !gesGruposExpandidos.value[grupo] }
}

function expandirTodos() {
  if (!gesDash.value?.por_grupo) return
  const nuevos = {}
  gesDash.value.por_grupo.filter(g => g.total > 0).forEach(g => { nuevos[g.grupo] = true })
  gesGruposExpandidos.value = nuevos
}

function colapsarTodos() {
  gesGruposExpandidos.value = {}
}

function articulosPorGrupo(grupo) {
  return gesArticulos.value.filter(a => (a.grupo || '') === grupo)
}

const gesTotalFiltrados = computed(() => gesArticulos.value.length)

async function abrirDetalleGestion(a) {
  gesDetalleData.value = await fetchApi(`/api/inventario/gestion/${a.id}/detalle`)
  gesFormEstado.value = gesDetalleData.value.gestion.estado
  gesFormCausa.value = gesDetalleData.value.gestion.causa_final || ''
  gesFormObs.value = gesDetalleData.value.gestion.observaciones || ''
  gesDetalleVisible.value = true
}

function parseEvidencia(ev) {
  if (!ev) return []
  try { return typeof ev === 'string' ? JSON.parse(ev) : ev } catch { return [] }
}

async function guardarResolucion() {
  if (!gesDetalleData.value) return
  gesGuardando.value = true
  try {
    await fetch(API + `/api/inventario/gestion/${gesDetalleData.value.gestion.id}`, {
      method: 'PUT',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        estado: gesFormEstado.value,
        causa_final: gesFormCausa.value || null,
        observaciones: gesFormObs.value || null,
        usuario: usuario.value
      })
    })
    gesDetalleVisible.value = false
    await cargarGestion()
  } catch (e) {
    console.error('Error guardando resolución:', e)
  }
  gesGuardando.value = false
}

// ── Auditoría OPs ──
async function cargarOpsRevisar() {
  let url = `/api/inventario/ops-revisar?fecha=${FECHA.value}`
  if (opsFiltroInc.value) url += `&filtro_inclusion=${opsFiltroInc.value}`
  if (opsFiltroSos.value) url += `&filtro_sospecha=${opsFiltroSos.value}`
  if (opsFiltroRev.value) url += `&filtro_revision=${opsFiltroRev.value}`
  const data = await fetchApi(url)
  opsRevisar.value = data.ops || []
  opsResumen.value = data.resumen || {}
}

async function abrirDetalleOp(op) {
  opDetalleData.value = await fetchApi(`/api/inventario/ops-revisar/${op.id}/detalle`)
  opNotaRevision.value = opDetalleData.value.op.nota_revision || ''
  opDetalleVisible.value = true
}

async function marcarOpRevisada(revisada) {
  if (!opDetalleData.value) return
  opGuardando.value = true
  try {
    await fetch(API + `/api/inventario/ops-revisar/${opDetalleData.value.op.id}`, {
      method: 'PUT',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        revisada: revisada,
        nota: opNotaRevision.value || null,
        usuario: usuario.value
      })
    })
    opDetalleVisible.value = false
    await cargarOpsRevisar()
  } catch (e) {
    console.error('Error guardando revisión OP:', e)
  }
  opGuardando.value = false
}

function formatDelta(minutos) {
  if (minutos === null || minutos === undefined) return '—'
  const abs = Math.abs(minutos)
  const signo = minutos < 0 ? '-' : '+'
  if (abs < 60) return `${signo}${abs}m`
  if (abs < 1440) {
    const h = Math.floor(abs / 60)
    const m = abs % 60
    return `${signo}${h}h ${m}m`
  }
  const d = Math.floor(abs / 1440)
  const h = Math.floor((abs % 1440) / 60)
  return `${signo}${d}d ${h}h`
}

function formatFechaCorta2(f) {
  if (!f) return '—'
  // f viene como '2026-03-31 19:48:00'
  const [fecha, hora] = f.split(' ')
  const [y, m, d] = fecha.split('-')
  return `${d}/${m} ${hora ? hora.substring(0, 5) : ''}`
}

// ── Excluidos ──
async function cargarExcluidos() {
  excluidos.value = await fetchApi(`/api/inventario/excluidos?fecha=${FECHA.value}`)
}

const excluidosFiltrados = computed(() => {
  if (!busquedaExcluidos.value) return excluidos.value
  const q = busquedaExcluidos.value.toLowerCase()
  return excluidos.value.filter(e => e.nombre.toLowerCase().includes(q))
})

async function reactivarExcluido(art) {
  await fetch(API + `/api/inventario/articulos/${art.id}/reactivar`, {
    method: 'PUT', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ usuario: usuario.value })
  })
  excluidos.value = excluidos.value.filter(e => e.id !== art.id)
  cargarArticulos(); cargarResumen(); cargarBodegas()
}

// ── No matriculado ──
function onManualFoto(event) {
  const file = event.target.files[0]
  if (file) { manualFoto.value = file; manualFotoNombre.value = file.name }
}

async function agregarNoMatriculado() {
  if (!manualNombre.value || !manualCantidad.value || !manualUnidad.value) return
  const cantidad = parseDecimal(manualCantidad.value)
  if (isNaN(cantidad)) return

  const formData = new FormData()
  formData.append('fecha_inventario', FECHA.value)
  formData.append('bodega', bodegaActiva.value || 'Principal')
  formData.append('nombre', manualNombre.value)
  formData.append('unidad', manualUnidad.value)
  formData.append('cantidad', cantidad)
  formData.append('costo', manualCosto.value || '0')
  formData.append('notas', manualNotas.value || '')
  formData.append('usuario', usuario.value)
  if (manualFoto.value) formData.append('foto', manualFoto.value)

  await fetch(API + '/api/inventario/articulos/no-matriculado', {
    method: 'POST', headers: authHeaders(), body: formData
  })
  cerrarModalAgregar()
  cargarArticulos(); cargarResumen(); cargarBodegas()
}

// ── Menú acciones ──
function toggleMenu(id) { menuAbierto.value = menuAbierto.value === id ? null : id }

// ── Fotos ──
function tomarFoto(a) {
  articuloParaFoto.value = a
  fotoInput.value?.click()
}

async function onFotoCapturada(event) {
  const file = event.target.files[0]
  if (!file || !articuloParaFoto.value) return

  const formData = new FormData()
  formData.append('file', file)
  formData.append('usuario', usuario.value)

  const res = await fetch(API + `/api/inventario/articulos/${articuloParaFoto.value.id}/foto`, {
    method: 'POST',
    headers: authHeaders(),
    body: formData
  }).then(r => r.json())

  articuloParaFoto.value.foto = res.foto
  articuloParaFoto.value = null
  event.target.value = ''
}

function verFoto(a) {
  articuloFoto.value = a
  mostrarFoto.value = true
}

// ── Gestión de inventarios ──
async function crearInventario() {
  if (!nuevaFechaInv.value) return
  creandoInv.value = true
  await fetch(API + '/api/inventario/nuevo', {
    method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ fecha_inventario: nuevaFechaInv.value, usuario: usuario.value })
  })
  mostrarNuevoInv.value = false
  nuevaFechaInv.value = ''
  creandoInv.value = false
  await cargarFechas()
  cambiarFecha(nuevaFechaInv.value || FECHA.value)
}

function confirmarReiniciar() { mostrarConfirmReiniciar.value = true }
function confirmarEliminar() { mostrarConfirmEliminar.value = true }

function cerrarModalReiniciar() {
  mostrarConfirmReiniciar.value = false
  textoConfirmReiniciar.value = ''
}

async function ejecutarReiniciar() {
  if (textoConfirmReiniciar.value !== 'REINICIAR') return
  await fetch(API + '/api/inventario/reiniciar', {
    method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ fecha_inventario: FECHA.value, usuario: usuario.value })
  })
  cerrarModalReiniciar()
  await cargarArticulos()
  await cargarResumen()
  await cargarBodegas()
}

async function ejecutarEliminar() {
  await fetch(API + '/api/inventario/eliminar', {
    method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ fecha_inventario: FECHA.value, usuario: usuario.value })
  })
  mostrarConfirmEliminar.value = false
  await cargarFechas()
  if (fechasInventario.value.length) {
    cambiarFecha(fechasInventario.value[0].fecha_inventario)
  } else {
    articulos.value = []
    resumen.value = {}
  }
}

async function cargarEstadoCierre() {
  try {
    estadoCierre.value = await fetchApi(`/api/inventario/estado-cierre?fecha=${FECHA.value}`)
  } catch { estadoCierre.value = { conteo_cerrado: false, inventario_cerrado: false } }
}

function confirmarCerrarConteo() { mostrarConfirmCerrarConteo.value = true }
function confirmarCerrarInventario() { mostrarConfirmCerrarInventario.value = true }
function confirmarReabrirConteo() { mostrarConfirmReabrirConteo.value = true }

async function ejecutarCerrarConteo() {
  await fetch(API + '/api/inventario/cerrar-conteo', {
    method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ fecha_inventario: FECHA.value, usuario: usuario.value })
  })
  mostrarConfirmCerrarConteo.value = false
  await cargarEstadoCierre()
  await cargarArticulos()
  await cargarResumen()
}

async function ejecutarCerrarInventario() {
  const res = await fetch(API + '/api/inventario/cerrar-inventario', {
    method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ fecha_inventario: FECHA.value, usuario: usuario.value })
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    alert('Error: ' + (err.detail || 'No se pudo cerrar el inventario'))
    return
  }
  mostrarConfirmCerrarInventario.value = false
  await cargarEstadoCierre()
}

async function ejecutarReabrirConteo() {
  await fetch(API + '/api/inventario/reabrir-conteo', {
    method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ fecha_inventario: FECHA.value, usuario: usuario.value })
  })
  mostrarConfirmReabrirConteo.value = false
  await cargarEstadoCierre()
  await cargarArticulos()
}

// ── Inventario teórico ──
async function cargarEstadoTeorico() {
  if (!FECHA.value) return
  const res = await fetch(API + `/api/inventario/teorico/estado?fecha=${FECHA.value}`, { headers: authHeaders() })
  estadoTeorico.value = await res.json()
}

async function calcularTeorico() {
  calculandoTeorico.value = true
  try {
    const res = await fetch(API + '/api/inventario/calcular-teorico', {
      method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ fecha_inventario: FECHA.value, usuario: usuario.value })
    })
    if (!res.ok) throw new Error('Error al calcular')
    await cargarEstadoTeorico()
    await cargarArticulos()
    await cargarResumen()
  } catch (e) {
    alert('Error calculando inventario teórico: ' + e.message)
  } finally {
    calculandoTeorico.value = false
  }
}

// ── Helpers visuales ──
function parseDecimal(str) {
  if (str == null || str === '') return NaN
  return parseFloat(String(str).replace(',', '.'))
}
function displayConteo(a) {
  return a.inventario_fisico != null ? a.inventario_fisico : ''
}
function inicialesDe(nombre) {
  if (!nombre) return ''
  return nombre.split(' ').map(p => p[0]).join('').substring(0, 2).toUpperCase()
}
const GRUPO_NOMBRES = { MP: 'Materia Prima', PP: 'Producto en Proceso', PT: 'Producto Terminado', INS: 'Insumos', DS: 'Desarrollo', DES: 'Desperdicio', NM: 'No Matriculado' }
const GRUPO_CORTOS = { MP: 'M.Prima', PP: 'Proceso', PT: 'P.Term', INS: 'Insumo', DS: 'Desarr', DES: 'Desper', NM: 'NoMatr' }
function grupoNombre(g) { return GRUPO_NOMBRES[g] || g || '' }
function grupoCorto(g) { return GRUPO_CORTOS[g] || g || '' }
function fmtNum(n) { return n != null ? Math.round(n) : '—' }
function clasesFila(a) { return a.estado === 'contado' ? (a.diferencia === 0 ? 'row-ok' : 'row-diff') : '' }
function claseDot(a) { if (a.estado === 'pendiente') return 'dot-pending'; if (a.diferencia === 0) return 'dot-ok'; return Math.abs(a.diferencia) >= 10 ? 'dot-critical' : 'dot-warning' }
function claseInput(a) { if (a.inventario_fisico == null) return ''; if (a.diferencia === 0) return 'input-ok'; return Math.abs(a.diferencia) >= 10 ? 'input-critical' : 'input-warning' }
function claseBadge(a) { if (a.estado === 'pendiente') return 'badge-empty'; if (a.diferencia === 0) return 'badge-ok'; return Math.abs(a.diferencia) >= 10 ? 'badge-error' : 'badge-warning' }
function textoBadge(a) { if (a.estado === 'pendiente') return '—'; if (a.diferencia === 0) return 'OK'; return (a.diferencia > 0 ? '+' : '') + Math.round(a.diferencia) }

// ── Permisos ──
function puede(accion) {
  const config = politicas.value.acciones?.[accion]
  return config && nivelUsuario.value >= config.nivel_minimo
}

// ── Auth ──
function initGoogleSignIn() {
  const checkGoogle = setInterval(() => {
    if (window.google?.accounts?.id) {
      clearInterval(checkGoogle)
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: onGoogleCallback,
        ux_mode: 'popup'
      })
      window.google.accounts.id.renderButton(
        document.getElementById('google-signin-btn'),
        { theme: 'filled_black', size: 'large', width: 280, text: 'continue_with', locale: 'es' }
      )
    }
  }, 100)
}

async function onGoogleCallback(response) {
  loginCargando.value = true
  loginError.value = ''
  try {
    const res = await fetch(AUTH_API + '/api/gestion/auth/google', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: response.credential })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Error de autenticación')

    localStorage.setItem(KEY_JWT, data.token)
    localStorage.setItem(KEY_USUARIO, JSON.stringify(data.usuario))
    establecerUsuario(data.usuario)
    autenticado.value = true
    await nextTick()
    await cargarDatos()
  } catch (e) {
    loginError.value = e.message
  } finally {
    loginCargando.value = false
  }
}

function establecerUsuario(u) {
  if (u?.nombre) {
    usuario.value = u.nombre
    iniciales.value = u.nombre.split(' ').map(p => p[0]).join('').substring(0, 2).toUpperCase()
  }
  if (u?.nivel) nivelUsuario.value = u.nivel
}

function cerrarSesion() {
  localStorage.removeItem(KEY_JWT)
  localStorage.removeItem(KEY_USUARIO)
  autenticado.value = false
  usuario.value = ''
  iniciales.value = ''
  nivelUsuario.value = 1
  nextTick(() => initGoogleSignIn())
}

function verificarSesion() {
  const token = localStorage.getItem(KEY_JWT)
  const usr = localStorage.getItem(KEY_USUARIO)
  if (token && usr) {
    try {
      const u = JSON.parse(usr)
      establecerUsuario(u)
      autenticado.value = true
      return true
    } catch {}
  }
  return false
}

async function cargarPoliticas() {
  try { politicas.value = await fetchApi('/api/inventario/politicas') } catch {}
}

async function cargarDatos() {
  await cargarPoliticas()
  await cargarFechas(); await cargarBodegas(); await cargarResumen(); await cargarArticulos(); await cargarEstadoTeorico()
}

onMounted(async () => {
  actualizarReloj(); clockInterval = setInterval(actualizarReloj, 1000)
  document.addEventListener('click', () => { mostrarListaBodegas.value = false; menuAbierto.value = null })

  if (verificarSesion()) {
    await cargarDatos()
  } else {
    nextTick(() => initGoogleSignIn())
  }
})
onUnmounted(() => clearInterval(clockInterval))
</script>

<style scoped>
/* LOGIN */
.inv-login { display: flex; align-items: center; justify-content: center; height: 100vh; background: var(--bg-app); }
.inv-login-card { background: var(--bg-card, #1c1c1e); border: 1px solid var(--border-default); border-radius: 12px; padding: 40px 36px; text-align: center; width: 360px; box-shadow: 0 20px 80px rgba(0,0,0,0.5); }
.inv-login-logo { width: 48px; height: 48px; border-radius: 12px; background: var(--accent-muted); color: var(--accent); display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: 700; margin: 0 auto 16px; }
.inv-login-title { font-size: 20px; font-weight: 600; margin-bottom: 4px; }
.inv-login-subtitle { font-size: 13px; color: var(--text-secondary); margin-bottom: 28px; }
.inv-login-btn-wrap { display: flex; justify-content: center; margin-bottom: 12px; }
.inv-login-error { color: var(--color-error); font-size: 12px; margin-top: 8px; }
.inv-login-loading { color: var(--text-tertiary); font-size: 12px; margin-top: 8px; }

.inv-app { display: flex; height: 100dvh; overflow: hidden; }
.inv-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

/* SIDE PANEL */
.inv-panel { width: 0; overflow: hidden; background: var(--bg-sidebar); border-right: 1px solid var(--border-default); display: flex; flex-direction: column; transition: width 0.2s ease; flex-shrink: 0; min-height: 0; }
.inv-panel.open { width: 240px; }
.inv-panel-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid var(--border-subtle); }
.inv-panel-title { font-size: 13px; font-weight: 600; }
.inv-panel-list { flex: 1; overflow-y: auto; padding: 6px; }
.inv-panel-item { padding: 8px 10px; border-radius: 4px; cursor: pointer; margin-bottom: 2px; transition: background 0.08s; }
.inv-panel-item:hover { background: rgba(255,255,255,0.04); }
.inv-panel-item.active { background: var(--accent-muted); }
.inv-panel-item-fecha { font-size: 13px; font-weight: 500; }
.inv-panel-item.active .inv-panel-item-fecha { color: var(--accent); }
.inv-panel-item-stats { font-size: 11px; color: var(--text-tertiary); display: flex; justify-content: space-between; margin-top: 2px; }
.inv-panel-item-pct { font-family: 'Fragment Mono', monospace; }
.inv-panel-empty { text-align: center; color: var(--text-tertiary); padding: 24px; font-size: 12px; }
.inv-panel-action-spin { pointer-events: none; opacity: 0.7; }
@keyframes spin-anim { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }
.spin { animation: spin-anim 1s linear infinite; }
.inv-panel-add { width: 22px; height: 22px; border-radius: 4px; border: 1px dashed var(--border-strong); background: transparent; color: var(--text-tertiary); cursor: pointer; display: flex; align-items: center; justify-content: center; margin-left: auto; }
.inv-panel-add:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-muted); }
.inv-panel-item-main { cursor: pointer; flex: 1; }
.inv-panel-item-actions { display: flex; gap: 2px; margin-top: 4px; }
.inv-panel-action { width: 24px; height: 24px; border: none; background: transparent; color: var(--text-tertiary); cursor: pointer; border-radius: 4px; display: flex; align-items: center; justify-content: center; }
.inv-panel-action:hover { background: rgba(255,255,255,0.06); color: var(--text-primary); }
.inv-panel-action-danger:hover { background: rgba(248,113,113,0.1); color: var(--color-error); }
.inv-form-label { font-size: 12px; font-weight: 500; color: var(--text-secondary); margin-bottom: 6px; display: block; }
.inv-form-input { width: 100%; height: 36px; background: var(--bg-input); border: 1px solid var(--border-strong); border-radius: 4px; padding: 0 10px; color: var(--text-primary); font-size: 13px; font-family: inherit; margin-bottom: 8px; }
.inv-form-input:focus { border-color: var(--accent); outline: none; }
.inv-form-hint { font-size: 11px; color: var(--text-tertiary); margin-bottom: 16px; line-height: 1.4; }
.inv-btn-danger { background: var(--color-error); color: #fff; border: none; padding: 8px 16px; border-radius: 4px; font-size: 13px; font-weight: 600; cursor: pointer; width: 100%; }
.inv-btn-danger:hover { opacity: 0.9; }
.inv-panel-toggle { width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border: none; background: transparent; color: var(--text-secondary); cursor: pointer; border-radius: 4px; margin-right: 4px; }
.inv-panel-toggle:hover { background: rgba(255,255,255,0.06); }

/* HEADER */
.inv-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; background: var(--bg-sidebar); border-bottom: 1px solid var(--border-default); }
.inv-header-left { display: flex; align-items: center; gap: 10px; }
.inv-avatar { width: 28px; height: 28px; border-radius: 50%; background: var(--accent-muted); color: var(--accent); display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; }
.inv-user-info { display: flex; flex-direction: column; }
.inv-user-name { font-size: 13px; font-weight: 500; }
.inv-panel-logout { margin-top: auto; padding: 12px 14px; padding-bottom: calc(12px + env(safe-area-inset-bottom, 16px)); border-top: 1px solid var(--border-default); font-size: 12px; color: var(--text-tertiary); cursor: pointer; display: flex; align-items: center; gap: 6px; }
.inv-panel-logout:hover { color: var(--text-primary); background: var(--bg-overlay); }
.inv-title { font-size: 12px; color: var(--accent); font-weight: 500; }
.inv-header-right { display: flex; align-items: center; gap: 16px; }
.inv-clock { font-size: 11px; color: var(--text-tertiary); font-family: 'Fragment Mono', 'JetBrains Mono', monospace; }
.inv-progress-wrap { display: flex; align-items: center; gap: 10px; width: 240px; }
.inv-progress-track { flex: 1; height: 4px; background: rgba(255,255,255,0.06); border-radius: 2px; overflow: hidden; display: flex; }
.inv-progress-ok { background: var(--color-ok); height: 100%; transition: width 0.3s ease; }
.inv-progress-diff { background: var(--color-warning); height: 100%; transition: width 0.3s ease; }
.inv-progress-text { font-size: 12px; color: var(--text-secondary); font-family: 'Fragment Mono', monospace; white-space: nowrap; }

/* TOOLBAR */
.inv-toolbar { padding: 8px 16px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid var(--border-subtle); }
.inv-search-box { flex: 1; display: flex; align-items: center; background: var(--bg-input); border: 1px solid var(--border-default); border-radius: 4px; padding: 0 10px; height: 32px; gap: 8px; }
.inv-search-box:focus-within { border-color: var(--accent); }
.inv-search-icon { font-size: 18px; color: var(--text-tertiary); }
.inv-search-input { flex: 1; background: none; border: none; color: var(--text-primary); font-size: 13px; outline: none; }
.inv-search-input::placeholder { color: var(--text-tertiary); }
.inv-btn-scan { height: 32px; padding: 0 12px; background: var(--accent-muted); border: 1px solid var(--accent-border); border-radius: 4px; color: var(--accent); font-size: 13px; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 6px; }
.inv-btn-scan:hover { background: rgba(0,200,83,0.18); }

/* FILTROS + BODEGAS */
.inv-filters-row { padding: 6px 16px; display: flex; align-items: center; gap: 4px; border-bottom: 1px solid var(--border-subtle); flex-wrap: wrap; }
.inv-pill { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; cursor: pointer; border: 1px solid transparent; background: transparent; color: var(--text-secondary); transition: all 0.1s ease-out; white-space: nowrap; }
.inv-pill:hover { background: rgba(255,255,255,0.04); }
.inv-pill.active { background: var(--accent-muted); color: var(--accent); border-color: var(--accent-border); }
.inv-pill-count { font-size: 11px; opacity: 0.7; margin-left: 4px; font-family: 'Fragment Mono', monospace; }
.inv-separator { width: 1px; height: 20px; background: var(--border-strong); margin: 0 6px; flex-shrink: 0; }
.inv-bodegas-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-tertiary); margin-right: 2px; }
.inv-pill-bodega { }
.inv-bodega-add-wrap { position: relative; }
.inv-bodega-add-btn { width: 24px; height: 24px; border-radius: 12px; border: 1px dashed var(--border-strong); background: transparent; color: var(--text-tertiary); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.1s; }
.inv-bodega-add-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-muted); }
.inv-bodega-dropdown { position: absolute; top: calc(100% + 6px); left: 0; background: var(--bg-card, #1c1c1e); border: 1px solid var(--border-strong); border-radius: 8px; box-shadow: 0 8px 40px rgba(0,0,0,0.7); min-width: 200px; z-index: 100; padding: 4px; animation: popup-col-in 100ms ease-out; }
.inv-bodega-dropdown-title { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; color: var(--text-tertiary); padding: 8px 10px 4px; }
.inv-bodega-dropdown-item { padding: 7px 10px; border-radius: 4px; cursor: pointer; font-size: 13px; color: var(--text-secondary); }
.inv-bodega-dropdown-item:hover { background: rgba(255,255,255,0.04); color: var(--text-primary); }
.inv-bodega-dropdown-empty { padding: 12px 10px; font-size: 12px; color: var(--text-tertiary); text-align: center; }

/* TABLE */
.inv-table-container { flex: 1; overflow: auto; }
.inv-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.col-status { width: 32px; }
.col-id { width: 60px; }
.col-articulo { width: auto; }
.col-categoria { width: 80px; }
.col-conteo { width: 280px; }
.inv-table thead { position: sticky; top: 0; z-index: 5; }

.th { text-align: left; padding: 0 12px; height: 36px; font-size: 11px; font-weight: 600; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--border-default); background: var(--bg-card, #1c1c1e); position: sticky; top: 0; z-index: 5; cursor: pointer; user-select: none; white-space: nowrap; transition: color 80ms; }
.th:hover { color: var(--text-secondary); }
.th-nosort { cursor: default; }
.th-nosort:hover { color: var(--text-tertiary); }
.th-inner { display: flex; align-items: center; gap: 4px; }
.th-label { flex: 1; }
.sort-icon { font-size: 14px !important; color: var(--accent); }
.th-sorted { color: var(--accent); }
.th-filter-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--accent); flex-shrink: 0; }
.th-filtered { color: var(--accent); }
.th-popup-open { background: var(--bg-row-hover); }
.th-conteo { text-align: right; padding-right: 48px; }

.td { padding: 0 12px; height: 44px; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); vertical-align: middle; white-space: nowrap; }
.inv-table tr:hover .td { background: var(--bg-row-hover); }
.inv-table tr.row-ok .td { background: rgba(34,197,94,0.02); }
.inv-table tr.row-diff .td { background: rgba(248,161,1,0.03); }
.td-center { text-align: center; }
.td-empty { height: 80px; text-align: center; color: var(--text-tertiary); font-size: 13px; border-bottom: none; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; }

.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot-pending { border: 1.5px solid var(--color-pending); background: transparent; }
.dot-ok { background: var(--color-ok); box-shadow: 0 0 6px rgba(34,197,94,0.3); }
.dot-warning { background: var(--color-warning); box-shadow: 0 0 6px rgba(245,158,11,0.3); }
.dot-critical { background: var(--color-error); box-shadow: 0 0 6px rgba(248,113,113,0.3); }

.cell-id { font-size: 12px; color: var(--text-tertiary); font-family: 'Fragment Mono', monospace; }
.cell-articulo { font-size: 13px; color: var(--text-primary); }
.articulo-line1 { display: flex; align-items: center; gap: 4px; overflow: hidden; }
.articulo-teorico-movil { display: none; }
.articulo-line2 { display: none; }
.grupo-tag { font-size: 8px; font-weight: 700; letter-spacing: 0.3px; padding: 1px 4px; border-radius: 3px; flex-shrink: 0; }
.grupo-mp { background: rgba(59,130,246,0.15); color: #60a5fa; }
.grupo-pp { background: rgba(168,85,247,0.15); color: #c084fc; }
.grupo-pt { background: rgba(34,197,94,0.15); color: #4ade80; }
.grupo-ins { background: rgba(245,158,11,0.15); color: #fbbf24; }
.grupo-ds { background: rgba(107,114,128,0.15); color: #9ca3af; }
.grupo-des { background: rgba(239,68,68,0.15); color: #f87171; }
.grupo-nm { background: rgba(14,165,233,0.15); color: #38bdf8; }
.articulo-nombre { white-space: normal; word-break: break-word; line-height: 1.3; }
.unit-tag { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; padding: 1px 5px; border-radius: 3px; background: rgba(0,200,83,0.12); color: var(--accent); flex-shrink: 0; }
.cell-categoria { font-size: 12px; cursor: default; }
.grupo-tag-full { white-space: normal; line-height: 1.3; }
.grupo-tag-short { display: none; }

/* CONTEO CELL */
.conteo-cell { display: flex; align-items: center; justify-content: flex-end; gap: 8px; height: 44px; }
.teorico-block { display: flex; flex-direction: column; align-items: flex-end; min-width: 30px; }
.teorico-label { font-size: 8px; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.3px; }
.teorico-value { font-size: 12px; color: var(--text-secondary); font-family: 'Fragment Mono', monospace; font-weight: 500; }
.stepper { display: flex; align-items: center; gap: 0; }
.stepper-btn { width: 24px; height: 32px; border: 1px solid var(--border-default); background: transparent; color: var(--text-tertiary); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.08s; }
.stepper-btn:hover { background: rgba(255,255,255,0.06); color: var(--text-primary); }
.stepper-btn:active { background: var(--accent-muted); color: var(--accent); }
.stepper-down { border-radius: 4px 0 0 4px; border-right: none; }
.stepper-up { border-radius: 0 4px 4px 0; border-left: none; }
.count-input { width: 60px; height: 32px; background: var(--bg-input); border: 1px solid var(--border-strong); border-radius: 0; color: var(--text-primary); font-size: 13px; font-weight: 500; font-family: 'Fragment Mono', monospace; text-align: center; outline: none; -moz-appearance: textfield; }
.count-input::-webkit-inner-spin-button, .count-input::-webkit-outer-spin-button { -webkit-appearance: none; }
.count-input:focus { border-color: var(--accent); box-shadow: 0 0 0 2px rgba(0,200,83,0.15); }
.input-ok { border-color: var(--color-ok); background: rgba(34,197,94,0.06); }
.input-warning { border-color: var(--color-warning); background: rgba(245,158,11,0.06); }
.input-critical { border-color: var(--color-error); background: rgba(248,113,113,0.06); }
.diff-badge { font-size: 11px; font-weight: 600; font-family: 'Fragment Mono', monospace; padding: 2px 6px; border-radius: 10px; min-width: 32px; text-align: center; }
.badge-ok { background: rgba(34,197,94,0.12); color: #4ade80; }
.badge-warning { background: rgba(245,158,11,0.12); color: #fbbf24; }
.badge-error { background: rgba(248,113,113,0.12); color: #f87171; }
.badge-empty { color: var(--text-tertiary); }
.diff-col { display: flex; align-items: center; gap: 4px; }
.contador-chip { font-size: 8px; font-weight: 600; font-family: 'Fragment Mono', monospace; padding: 1px 4px; border-radius: 3px; background: rgba(255,255,255,0.06); color: var(--text-tertiary); letter-spacing: 0.3px; }
.diff-col { display: flex; flex-direction: column; align-items: center; gap: 1px; min-width: 32px; }
.contado-por { font-size: 8px; color: var(--text-tertiary); font-family: 'Fragment Mono', monospace; letter-spacing: 0.3px; }

.action-menu-wrap { position: relative; }
.action-btn { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border: none; background: transparent; color: var(--text-tertiary); cursor: pointer; border-radius: 4px; }
.action-btn:hover { background: rgba(255,255,255,0.06); color: var(--text-secondary); }
.action-btn.has-note { color: var(--accent); }
.action-menu { position: absolute; right: 0; top: calc(100% + 4px); background: var(--bg-card, #1c1c1e); border: 1px solid var(--border-strong); border-radius: 6px; box-shadow: 0 8px 30px rgba(0,0,0,0.6); min-width: 160px; z-index: 100; padding: 4px; animation: popup-col-in 80ms ease-out; }
.action-menu-item { display: flex; align-items: center; gap: 8px; padding: 7px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; color: var(--text-secondary); white-space: nowrap; }
.action-menu-item:hover { background: rgba(255,255,255,0.04); color: var(--text-primary); }
.inv-foto-preview { width: 100%; max-height: 60vh; object-fit: contain; display: block; border-radius: 0 0 8px 8px; }

/* FAB */
.inv-fab { position: fixed; bottom: 24px; right: 24px; width: 44px; height: 44px; border-radius: 50%; background: var(--accent); color: #000; border: none; cursor: pointer; box-shadow: 0 4px 20px rgba(0,200,83,0.4); display: flex; align-items: center; justify-content: center; z-index: 20; }
.inv-fab:hover { transform: scale(1.08); }

/* MODALS */
.inv-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.65); z-index: 50; display: flex; align-items: center; justify-content: center; }
.inv-modal { background: var(--bg-card, #1c1c1e); border: 1px solid var(--border-default); border-radius: 8px; width: 460px; max-height: 80vh; display: flex; flex-direction: column; box-shadow: 0 20px 80px rgba(0,0,0,0.8); transition: width 0.2s ease; }
.inv-modal-sm { width: 380px; }
.inv-modal-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid var(--border-subtle); font-weight: 500; }
.inv-modal-body { padding: 16px; }
.inv-modal-expanded { width: 500px; }
.inv-modal-tabs { display: flex; border-bottom: 1px solid var(--border-subtle); padding: 0 16px; }
.inv-modal-tab { padding: 8px 14px; font-size: 12px; font-weight: 500; color: var(--text-tertiary); background: none; border: none; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; transition: all 0.1s; }
.inv-modal-tab:hover { color: var(--text-secondary); }
.inv-modal-tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.inv-modal-result-sub { font-size: 10px; color: var(--text-tertiary); margin-top: 1px; }
.inv-form-group { margin-bottom: 12px; }
.inv-form-row { display: flex; gap: 12px; }
.inv-form-half { flex: 1; }
.inv-btn-outline { display: flex; align-items: center; gap: 6px; height: 32px; padding: 0 12px; background: transparent; border: 1px solid var(--border-strong); border-radius: 4px; color: var(--text-secondary); font-size: 12px; cursor: pointer; width: 100%; }
.inv-btn-outline:hover { border-color: var(--accent); color: var(--accent); }
.inv-modal-search { width: 100%; background: var(--bg-input); border: 1px solid var(--border-strong); border-radius: 4px; padding: 8px 12px; margin-bottom: 12px; color: var(--text-primary); font-size: 13px; outline: none; }
.inv-modal-search:focus { border-color: var(--accent); }
.inv-modal-results { max-height: 300px; overflow-y: auto; }
.inv-modal-result-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; border-radius: 4px; cursor: pointer; }
.inv-modal-result-item:hover { background: rgba(255,255,255,0.04); }
.inv-modal-result-name { font-size: 13px; }
.inv-modal-result-id { font-size: 11px; color: var(--text-tertiary); font-family: 'Fragment Mono', monospace; }
.inv-modal-empty { text-align: center; color: var(--text-tertiary); padding: 20px; }
.inv-nota-textarea { width: 100%; background: var(--bg-input); border: 1px solid var(--border-strong); border-radius: 4px; padding: 10px; color: var(--text-primary); font-size: 13px; font-family: inherit; resize: vertical; margin-bottom: 12px; outline: none; }
.inv-nota-textarea:focus { border-color: var(--accent); }
.inv-btn-primary { background: var(--accent); color: #000; border: none; padding: 8px 16px; border-radius: 4px; font-size: 13px; font-weight: 600; cursor: pointer; width: 100%; }
.inv-btn-primary:hover { background: var(--accent-hover); }

/* Alerta de rango */
.inv-modal-header-warn { gap: 8px; }
.alerta-articulo { font-size: 14px; font-weight: 500; margin-bottom: 8px; }
.alerta-mensaje { font-size: 13px; color: var(--text-secondary); margin-bottom: 16px; line-height: 1.5; }
.alerta-btns { display: flex; flex-direction: column; gap: 8px; }
.alerta-btn-confirmar { background: transparent; border: 1px solid var(--border-strong); color: var(--text-secondary); padding: 8px 16px; border-radius: 4px; font-size: 13px; cursor: pointer; width: 100%; }
.alerta-btn-confirmar:hover { background: rgba(255,255,255,0.04); color: var(--text-primary); }

/* ═══ TABS ═══ */
.inv-tabs { display: flex; border-bottom: 1px solid var(--border-subtle); padding: 0 16px; background: var(--bg-sidebar); }
.inv-tab { display: flex; align-items: center; gap: 5px; padding: 8px 16px; font-size: 13px; font-weight: 500; color: var(--text-tertiary); background: none; border: none; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; transition: all 0.15s; }
.inv-tab:hover { color: var(--text-secondary); }
.inv-tab.active { color: var(--accent); border-bottom-color: var(--accent); }

/* ═══ GESTIÓN DASHBOARD ═══ */
.ges-dashboard { padding: 12px 16px; }
.ges-kpis { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }
.ges-kpi { background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 10px 14px; flex: 1; min-width: 120px; }
.ges-kpi-label { font-size: 10px; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.5px; }
.ges-kpi-value { font-size: 18px; font-weight: 600; color: var(--text-primary); margin-top: 2px; }
.ges-kpi-value small { font-size: 12px; color: var(--text-tertiary); font-weight: 400; }
.ges-kpi-impacto.neg .ges-kpi-value { color: #f87171; }
.ges-kpi-impacto.pos .ges-kpi-value { color: #4ade80; }

.ges-severidad-row { display: flex; gap: 8px; margin-bottom: 10px; }
.ges-sev-card { flex: 1; padding: 8px 12px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: all 0.15s; }
.ges-sev-card:hover { filter: brightness(1.2); }
.ges-sev-count { font-size: 20px; font-weight: 700; }
.ges-sev-label { font-size: 11px; color: var(--text-secondary); }
.ges-sev-critica { background: rgba(239,68,68,0.1); color: #f87171; }
.ges-sev-significativa { background: rgba(245,158,11,0.1); color: #fbbf24; }
.ges-sev-menor { background: rgba(59,130,246,0.1); color: #60a5fa; }

.ges-grupos-table { margin-bottom: 8px; }

/* ═══ CIERRES ═══ */
.cierre-badge { display: inline-flex; align-items: center; gap: 3px; font-size: 9px; font-weight: 700; padding: 1px 5px; border-radius: 3px; margin-left: 6px; vertical-align: middle; letter-spacing: 0.3px; }
.cierre-badge-conteo { background: rgba(245,158,11,0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
.cierre-badge-full { background: rgba(168,85,247,0.15); color: #c084fc; border: 1px solid rgba(168,85,247,0.3); }
.stepper-bloqueado { opacity: 0.55; }
.stepper-bloqueado .stepper-btn { cursor: not-allowed; }
.stepper-bloqueado .count-input { cursor: not-allowed; background: rgba(0,0,0,0.2); }
.inv-panel-action-warn { color: #fbbf24 !important; }
.inv-panel-action-warn:hover { background: rgba(245,158,11,0.15) !important; }

/* ═══ SUB-PESTAÑAS DE GESTIÓN ═══ */
.ges-subtabs { display: flex; gap: 4px; padding: 6px 16px 0 16px; border-bottom: 1px solid var(--border-subtle); }
.ges-subtab { display: flex; align-items: center; gap: 5px; padding: 7px 14px; font-size: 12px; font-weight: 500; color: var(--text-tertiary); background: none; border: none; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; transition: all 0.15s; position: relative; }
.ges-subtab:hover { color: var(--text-secondary); }
.ges-subtab.active { color: var(--accent); border-bottom-color: var(--accent); }
.ges-subtab-badge { background: rgba(239,68,68,0.2); color: #f87171; font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 8px; margin-left: 3px; }

/* ═══ AUDITORÍA OPs ═══ */
.ops-header { padding-bottom: 8px; }
.ops-resumen-cards { display: flex; gap: 8px; flex-wrap: wrap; }
.ops-card { flex: 1; min-width: 90px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 8px 12px; }
.ops-card-num { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.ops-card-label { font-size: 9px; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
.ops-card-incluidas .ops-card-num { color: #4ade80; }
.ops-card-excluidas .ops-card-num { color: #9ca3af; }
.ops-card-sospechosas { border-color: rgba(239,68,68,0.3); background: rgba(239,68,68,0.05); }
.ops-card-sospechosas .ops-card-num { color: #f87171; }
.ops-card-revisadas .ops-card-num { color: #60a5fa; }

.ops-table-wrap { background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 6px; overflow-x: auto; }
.ops-table { width: 100%; table-layout: fixed; }
.ops-table .td { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ops-row { cursor: pointer; }
.ops-row:hover td { background: rgba(255,255,255,0.03); }
.ops-row-sospechosa td { background: rgba(239,68,68,0.04); }
.ops-row-sospechosa:hover td { background: rgba(239,68,68,0.08); }
.ops-row-revisada { opacity: 0.55; }

.ops-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; }
.ops-dot-sospechosa { background: #f87171; box-shadow: 0 0 6px rgba(239,68,68,0.5); }
.ops-dot-normal { background: #4ade80; }

.ops-estado-chip { font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 3px; text-transform: uppercase; letter-spacing: 0.3px; }
.est-generada { background: rgba(245,158,11,0.15); color: #fbbf24; }
.est-procesada { background: rgba(107,114,128,0.15); color: #9ca3af; }

.ops-rev-chip { font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 3px; }
.ops-rev-yes { background: rgba(59,130,246,0.15); color: #60a5fa; }
.ops-rev-no { background: rgba(107,114,128,0.15); color: #9ca3af; }

.ops-fechas { font-size: 11px; line-height: 1.7; color: var(--text-secondary); }
.ops-fechas strong { color: var(--text-primary); display: inline-block; min-width: 90px; }

.td-center { text-align: center; }

/* ═══ ACORDEONES GESTIÓN ═══ */
.ges-scroll-container { flex: 1; overflow-y: auto; overflow-x: hidden; min-height: 0; }
.ges-acordeones { padding: 0 16px 20px; }
.ges-grupo-acordeon { border: 1px solid var(--border-subtle); border-radius: 6px; margin-bottom: 8px; background: var(--bg-card); overflow: hidden; }
.ges-grupo-header { display: flex; align-items: center; gap: 10px; padding: 10px 14px; cursor: pointer; transition: background 0.15s; }
.ges-grupo-header:hover { background: rgba(255,255,255,0.03); }
.ges-chevron { font-size: 18px; color: var(--text-tertiary); transition: transform 0.2s; }
.ges-chevron.expandido { transform: rotate(90deg); }
.ges-grupo-nombre { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.ges-grupo-count { font-size: 11px; color: var(--text-tertiary); background: rgba(255,255,255,0.05); padding: 2px 7px; border-radius: 10px; }
.ges-grupo-metricas { display: flex; gap: 16px; margin-left: auto; }
.ges-metrica { display: flex; flex-direction: column; align-items: flex-end; min-width: 65px; }
.ges-metrica-label { font-size: 9px; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.3px; }
.ges-metrica-value { font-size: 12px; font-weight: 500; color: var(--text-primary); }
.ges-grupo-body { border-top: 1px solid var(--border-subtle); background: rgba(0,0,0,0.15); }
.ges-table-grupo { table-layout: fixed; width: 100%; }
.ges-table-grupo .th { padding: 6px 8px; font-size: 10px; }
.ges-table-grupo .td { padding: 6px 8px; font-size: 12px; }
.ges-accion-info { font-size: 11px; color: var(--text-tertiary); margin-left: 8px; }
.ges-action-btn-sec { padding: 4px 10px; background: transparent; border: 1px solid var(--border-strong); border-radius: 4px; color: var(--text-secondary); font-size: 11px; cursor: pointer; }
.ges-action-btn-sec:hover { background: rgba(255,255,255,0.04); color: var(--text-primary); }

.ges-table-mini { width: 100%; border-collapse: collapse; font-size: 12px; }
.ges-table-mini th { padding: 5px 8px; text-align: left; color: var(--text-tertiary); font-weight: 500; font-size: 10px; text-transform: uppercase; border-bottom: 1px solid var(--border-subtle); }
.ges-table-mini td { padding: 5px 8px; border-bottom: 1px solid rgba(255,255,255,0.03); cursor: pointer; }
.ges-table-mini tr:hover td { background: rgba(255,255,255,0.02); }
.text-right { text-align: right; }
.text-red { color: #f87171; }
.text-green { color: #4ade80; }

/* ═══ GESTIÓN TABLA ═══ */
.ges-actions-bar { display: flex; gap: 8px; padding: 4px 16px; }
.ges-action-btn { display: flex; align-items: center; gap: 5px; padding: 6px 12px; background: rgba(168,85,247,0.1); border: 1px solid rgba(168,85,247,0.25); border-radius: 4px; color: #c084fc; font-size: 12px; font-weight: 500; cursor: pointer; }
.ges-action-btn:hover { background: rgba(168,85,247,0.18); }
.ges-action-btn:disabled { opacity: 0.5; cursor: wait; }

.ges-table { table-layout: fixed; }
.ges-row { cursor: pointer; }
.ges-row:hover td { background: rgba(255,255,255,0.03); }

.ges-sev-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }
.sev-ok { background: #4ade80; }
.sev-menor { background: #60a5fa; }
.sev-significativa { background: #fbbf24; }
.sev-critica { background: #f87171; }

.ges-causa { display: flex; align-items: center; gap: 4px; }
.ges-causa-text { font-size: 11px; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 120px; }
.ges-conf-badge { font-size: 9px; font-weight: 700; padding: 1px 4px; border-radius: 3px; white-space: nowrap; }
.conf-alta { background: rgba(34,197,94,0.15); color: #4ade80; }
.conf-media { background: rgba(245,158,11,0.15); color: #fbbf24; }
.conf-baja { background: rgba(239,68,68,0.15); color: #f87171; }
.ges-sin-causa { color: var(--text-tertiary); font-size: 11px; }

.ges-estado-chip { font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 3px; white-space: nowrap; }
.est-pendiente { background: rgba(107,114,128,0.15); color: #9ca3af; }
.est-analizado { background: rgba(59,130,246,0.15); color: #60a5fa; }
.est-justificada { background: rgba(34,197,94,0.15); color: #4ade80; }
.est-requiere_ajuste { background: rgba(245,158,11,0.15); color: #fbbf24; }
.est-ajustada { background: rgba(168,85,247,0.15); color: #c084fc; }

.ges-pill-critica.active { background: rgba(239,68,68,0.2); color: #f87171; border-color: rgba(239,68,68,0.4); }
.ges-pill-significativa.active { background: rgba(245,158,11,0.2); color: #fbbf24; border-color: rgba(245,158,11,0.4); }
.ges-pill-menor.active { background: rgba(59,130,246,0.2); color: #60a5fa; border-color: rgba(59,130,246,0.4); }

/* ═══ GESTIÓN MODAL DETALLE ═══ */
.ges-modal-detalle { width: 560px; max-height: 85vh; }
.ges-detalle-body { padding: 12px 16px; overflow-y: auto; max-height: 70vh; }
.ges-detalle-info { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border-subtle); margin-bottom: 10px; }
.ges-detalle-costo { font-size: 12px; color: var(--text-tertiary); }
.ges-detalle-section { margin-bottom: 14px; }
.ges-detalle-label { font-size: 10px; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; font-weight: 500; }
.ges-detalle-totales { font-size: 12px; color: var(--text-secondary); margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--border-subtle); }
.ges-detalle-ia { background: rgba(168,85,247,0.05); border: 1px solid rgba(168,85,247,0.15); border-radius: 6px; padding: 10px; }
.ges-ia-causa { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 500; color: var(--text-primary); margin-bottom: 6px; }
.ges-ia-explicacion { font-size: 12px; color: var(--text-secondary); line-height: 1.5; }
.ges-ia-evidencias { margin-top: 8px; }
.ges-ia-ev-item { display: flex; align-items: start; gap: 4px; font-size: 11px; color: var(--text-tertiary); margin-bottom: 2px; }
.ges-sin-analisis { text-align: center; padding: 16px; color: var(--text-tertiary); font-size: 12px; }
.ges-resolucion-form { display: flex; flex-direction: column; gap: 8px; }
.ges-form-row { display: flex; flex-direction: column; gap: 3px; }
.ges-form-row label { font-size: 11px; color: var(--text-tertiary); }
.ges-select { background: var(--bg-input); border: 1px solid var(--border-strong); border-radius: 4px; padding: 6px 8px; color: var(--text-primary); font-size: 13px; }
.ges-textarea { background: var(--bg-input); border: 1px solid var(--border-strong); border-radius: 4px; padding: 6px 8px; color: var(--text-primary); font-size: 13px; resize: vertical; }

/* ═══ SYNC EFFI ═══ */
.inv-btn-sync { height: 32px; padding: 0 12px; background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.25); border-radius: 4px; color: #60a5fa; font-size: 13px; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: all 0.15s; }
.inv-btn-sync:hover { background: rgba(59,130,246,0.18); }
.inv-btn-sync.syncing { opacity: 0.7; cursor: wait; }
.inv-btn-sync:disabled { cursor: wait; }
@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }
.spin { animation: spin 1s linear infinite; }

/* ═══ ASIGNAR ARTÍCULO ═══ */
.asignar-origen, .asignar-destino { background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 12px; }
.asignar-label { font-size: 10px; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.asignar-nombre { font-size: 14px; font-weight: 500; color: var(--text-primary); }
.asignar-meta { font-size: 11px; color: var(--text-tertiary); margin-top: 4px; }
.asignar-unidad-tag { display: inline-block; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px; background: rgba(59,130,246,0.15); color: #60a5fa; margin-top: 6px; }
.asignar-unidad-sm { margin-top: 0; font-size: 9px; padding: 1px 4px; }
.asignar-flecha { text-align: center; padding: 8px 0; }
.asignar-comparacion { display: flex; align-items: center; gap: 8px; margin-top: 12px; padding: 8px 12px; border-radius: 6px; font-size: 13px; font-weight: 500; }
.asignar-match { background: rgba(34,197,94,0.1); color: #4ade80; }
.asignar-mismatch { background: rgba(245,158,11,0.1); color: #fbbf24; }
.asignar-comparacion-msg { font-size: 11px; margin-left: auto; }
.asignar-btns { display: flex; gap: 8px; margin-top: 14px; }
.asignar-btns .inv-btn-primary { width: auto; flex: 1; }
.inv-btn-secondary { background: transparent; border: 1px solid var(--border-strong); color: var(--text-secondary); padding: 8px 16px; border-radius: 4px; font-size: 13px; cursor: pointer; }
.inv-btn-secondary:hover { background: rgba(255,255,255,0.04); color: var(--text-primary); }

/* ═══ TABLET (≤1024px) ═══ */
@media (max-width: 1024px) {
  .inv-panel.open { width: 220px; }
  .inv-progress-wrap { width: 180px; }
  .col-categoria { width: 140px; }
  .col-conteo { width: 240px; }
}

/* ═══ MÓVIL (≤768px) ═══ */
@media (max-width: 768px) {
  .inv-app { width: 100vw; max-width: 100vw; overflow-x: hidden; }
  .inv-content { width: 100%; min-width: 0; }

  /* Panel: overlay */
  .inv-panel.open { position: fixed; z-index: 30; width: 260px; height: 100dvh; box-shadow: 8px 0 40px rgba(0,0,0,0.6); }

  /* Header: 1 línea compacta */
  .inv-header { padding: 6px 10px; }
  .inv-header-left { gap: 6px; }
  .inv-header-left .inv-avatar { display: none; }
  .inv-user-name { font-size: 11px; }
  .inv-title { font-size: 9px; }
  .inv-clock { display: none; }
  .inv-header-right { gap: 8px; }
  .inv-progress-wrap { width: 100px; }
  .inv-progress-text { font-size: 10px; }

  /* Toolbar: compacto */
  .inv-toolbar { padding: 4px 8px; gap: 4px; }
  .inv-search-box { height: 28px; padding: 0 6px; }
  .inv-search-input { font-size: 12px; }
  .inv-search-icon { font-size: 14px; }
  .inv-btn-sync { height: 28px; padding: 0 7px; font-size: 11px; }
  .inv-btn-sync span:last-child { display: none; }
  .inv-btn-scan { height: 28px; padding: 0 7px; font-size: 11px; }
  .inv-btn-scan span:last-child { display: none; }

  /* Filtros: scroll horizontal, compacto */
  .inv-filters-row { padding: 3px 8px; overflow-x: auto; flex-wrap: nowrap; -webkit-overflow-scrolling: touch; scrollbar-width: none; gap: 3px; }
  .inv-filters-row::-webkit-scrollbar { display: none; }
  .inv-pill { padding: 2px 7px; font-size: 10px; }
  .inv-pill-count { font-size: 9px; }
  .inv-bodegas-label { display: none; }
  .inv-separator { height: 16px; margin: 0 3px; }
  .inv-bodega-add-btn { width: 20px; height: 20px; }
  .inv-bodega-dropdown { left: auto; right: 0; min-width: 180px; }

  /* 400px = status(14) + id(22) + art(auto≈170) + cat(30) + conteo(134) */
  .inv-table-container { overflow-x: hidden; }
  .col-status { width: 14px; }
  .col-id { width: 22px; }
  .col-articulo { width: auto; }
  .col-categoria { width: 30px; }
  .col-conteo { width: 134px; }
  .inv-table td { padding: 3px 2px; vertical-align: middle; }
  .inv-table th { padding: 0 2px; font-size: 8px; height: 24px; }
  .cell-id { font-size: 8px; }

  /* Artículo: wrap, nombre + unidad + teórico debajo */
  .articulo-line1 { font-size: 11px; gap: 2px; flex-wrap: nowrap; }
  .articulo-nombre { line-height: 1.25; }
  .unit-tag { font-size: 6px; padding: 0 2px; flex-shrink: 0; }
  .articulo-teorico-movil { display: block; font-size: 9px; color: var(--text-tertiary); margin-top: 1px; letter-spacing: 0.3px; }

  /* Categoría: short en móvil */
  .col-categoria { width: 36px; }
  .cell-categoria { text-align: center; }
  .grupo-tag-full { display: none; }
  .grupo-tag-short { display: inline-block; font-size: 7px; white-space: normal; word-break: break-word; line-height: 1.3; padding: 2px 3px; }

  /* Conteo: stepper + input + badge + dots */
  .teorico-block { display: none; }
  .stepper-btn { width: 20px; height: 26px; }
  .count-input { width: 32px; height: 26px; font-size: 9px; }
  .conteo-cell { gap: 1px; }
  .diff-col { flex-direction: column; gap: 0; align-items: center; }
  .diff-badge { font-size: 8px; min-width: 18px; padding: 1px 2px; }
  .contador-chip { font-size: 6px; }
  .status-dot { width: 6px; height: 6px; }
  .action-btn { width: 16px; height: 16px; }

  /* Modales */
  .inv-modal, .inv-modal-sm { width: calc(100vw - 16px); margin: 8px; }

  /* FAB */
  .inv-fab { width: 44px; height: 44px; bottom: 12px; right: 10px; }

  /* Mini menú */
  .action-menu { right: 0; left: auto; }
  .action-btn { width: 20px; height: 20px; }
}
</style>

<!-- POPUP COLUMNA — sin scoped (Teleport to body) -->
<style>
.col-popup-overlay { position: fixed; inset: 0; z-index: 9999; background: transparent; }
.col-popup { position: fixed; z-index: 10000; background: #1c1c1e; border: 1px solid rgba(255,255,255,0.18); border-radius: 8px; box-shadow: 0 8px 40px rgba(0,0,0,0.7); padding: 10px 12px; min-width: 210px; display: flex; flex-direction: column; gap: 8px; font-size: 12px; color: #fff; animation: popup-col-in 100ms ease-out; }
@keyframes popup-col-in { from { opacity: 0; transform: translateY(-3px); } to { opacity: 1; transform: none; } }
.cp-section { display: flex; flex-direction: column; gap: 5px; }
.cp-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; color: #5f6369; }
.cp-filter-row { display: flex; gap: 4px; }
.cp-select { flex: 1; height: 26px; padding: 0 6px; border: 1px solid rgba(255,255,255,0.10); border-radius: 4px; background: #1a1a1e; color: #fff; font-size: 12px; font-family: inherit; }
.cp-filter-inputs { display: flex; flex-direction: column; gap: 4px; }
.cp-input { width: 100%; height: 26px; padding: 0 8px; border: 1px solid rgba(255,255,255,0.10); border-radius: 4px; background: #1a1a1e; color: #fff; font-size: 12px; font-family: inherit; }
.cp-input:focus, .cp-select:focus { outline: none; border-color: #00C853; }
.cp-sort-btns { display: flex; flex-direction: column; gap: 3px; }
.cp-sort-btn { display: flex; align-items: center; gap: 5px; height: 28px; padding: 0 8px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.10); background: transparent; font-size: 12px; color: #8a8f98; cursor: pointer; font-family: inherit; transition: all 80ms; }
.cp-sort-btn:hover { background: #1a1a1e; color: #fff; border-color: rgba(255,255,255,0.18); }
.cp-sort-btn.active { background: rgba(0,200,83,0.12); border-color: rgba(0,200,83,0.35); color: #00C853; }
.cp-footer { border-top: 1px solid rgba(255,255,255,0.06); padding-top: 6px; }
.cp-clear-btn { width: 100%; height: 26px; border-radius: 4px; border: none; background: transparent; font-size: 12px; color: #f87171; cursor: pointer; font-family: inherit; }
.cp-clear-btn:hover { background: rgba(248,113,113,0.08); }

/* ── COSTOS ── */
.costos-container {
  padding: 12px;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.costos-container .os-table-wrapper {
  flex: 1;
  min-height: 0;
}
</style>
