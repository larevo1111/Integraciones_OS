/**
 * QA Setup: genera JWT y crea 25 tareas variadas en OS Gestión
 */
const jwt = require('/home/osserver/Proyectos_Antigravity/Integraciones_OS/sistema_gestion/api/node_modules/jsonwebtoken');

const JWT_SECRET = '30e4cfa02643f4f05b846aab50974c7a5df85b1f05c990b3fe64e297538adbc2';
const BASE_URL = 'http://localhost:9300';

const token = jwt.sign(
  {
    tipo: 'final',
    email: 'larevo1111@gmail.com',
    nombre: 'SYSOP',
    nivel: 9,
    empresa_activa: 'Ori_Sil_2',
    empresa_nombre: 'Origen Silvestre',
    empresa_siglas: 'OS'
  },
  JWT_SECRET,
  { expiresIn: '7d' }
);

console.log('TOKEN:', token);

const headers = {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
};

async function get(path) {
  const res = await fetch(`${BASE_URL}${path}`, { headers });
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}: ${await res.text()}`);
  return res.json();
}

async function post(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body)
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}: ${text}`);
  return JSON.parse(text);
}

async function main() {
  // Obtener datos reales
  console.log('\n=== Obteniendo categorías, etiquetas y proyectos ===');

  const categoriasRes = await get('/api/gestion/categorias');
  const categorias = categoriasRes.categorias || categoriasRes || [];
  console.log('Categorías:', JSON.stringify(categorias.slice(0, 5)));

  const etiquetasRes = await get('/api/gestion/etiquetas');
  const etiquetas = etiquetasRes.etiquetas || etiquetasRes || [];
  console.log('Etiquetas:', JSON.stringify(etiquetas.slice(0, 5)));

  const proyectosRes = await get('/api/gestion/proyectos?estado=Activo');
  const proyectos = proyectosRes.proyectos || proyectosRes || [];
  console.log('Proyectos:', JSON.stringify(proyectos.slice(0, 5)));

  // Helpers
  const catId = (i) => categorias[i % categorias.length]?.id || null;
  const etqId = (i) => etiquetas[i % etiquetas.length]?.id || null;
  const proId = (i) => proyectos[i % proyectos.length]?.id || null;

  const hoy = '2026-03-17';
  const manana = '2026-03-18';
  const semana = ['2026-03-19', '2026-03-20', '2026-03-21'];
  const prioridades = ['Urgente', 'Alta', 'Media', 'Baja'];

  const tareasDef = [
    // 5 tareas hoy, prioridades variadas
    { titulo: 'Revisar propuesta cliente Medellín', fecha_vencimiento: hoy, prioridad: 'Urgente', categoria_id: catId(0) },
    { titulo: 'Enviar cotización proyecto expansión bodega', fecha_vencimiento: hoy, prioridad: 'Alta', categoria_id: catId(1) },
    { titulo: 'Llamar proveedor materiales embalaje', fecha_vencimiento: hoy, prioridad: 'Media', categoria_id: catId(2) },
    { titulo: 'Actualizar inventario almacén principal', fecha_vencimiento: hoy, prioridad: 'Baja', categoria_id: catId(0) },
    { titulo: 'Confirmar despacho pedido #4521', fecha_vencimiento: hoy, prioridad: 'Alta', categoria_id: catId(1) },

    // 5 tareas mañana
    { titulo: 'Preparar presentación junta directiva', fecha_vencimiento: manana, prioridad: 'Urgente', categoria_id: catId(2) },
    { titulo: 'Revisar contratos pendientes de firma', fecha_vencimiento: manana, prioridad: 'Alta', categoria_id: catId(0) },
    { titulo: 'Coordinar logística envío Cali', fecha_vencimiento: manana, prioridad: 'Media', categoria_id: catId(1) },
    { titulo: 'Seguimiento pago factura 0384', fecha_vencimiento: manana, prioridad: 'Alta', categoria_id: catId(2) },
    { titulo: 'Actualizar base de datos clientes', fecha_vencimiento: manana, prioridad: 'Baja', categoria_id: catId(0) },

    // 3 tareas esta semana
    { titulo: 'Reunión equipo ventas zona norte', fecha_vencimiento: semana[0], prioridad: 'Media', categoria_id: catId(1) },
    { titulo: 'Entrega informe mensual operaciones', fecha_vencimiento: semana[1], prioridad: 'Alta', categoria_id: catId(2) },
    { titulo: 'Auditoría interna bodega Bogotá', fecha_vencimiento: semana[2], prioridad: 'Media', categoria_id: catId(0) },

    // 3 tareas sin fecha
    { titulo: 'Investigar nuevos proveedores internacionales', prioridad: 'Baja', categoria_id: catId(1) },
    { titulo: 'Diseñar plan de capacitación equipo', prioridad: 'Media', categoria_id: catId(2) },
    { titulo: 'Revisar política de devoluciones', prioridad: 'Baja', categoria_id: catId(0) },

    // 3 tareas alta prioridad con proyectos
    { titulo: 'Lanzamiento línea productos ecológicos', fecha_vencimiento: hoy, prioridad: 'Urgente', categoria_id: catId(0), proyecto_id: proId(0) },
    { titulo: 'Negociación contrato anual proveedor principal', fecha_vencimiento: manana, prioridad: 'Alta', categoria_id: catId(1), proyecto_id: proId(1) },
    { titulo: 'Implementar CRM en sucursal Medellín', fecha_vencimiento: semana[0], prioridad: 'Alta', categoria_id: catId(2), proyecto_id: proId(0) },
  ];

  // 3 tareas con etiquetas
  if (etiquetas.length > 0) {
    tareasDef.push(
      { titulo: 'Campaña marketing temporada alta', fecha_vencimiento: hoy, prioridad: 'Alta', categoria_id: catId(0), etiqueta_ids: [etqId(0)] },
      { titulo: 'Análisis competencia mercado local', fecha_vencimiento: manana, prioridad: 'Media', categoria_id: catId(1), etiqueta_ids: [etqId(0), etqId(1 % etiquetas.length)] },
      { titulo: 'Optimizar proceso facturación electrónica', fecha_vencimiento: semana[1], prioridad: 'Media', categoria_id: catId(2), etiqueta_ids: [etqId(Math.min(1, etiquetas.length-1))] }
    );
  } else {
    tareasDef.push(
      { titulo: 'Campaña marketing temporada alta', fecha_vencimiento: hoy, prioridad: 'Alta', categoria_id: catId(0) },
      { titulo: 'Análisis competencia mercado local', fecha_vencimiento: manana, prioridad: 'Media', categoria_id: catId(1) },
      { titulo: 'Optimizar proceso facturación electrónica', fecha_vencimiento: semana[1], prioridad: 'Media', categoria_id: catId(2) }
    );
  }

  // 3 tareas padre para subtareas
  tareasDef.push(
    { titulo: 'Proyecto expansión punto venta Cali', fecha_vencimiento: manana, prioridad: 'Alta', categoria_id: catId(0), proyecto_id: proId(0) },
    { titulo: 'Migración sistema contabilidad', fecha_vencimiento: semana[0], prioridad: 'Urgente', categoria_id: catId(1) },
    { titulo: 'Plan estratégico Q2 2026', fecha_vencimiento: semana[2], prioridad: 'Alta', categoria_id: catId(2), proyecto_id: proId(proId(1) ? 1 : 0) }
  );

  // Crear tareas
  console.log(`\n=== Creando ${tareasDef.length} tareas ===`);
  const creadas = [];
  const padreIds = [];

  for (let i = 0; i < tareasDef.length; i++) {
    const def = tareasDef[i];
    const body = {
      titulo: def.titulo,
      prioridad: def.prioridad || 'Media',
    };
    if (def.fecha_vencimiento) body.fecha_vencimiento = def.fecha_vencimiento;
    if (def.categoria_id) body.categoria_id = def.categoria_id;
    if (def.proyecto_id) body.proyecto_id = def.proyecto_id;
    if (def.etiqueta_ids) body.etiqueta_ids = def.etiqueta_ids;

    try {
      const res = await post('/api/gestion/tareas', body);
      const id = res.tarea?.id || res.id;
      console.log(`  ✓ [${i+1}] ${def.titulo} → id=${id}`);
      creadas.push({ id, titulo: def.titulo });

      // Las últimas 3 son padres para subtareas
      if (i >= tareasDef.length - 3) {
        padreIds.push(id);
      }
    } catch (e) {
      console.log(`  ✗ [${i+1}] ${def.titulo}: ${e.message}`);
    }
  }

  // Crear subtareas
  if (padreIds.length > 0) {
    console.log('\n=== Creando subtareas ===');
    const subtareasDef = [
      ['Buscar local disponible zona norte Cali', 'Negociar arriendo local seleccionado'],
      ['Evaluar proveedores software contabilidad', 'Configurar migración datos históricos'],
      ['Definir objetivos KPI por área', 'Asignar responsables y fechas límite']
    ];

    for (let p = 0; p < padreIds.length; p++) {
      const parentId = padreIds[p];
      if (!parentId) continue;
      const subs = subtareasDef[p] || ['Subtarea 1', 'Subtarea 2'];

      for (const subTitulo of subs) {
        try {
          const res = await post('/api/gestion/tareas', {
            titulo: subTitulo,
            prioridad: 'Media',
            parent_id: parentId
          });
          const id = res.tarea?.id || res.id;
          console.log(`  ✓ Subtarea de ${parentId}: "${subTitulo}" → id=${id}`);
        } catch (e) {
          console.log(`  ✗ Subtarea de ${parentId}: "${subTitulo}": ${e.message}`);
        }
      }
    }
  }

  console.log(`\n=== TOTAL creadas: ${creadas.length} tareas ===`);
  console.log('TOKEN_FINAL:', token);

  // Guardar token para el script de playwright
  const fs = require('fs');
  fs.writeFileSync('/tmp/qa_token.txt', token);
  fs.writeFileSync('/tmp/qa_padre_ids.json', JSON.stringify(padreIds));
  console.log('Token guardado en /tmp/qa_token.txt');
  console.log('PadreIds guardados en /tmp/qa_padre_ids.json');
}

main().catch(e => {
  console.error('ERROR FATAL:', e);
  process.exit(1);
});
