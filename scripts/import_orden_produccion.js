/**
 * import_orden_produccion.js
 *
 * Crea una Orden de Producción en Effi a partir de un archivo JSON.
 *
 * Uso:
 *   node scripts/import_orden_produccion.js <archivo.json>
 *
 * Formato del JSON:
 * {
 *   "sucursal_id": 1,                    // Siempre 1 - Principal
 *   "bodega_id": 1,                      // 1 = Principal (ver import_ajuste_inventario.js)
 *   "fecha_inicio": "2026-04-21",        // YYYY-MM-DD
 *   "fecha_fin": "2026-04-21",
 *   "encargado": "74084937",             // CC del empleado (Deivy = 74084937, Jenifer = ...)
 *   "tercero": "",                       // CC del tercero (opcional)
 *   "activo_productivo_id": null,        // ID de máquina (opcional)
 *   "observacion": "LOTE xxx",
 *   "materiales": [
 *     { "cod_articulo": "178", "cantidad": 8, "costo": 24000, "lote": "", "serie": "" }
 *   ],
 *   "articulos_producidos": [
 *     { "cod_articulo": "317", "cantidad": 12, "precio": 5605, "lote": "", "serie": "" }
 *   ],
 *   "otros_costos": [
 *     { "tipo_costo_id": 1, "cantidad": 1, "costo": 5000 }
 *   ]
 * }
 *
 * IDs de bodegas: ver import_ajuste_inventario.js
 */

const { getPage } = require('./session');
const path = require('path');
const fs   = require('fs');

const EFFI_URL = 'https://effi.com.co/app/orden_produccion';

// ── Parámetros ──────────────────────────────────────────────────────────────

const jsonPath = process.argv[2];

if (!jsonPath) {
  console.error('Uso: node import_orden_produccion.js <archivo.json>');
  process.exit(1);
}
if (!fs.existsSync(jsonPath)) {
  console.error(`❌ Archivo no encontrado: ${jsonPath}`);
  process.exit(1);
}

const data = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));

// Validación básica
const required = ['sucursal_id', 'bodega_id', 'fecha_inicio', 'fecha_fin', 'encargado'];
for (const k of required) {
  if (!data[k]) {
    console.error(`❌ Campo obligatorio faltante: ${k}`);
    process.exit(1);
  }
}
data.materiales = data.materiales || [];
data.articulos_producidos = data.articulos_producidos || [];
data.otros_costos = data.otros_costos || [];
data.observacion = data.observacion || '';

if (data.materiales.length === 0 && data.articulos_producidos.length === 0) {
  console.error('❌ Se requiere al menos un material o artículo producido');
  process.exit(1);
}

console.log(`📄 Archivo: ${jsonPath}`);
console.log(`🏭 Sucursal: ${data.sucursal_id} | Bodega: ${data.bodega_id}`);
console.log(`📅 ${data.fecha_inicio} → ${data.fecha_fin}`);
console.log(`👤 Encargado: ${data.encargado}`);
console.log(`📦 Materiales: ${data.materiales.length}, Producidos: ${data.articulos_producidos.length}, Otros costos: ${data.otros_costos.length}`);

// Helper: buscar artículo mediante el modal Buscar artículo (stock).
// Apunta SIEMPRE a la última fila (.filaMateriales / .filaProducidos), que es la
// fila editable vacía. El bug histórico era usar #articulo_CRM (id duplicado en DOM)
// que siempre devolvía la PRIMERA fila y sobreescribía el material anterior.
// tipo: 'M' (material) | 'P' (producido)
async function buscarArticulo(page, tipo, codArticulo) {
  const filaClass = tipo === 'M' ? 'filaMateriales' : 'filaProducidos';
  await page.evaluate((cls) => {
    const filas = document.querySelectorAll('.' + cls);
    const ultima = filas[filas.length - 1];
    const addon = ultima.querySelector('.input-group-addon');
    addon.click();
  }, filaClass);
  await page.waitForTimeout(1500);

  await page.locator('#id_BAS').fill(String(codArticulo));
  await page.waitForTimeout(300);

  await page.locator('#modalBuscarArticuloStock button:has-text("Buscar")').first().click();
  await page.waitForTimeout(2000);

  const fila = page.locator('#modalBuscarArticuloStock tbody tr').first();
  await fila.waitFor({ state: 'visible', timeout: 5000 });
  await fila.click();
  await page.waitForTimeout(1000);
}

// Helper: llenar cantidad/costo/lote/serie en la ÚLTIMA fila (material o producido)
async function llenarUltimaFila(page, tipo, datos) {
  const filaClass = tipo === 'M' ? 'filaMateriales' : 'filaProducidos';
  const suf = tipo;                                              // 'M' o 'P'
  const precioField = tipo === 'M' ? 'costoM[]' : 'precioP[]';
  const precioVal   = tipo === 'M' ? (datos.costo || 0) : (datos.precio || 0);

  await page.evaluate(({ cls, suf, precioField, precioVal, cant, lote, serie }) => {
    const filas = document.querySelectorAll('.' + cls);
    const ultima = filas[filas.length - 1];
    const setVal = (name, v) => {
      const inp = ultima.querySelector(`[name="${name}"]`);
      if (inp) {
        inp.value = v;
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
      }
    };
    setVal(`lote${suf}[]`, lote || '');
    setVal(`serie${suf}[]`, serie || '');
    setVal(`cantidad${suf}[]`, String(cant));
    setVal(precioField, String(precioVal));
  }, { cls: filaClass, suf, precioField, precioVal, cant: datos.cantidad, lote: datos.lote, serie: datos.serie });
  await page.waitForTimeout(300);
}

// Helper: llenar cantidad/costo del ÚLTIMO costo de producción
async function llenarUltimoCosto(page, datos) {
  await page.evaluate(({ cant, costo }) => {
    const filas = document.querySelectorAll('.filaCostos');
    const ultima = filas[filas.length - 1];
    const setVal = (name, v) => {
      const inp = ultima.querySelector(`[name="${name}"]`);
      if (inp) {
        inp.value = v;
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
      }
    };
    setVal('cantidad[]', String(cant));
    setVal('costo[]', String(costo));
  }, { cant: datos.cantidad, costo: datos.costo });
  await page.waitForTimeout(300);
}

// Helper: buscar encargado/tercero (abre modal Buscar tercero y selecciona por CC/NIT)
async function buscarTercero(page, inputNombreId, idBusqueda) {
  // Click en el addon (lupa) hermano del input
  await page.evaluate((nombreId) => {
    const input = document.querySelector('#' + nombreId);
    const container = input.closest('.input-group');
    const addon = container.querySelector('.input-group-addon');
    addon.click();
  }, inputNombreId);
  await page.waitForTimeout(1500);

  // Llenar campo ID en modalBuscarTercero
  await page.locator('#id_BT').fill(String(idBusqueda));
  await page.waitForTimeout(300);

  // Click en botón Buscar del modal
  await page.locator('#modalBuscarTercero button:has-text("Buscar")').first().click();
  await page.waitForTimeout(2000);

  // Click en el primer resultado de la tabla
  const fila = page.locator('#modalBuscarTercero tbody tr').first();
  await fila.waitFor({ state: 'visible', timeout: 5000 });
  await fila.click();
  await page.waitForTimeout(1000);
}

(async () => {
  const { browser, page } = await getPage();

  try {
    console.log('🔄 Navegando a Órdenes de producción...');
    await page.goto(EFFI_URL, { waitUntil: 'networkidle', timeout: 30000 });
    if (page.url().includes('/ingreso')) {
      console.error('❌ Sesión expirada. Regenerar con session.js');
      process.exit(1);
    }
    console.log('✅ Página cargada');

    // 1. Click en Crear
    console.log('🔄 Abriendo formulario...');
    await page.locator('a:has-text("Crear"), button:has-text("Crear")').first().click();
    await page.waitForTimeout(1500);

    // 2. Sucursal
    console.log(`🔄 Sucursal: ${data.sucursal_id}`);
    await page.evaluate((id) => {
      const sel = document.querySelector('#sucursal_CR');
      sel.value = String(id);
      $(sel).trigger('change');
      $(sel).trigger('chosen:updated');
    }, data.sucursal_id);
    await page.waitForTimeout(1500);

    // 3. Bodega
    console.log(`🔄 Bodega: ${data.bodega_id}`);
    await page.evaluate((id) => {
      const sel = document.querySelector('#bodega_CR');
      sel.disabled = false;
      sel.value = String(id);
      $(sel).trigger('change');
      $(sel).trigger('chosen:updated');
    }, data.bodega_id);
    await page.waitForTimeout(1500);

    // 4. Fechas (Effi usa datepicker, pero con fill directo también funciona si es DD/MM/YYYY)
    const fmtFecha = (iso) => {
      const [y, m, d] = iso.split('-');
      return `${d}/${m}/${y}`;
    };
    console.log(`🔄 Fechas: ${fmtFecha(data.fecha_inicio)} → ${fmtFecha(data.fecha_fin)}`);
    await page.locator('#fecha_inicio_CR').fill(fmtFecha(data.fecha_inicio));
    await page.locator('#fecha_fin_CR').fill(fmtFecha(data.fecha_fin));
    // Cerrar datepicker si queda abierto
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // 5. Encargado (buscar por CC)
    console.log(`🔄 Encargado: ${data.encargado}`);
    await buscarTercero(page, 'nombre_encargado_CR', data.encargado);

    // 6. Tercero (opcional)
    if (data.tercero) {
      console.log(`🔄 Tercero: ${data.tercero}`);
      await buscarTercero(page, 'nombre_tercero_CR', data.tercero);
    }

    // 7. Activo productivo (opcional)
    if (data.activo_productivo_id) {
      await page.evaluate((id) => {
        const sel = document.querySelector('#maquina_CR');
        sel.value = String(id);
        $(sel).trigger('change');
        $(sel).trigger('chosen:updated');
      }, data.activo_productivo_id);
      await page.waitForTimeout(500);
    }

    // 8. Materiales — apuntar SIEMPRE a la última fila (.filaMateriales)
    for (let i = 0; i < data.materiales.length; i++) {
      const m = data.materiales[i];
      console.log(`  📥 Material ${i+1}/${data.materiales.length}: ${m.cod_articulo} x${m.cantidad}`);
      await buscarArticulo(page, 'M', m.cod_articulo);
      await llenarUltimaFila(page, 'M', m);
      await page.locator('#btnAgregarMaterial').click();
      await page.waitForTimeout(1000);
    }

    // 9. Artículos producidos — apuntar SIEMPRE a la última fila (.filaProducidos)
    for (let i = 0; i < data.articulos_producidos.length; i++) {
      const p = data.articulos_producidos[i];
      console.log(`  📤 Producido ${i+1}/${data.articulos_producidos.length}: ${p.cod_articulo} x${p.cantidad}`);
      await buscarArticulo(page, 'P', p.cod_articulo);
      await llenarUltimaFila(page, 'P', p);
      await page.locator('#btnAgregarProducido').click();
      await page.waitForTimeout(1000);
    }

    // 10. Otros costos — apuntar SIEMPRE a la última fila (.filaCostos)
    for (let i = 0; i < data.otros_costos.length; i++) {
      const c = data.otros_costos[i];
      console.log(`  💰 Otro costo ${i+1}/${data.otros_costos.length}: tipo ${c.tipo_costo_id} x${c.cantidad}`);
      // Seleccionar tipo en el chosen-select de la ÚLTIMA fila
      await page.evaluate(({ id }) => {
        const filas = document.querySelectorAll('.filaCostos');
        const ultima = filas[filas.length - 1];
        const sel = ultima.querySelector('select[name="costo_produccion[]"]');
        sel.value = String(id);
        $(sel).trigger('change');
        $(sel).trigger('chosen:updated');
      }, { id: c.tipo_costo_id });
      await page.waitForTimeout(400);
      await llenarUltimoCosto(page, c);
      await page.locator('#btnAgregarCosto_CR').click();
      await page.waitForTimeout(1000);
    }

    // 11. Observación
    if (data.observacion) {
      console.log(`🔄 Observación: "${data.observacion.substring(0, 50)}..."`);
      const textarea = page.locator('#form_CR textarea[name="observacion"], textarea[placeholder="Observación"]').first();
      await textarea.fill(data.observacion);
      await page.waitForTimeout(300);
    }

    // 11.b Limpiar SOLO la última fila si está vacía (cada click Agregar deja una fila vacía al final)
    const eliminadas = await page.evaluate(() => {
      let count = 0;
      const tipos = [
        { cls: 'filaMateriales',  articulo: 'articuloM[]' },
        { cls: 'filaProducidos',  articulo: 'articuloP[]' },
        { cls: 'filaCostos',      articulo: 'costo_produccion[]' }
      ];
      tipos.forEach(({ cls, articulo }) => {
        const filas = document.querySelectorAll('.' + cls);
        if (filas.length === 0) return;
        const ultima = filas[filas.length - 1];
        const inp = ultima.querySelector(`[name="${articulo}"]`);
        const val = inp ? (inp.value || '') : '';
        if (!val || val === 'default') {
          ultima.remove();
          count++;
        }
      });
      return count;
    });
    if (eliminadas > 0) console.log(`🧹 Filas vacías eliminadas: ${eliminadas}`);

    // Screenshot pre-crear
    await page.screenshot({ path: `/exports/op_pre_crear_${Date.now()}.png` });

    // Capturar MAX(id_orden) actual desde la lista visible (una nueva pestaña con la lista)
    async function leerMaxIdOP() {
      const lista = await page.context().newPage()
      try {
        await lista.goto(EFFI_URL, { waitUntil: 'networkidle', timeout: 30000 })
        await lista.waitForTimeout(1500)
        return await lista.evaluate(() => {
          const cuerpo = document.body.innerText || ''
          let max = 0
          // Busca tokens "ID: 1234" en la tabla de OPs
          const re = /ID:\s*(\d+)/g
          let m
          while ((m = re.exec(cuerpo)) !== null) {
            const n = parseInt(m[1], 10)
            if (Number.isFinite(n)) max = Math.max(max, n)
          }
          return max
        })
      } finally {
        await lista.close()
      }
    }
    const maxAntes = await leerMaxIdOP()
    console.log(`🔢 MAX(id_orden) antes de crear: ${maxAntes}`)

    // 12. Crear OP
    console.log('🔄 Creando orden de producción...');
    await page.locator('button:has-text("Crear orden de producción")').click();
    await page.waitForTimeout(5000);

    // Verificar errores
    const erroresValidacion = await page.locator('.modal.in .text-danger, .modal.in .alert-danger, .modal.show .text-danger, .modal.show .alert-danger').count();
    if (erroresValidacion > 0) {
      const textoError = await page.locator('.modal.in .text-danger, .modal.in .alert-danger, .modal.show .text-danger, .modal.show .alert-danger').first().textContent().catch(() => 'Error desconocido');
      await page.screenshot({ path: `/exports/op_error_${Date.now()}.png` });
      console.error(`❌ Error de validación: ${textoError.trim()}`);
      process.exit(1);
    }

    const screenshotPath = `/exports/op_resultado_${Date.now()}.png`;
    await page.screenshot({ path: screenshotPath });

    // Capturar MAX(id_orden) después de crear — el nuevo
    await page.waitForTimeout(2000)
    const maxDespues = await leerMaxIdOP()
    const nuevoId = maxDespues > maxAntes ? maxDespues : null
    if (nuevoId) {
      // Salida machine-readable para el backend que llama
      console.log(`OP_CREADA:${nuevoId}`)
      console.log(`✅ Orden de producción creada — nuevo ID: ${nuevoId} (screenshot: ${screenshotPath})`);
    } else {
      console.log(`⚠️ Creada pero no se pudo determinar el ID nuevo (max antes: ${maxAntes}, max después: ${maxDespues}). Screenshot: ${screenshotPath}`);
    }

  } catch (err) {
    console.error(`❌ ERROR: ${err.message}`);
    await page.screenshot({ path: `/exports/op_error_${Date.now()}.png` }).catch(() => {});
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
