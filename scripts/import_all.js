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

const EXPORTS_DIR = '/exports';

// Conexión via helper central (lee integracion_conexionesbd.env al importarse)
require('../lib/db_conn');
const DB = {
  host:     process.env.DB_LOCAL_HOST || '127.0.0.1',
  port:     parseInt(process.env.DB_LOCAL_PORT || '3306', 10),
  user:     process.env.DB_LOCAL_USER,
  password: process.env.DB_LOCAL_PASS,
  database: 'effi_data',
  charset:  'utf8mb4',
};

// Archivos a ignorar
const SKIP_TABLES = [];

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
        const mtime = fs.statSync(full).mtimeMs;
        if (!map[tableName] || mtime > map[tableName].mtime) {
          map[tableName] = { filePath: full, name: entry.name, mtime };
        }
      }
    }
  }

  scan(dir);
  return map;
}

// ─── Importación a MariaDB ────────────────────────────────────────────────────

async function importTable(conn, tableName, headers, rows) {
  const sqlTable = 'zeffi_' + toSqlName(tableName);

  // Deduplicar nombres de columna (ej. "Departamento" aparece 2 veces en empleados)
  const seen = {};
  const dedupedHeaders = headers.map(h => {
    const base = toSqlName(h);
    if (!seen[base]) { seen[base] = 0; }
    seen[base]++;
    return seen[base] === 1 ? base : `${base}_${seen[base]}`;
  });

  const colDefs  = dedupedHeaders.map(c => `\`${c}\` TEXT`).join(',\n  ');
  const colNames = dedupedHeaders.map(c => `\`${c}\``).join(', ');

  await conn.query(`DROP TABLE IF EXISTS \`${sqlTable}\``);
  await conn.query(`
    CREATE TABLE \`${sqlTable}\` (
      _pk BIGINT AUTO_INCREMENT PRIMARY KEY,
      ${colDefs}
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
  `);

  if (rows.length === 0) {
    console.log(`  ⚠️  Sin filas.`);
    return 0;
  }

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

      // zeffi_cambios_estado: convertir f_cambio_de_estado de UTC a UTC-5 (Colombia)
      if (tableName.toLowerCase().includes('cambios') && tableName.toLowerCase().includes('estado')) {
        await conn.query(`
          UPDATE zeffi_cambios_estado
          SET f_cambio_de_estado = DATE_SUB(f_cambio_de_estado, INTERVAL 5 HOUR)
          WHERE f_cambio_de_estado IS NOT NULL AND f_cambio_de_estado != ''
        `);
        console.log(`✅ ${inserted} filas (f_cambio_de_estado convertido UTC→COT)`);
      } else {
        console.log(`✅ ${inserted} filas`);
      }
      ok++;
    } catch (e) {
      console.log(`❌ ${e.message}`);
      err++;
    }
  }

  await conn.end();
  console.log(`\n─────────────────────────────`);
  const errMsg = err > 0 ? `  ❌ ${err} errores` : '';
  console.log(`✅ ${ok} tablas importadas${errMsg}`);
})();
