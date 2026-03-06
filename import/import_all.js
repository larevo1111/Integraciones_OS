/**
 * import_all.js
 * Lee todos los exports de Effi (.xlsx / HTML) y los importa a effi_data (MariaDB).
 * Estrategia: TRUNCATE + INSERT (exportación completa cada vez).
 * Detecta automáticamente tipo de archivo (HTML ISO-8859 vs Excel real).
 */

const mysql   = require('mysql2/promise');
const XLSX    = require('xlsx');
const cheerio = require('cheerio');
const iconv   = require('iconv-lite');
const fs      = require('fs');
const path    = require('path');

const EXPORTS_DIR = '/home/osserver/playwright/exports';

const DB = {
  host:     'localhost',
  port:     3306,
  user:     'osadmin',
  password: 'Epist2487.',
  database: 'effi_data',
  charset:  'utf8mb4',
};

// Archivos a ignorar (nombres viejos duplicados)
const SKIP_TABLES = ['compras_detalle', 'compras_encabezados'];

// ─── Utilidades ──────────────────────────────────────────────────────────────

function toSqlName(str) {
  return str
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '') // quitar tildes
    .replace(/[^a-zA-Z0-9_]/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '')
    .substring(0, 64)
    .toLowerCase() || 'col';
}

function isHtmlFile(filePath) {
  const buf = Buffer.alloc(20);
  const fd = fs.openSync(filePath, 'r');
  fs.readSync(fd, buf, 0, 20, 0);
  fs.closeSync(fd);
  const start = buf.toString('utf8').trimStart();
  return start.startsWith('<') || start.startsWith('\uFEFF<');
}

// ─── Parsers ─────────────────────────────────────────────────────────────────

function parseHtml(filePath) {
  const raw     = fs.readFileSync(filePath);
  const content = iconv.decode(raw, 'ISO-8859-1');
  const $       = cheerio.load(content);

  const headers = [];
  $('thead th').each((_, el) => {
    headers.push($(el).text().trim());
  });

  if (headers.length === 0) return null;

  const rows = [];
  $('tbody tr').each((_, tr) => {
    const row = {};
    $(tr).find('td').each((j, td) => {
      const h = headers[j];
      if (h !== undefined) row[h] = $(td).text().trim();
    });
    if (Object.keys(row).length > 0) rows.push(row);
  });

  return { headers, rows };
}

function parseExcel(filePath) {
  const wb   = XLSX.readFile(filePath);
  const ws   = wb.Sheets[wb.SheetNames[0]];
  const data = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' });

  if (data.length === 0) return null;

  const headers = (data[0] || []).map(h => String(h).trim());
  const rows = data.slice(1).map(rowArr => {
    const row = {};
    headers.forEach((h, i) => {
      row[h] = rowArr[i] !== undefined && rowArr[i] !== null ? String(rowArr[i]).trim() : '';
    });
    return row;
  }).filter(row => Object.values(row).some(v => v !== ''));

  return { headers, rows };
}

// ─── Descubrimiento de archivos ───────────────────────────────────────────────

function findLatestFiles(dir) {
  const map = {};

  function scan(d) {
    for (const entry of fs.readdirSync(d, { withFileTypes: true })) {
      const full = path.join(d, entry.name);
      if (entry.isDirectory()) {
        scan(full);
      } else if (entry.name.endsWith('.xlsx')) {
        const tableName = entry.name.replace(/_\d{4}-\d{2}-\d{2}\.xlsx$/, '');
        if (SKIP_TABLES.includes(tableName)) continue;
        if (!map[tableName] || entry.name > map[tableName].name) {
          map[tableName] = { filePath: full, name: entry.name };
        }
      }
    }
  }

  scan(dir);
  return map;
}

// ─── Importación a MariaDB ────────────────────────────────────────────────────

async function importTable(conn, tableName, headers, rows) {
  const sqlTable = toSqlName(tableName);
  const colDefs  = headers.map(h => `\`${toSqlName(h)}\` TEXT`).join(',\n  ');
  const colNames = headers.map(h => `\`${toSqlName(h)}\``).join(', ');

  // Crear tabla si no existe
  await conn.query(`
    CREATE TABLE IF NOT EXISTS \`${sqlTable}\` (
      _pk BIGINT AUTO_INCREMENT PRIMARY KEY,
      ${colDefs}
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
  `);

  // Vaciar tabla
  await conn.query(`TRUNCATE TABLE \`${sqlTable}\``);

  if (rows.length === 0) {
    console.log(`  ⚠️  Sin filas.`);
    return 0;
  }

  // Insertar en lotes de 200
  const BATCH = 200;
  let inserted = 0;

  for (let i = 0; i < rows.length; i += BATCH) {
    const batch      = rows.slice(i, i + BATCH);
    const rowValues  = batch.map(row =>
      '(' + headers.map(h => {
        const v = row[h];
        return (v === null || v === undefined || v === '')
          ? 'NULL'
          : conn.escape(String(v));
      }).join(', ') + ')'
    ).join(', ');

    await conn.query(`INSERT INTO \`${sqlTable}\` (${colNames}) VALUES ${rowValues}`);
    inserted += batch.length;
  }

  return inserted;
}

// ─── Main ─────────────────────────────────────────────────────────────────────

(async () => {
  const conn = await mysql.createConnection(DB);
  console.log('✅ Conectado a MariaDB → effi_data\n');

  const files = findLatestFiles(EXPORTS_DIR);
  const tables = Object.keys(files).sort();

  console.log(`📂 ${tables.length} tablas encontradas\n`);

  let ok = 0, err = 0;

  for (const tableName of tables) {
    const { filePath } = files[tableName];
    process.stdout.write(`⏳ ${tableName} ... `);

    try {
      let parsed;
      if (isHtmlFile(filePath)) {
        parsed = parseHtml(filePath);
      } else {
        parsed = parseExcel(filePath);
      }

      if (!parsed || parsed.headers.length === 0) {
        console.log(`⚠️  Sin headers, omitido.`);
        continue;
      }

      const inserted = await importTable(conn, tableName, parsed.headers, parsed.rows);
      console.log(`✅ ${inserted} filas`);
      ok++;
    } catch (e) {
      console.log(`❌ ${e.message}`);
      err++;
    }
  }

  await conn.end();
  console.log(`\n─────────────────────────────`);
  console.log(`✅ ${ok} tablas importadas  ❌ ${err} errores`);
})();
