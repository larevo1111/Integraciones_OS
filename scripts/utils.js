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

module.exports = { contarFilas };
