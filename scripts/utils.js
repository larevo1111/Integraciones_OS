/**
 * utils.js
 * Utilidades compartidas para los scripts de exportación.
 */

const XLSX = require('xlsx');
const fs   = require('fs');

/**
 * Cuenta las filas de datos (sin cabecera) de un archivo .xlsx (o HTML disfrazado).
 * Devuelve el número de filas, o '?' si el archivo no se puede leer.
 */
function contarFilas(filePath) {
  try {
    if (!fs.existsSync(filePath)) return '?';
    const wb   = XLSX.readFile(filePath);
    const ws   = wb.Sheets[wb.SheetNames[0]];
    const data = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' });
    // Filtra filas completamente vacías y descuenta la cabecera
    const dataRows = data.slice(1).filter(row => row.some(c => c !== ''));
    return dataRows.length;
  } catch {
    return '?';
  }
}

/**
 * Aplica el filtro "Vigente" explícitamente a través de la UI de filtros de Effi.
 * Necesario para que "Reporte de conceptos" use el filtro correcto (el servidor
 * usa el filtro activo de sesión, no el parámetro ?vigente=1 de la URL).
 */
async function aplicarFiltroVigente(page) {
  // Abrir panel de filtros (tab "Filtros de búsqueda")
  await page.click('a:has-text("Filtros de búsqueda"), button:has-text("Filtros de búsqueda")', { timeout: 5000 });
  await page.waitForTimeout(600);

  // Seleccionar "Vigente" en el dropdown Vigencia via jQuery/Select2 (Effi usa jQuery)
  await page.evaluate(() => {
    const selects = Array.from(document.querySelectorAll('select'));
    for (const sel of selects) {
      const vigenteOpt = Array.from(sel.options).find(o => o.text.trim() === 'Vigente');
      if (vigenteOpt) {
        sel.value = vigenteOpt.value;
        // Notificar a Select2 (Effi usa jQuery + Select2)
        if (typeof $ !== 'undefined') $(sel).trigger('change');
        else sel.dispatchEvent(new Event('change', { bubbles: true }));
        break;
      }
    }
  });
  await page.waitForTimeout(300);

  // Aplicar filtros
  await page.click('button:has-text("Aplicar filtros")', { timeout: 5000 });
  await page.waitForLoadState('networkidle', { timeout: 20000 });
}

module.exports = { contarFilas, aplicarFiltroVigente };
