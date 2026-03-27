/**
 * wa_bridge — WhatsApp HTTP Bridge para OS
 * Servicio transversal: cualquier módulo OS puede enviar/recibir WhatsApp via REST.
 * Puerto: 3100 | BD: os_whatsapp (MariaDB local)
 *
 * Mensajes entrantes → guardados en wa_mensajes_entrantes + wa_contactos
 * Mensajes enviados  → guardados en wa_mensajes_salientes
 * Mensajes entrantes → reenviados al webhook configurado (WA_WEBHOOK_URL)
 */

const {
  default: makeWASocket,
  DisconnectReason,
  useMultiFileAuthState,
  downloadMediaMessage,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
} = require('@whiskeysockets/baileys');

const express  = require('express');
const axios    = require('axios');
const mysql    = require('mysql2/promise');
const fs       = require('fs');
const path     = require('path');
const pino     = require('pino');
const qrTerminal = require('qrcode-terminal');

// ── Configuración ──────────────────────────────────────────────────────────────
const CONFIG = {
  port:           3100,
  authDir:        path.join(__dirname, 'auth'),
  empresa:        process.env.WA_EMPRESA || 'ori_sil_2',
  allowedNumbers: null,  // null = todos; o ['573001234567@s.whatsapp.net']
  reconnectDelay: 3,
  db: {
    host:     'localhost',
    user:     'osadmin',
    password: 'Epist2487.',
    database: 'os_whatsapp',
    charset:  'utf8mb4',
  },
  // Cargados desde wa_config en BD al iniciar
  mediaDir:     `/home/osserver/wa_media/${process.env.WA_EMPRESA || 'ori_sil_2'}`,
  webhookUrl:   null,
};

// ── Logger ─────────────────────────────────────────────────────────────────────
const logger = pino({ level: 'info' }, pino.destination('./wa_bridge.log'));
const log    = (msg, data = {}) => {
  logger.info(data, msg);
  console.log(`[wa_bridge] ${msg}`, Object.keys(data).length ? data : '');
};
const logErr = (msg, err) => {
  logger.error({ err }, msg);
  console.error(`[wa_bridge] ERROR ${msg}`, err?.message || err);
};

// ── Pool de BD ─────────────────────────────────────────────────────────────────
const pool = mysql.createPool({ ...CONFIG.db, waitForConnections: true, connectionLimit: 5 });

async function dbRun(sql, params = []) {
  const [result] = await pool.execute(sql, params);
  return result;
}

// ── Cargar configuración desde wa_config ───────────────────────────────────────
async function cargarConfig() {
  try {
    const [rows] = await pool.execute(
      'SELECT media_dir, webhook_url, numero_vinculado FROM wa_config WHERE empresa = ? AND activo = 1',
      [CONFIG.empresa]
    );
    if (rows.length) {
      CONFIG.mediaDir   = rows[0].media_dir;
      CONFIG.webhookUrl = rows[0].webhook_url || null;
      log('Config cargada desde BD', { empresa: CONFIG.empresa, mediaDir: CONFIG.mediaDir });
    } else {
      log('Sin config en BD — usando defaults', { empresa: CONFIG.empresa, mediaDir: CONFIG.mediaDir });
    }
    // Asegurar que el directorio de media existe
    if (!fs.existsSync(CONFIG.mediaDir)) fs.mkdirSync(CONFIG.mediaDir, { recursive: true });
  } catch (e) {
    logErr('Error cargando config desde BD', e);
  }
}

// ── Estado global ──────────────────────────────────────────────────────────────
let sock            = null;
let connectionState = 'disconnected';
let qrCode          = null;

// ── Helpers ────────────────────────────────────────────────────────────────────
function formatJid(number) {
  const clean = number.toString().replace(/[^0-9]/g, '');
  return `${clean}@s.whatsapp.net`;
}

function jidToNumber(jid) {
  return jid ? jid.replace('@s.whatsapp.net', '').replace('@g.us', '') : null;
}

function mediaFilename(ext) {
  return path.join(CONFIG.mediaDir, `${Date.now()}.${ext}`);
}

async function downloadAndSave(message, ext) {
  const buffer   = await downloadMediaMessage(message, 'buffer', {});
  const filePath = mediaFilename(ext);
  fs.writeFileSync(filePath, buffer);
  return filePath;
}

function getMediaSource(body) {
  if (body.filePath) return { filePath: body.filePath };
  if (body.base64) {
    const ext      = body.ext || 'bin';
    const filePath = mediaFilename(ext);
    fs.writeFileSync(filePath, Buffer.from(body.base64, 'base64'));
    return { filePath };
  }
  return null;
}

// ── BD: upsert contacto ────────────────────────────────────────────────────────
async function upsertContacto(jid, nombre, esGrupo = false, tipo = 'entrante') {
  const numero = jidToNumber(jid);
  const colCount = tipo === 'entrante' ? 'total_entrantes = total_entrantes + 1' : 'total_salientes = total_salientes + 1';
  try {
    await dbRun(
      `INSERT INTO wa_contactos (empresa, jid, numero, nombre_push, es_grupo)
       VALUES (?, ?, ?, ?, ?)
       ON DUPLICATE KEY UPDATE
         nombre_push     = COALESCE(VALUES(nombre_push), nombre_push),
         ultimo_contacto = CURRENT_TIMESTAMP,
         ${colCount}`,
      [CONFIG.empresa, jid, numero, nombre || null, esGrupo ? 1 : 0]
    );
  } catch (e) {
    logErr('upsertContacto', e);
  }
}

// ── BD: guardar mensaje entrante ───────────────────────────────────────────────
async function guardarEntrante(data) {
  try {
    await dbRun(
      `INSERT IGNORE INTO wa_mensajes_entrantes
         (empresa, message_id, from_jid, from_number, from_name,
          es_grupo, group_jid, group_name, sender_jid,
          tipo, texto, caption,
          media_path, media_mime, media_size_bytes, media_duracion_seg, media_filename, media_sha256,
          latitude, longitude, location_name, location_address,
          contact_nombre, contact_vcard,
          reaction_emoji, reaction_target_id,
          quoted_message_id, quoted_texto, quoted_from,
          es_reenviado, veces_reenviado, ts_wa)
       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
      [
        CONFIG.empresa,
        data.messageId,
        data.fromJid,
        data.fromNumber,
        data.fromName       || null,
        data.esGrupo        ? 1 : 0,
        data.groupJid       || null,
        data.groupName      || null,
        data.senderJid      || null,
        data.tipo,
        data.texto          || null,
        data.caption        || null,
        data.mediaPath      || null,
        data.mediaMime      || null,
        data.mediaSizeBytes || null,
        data.mediaDuracion  || null,
        data.mediaFilename  || null,
        data.mediaSha256    || null,
        data.latitude       || null,
        data.longitude      || null,
        data.locationName   || null,
        data.locationAddress|| null,
        data.contactNombre  || null,
        data.contactVcard   || null,
        data.reactionEmoji  || null,
        data.reactionTarget || null,
        data.quotedId       || null,
        data.quotedTexto    || null,
        data.quotedFrom     || null,
        data.esReenviado    ? 1 : 0,
        data.vecesReenviado || 0,
        data.tsWa           || null,
      ]
    );
  } catch (e) {
    logErr('guardarEntrante', e);
  }
}

// ── BD: guardar mensaje saliente ───────────────────────────────────────────────
async function guardarSaliente(data) {
  try {
    const [result] = await pool.execute(
      `INSERT INTO wa_mensajes_salientes
         (empresa, message_id_wa, to_jid, to_number,
          tipo, texto, caption, media_path, media_filename, media_mime, ptt,
          caller_service, caller_user, status)
       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
      [
        CONFIG.empresa,
        data.messageIdWa  || null,
        data.toJid,
        data.toNumber,
        data.tipo,
        data.texto        || null,
        data.caption      || null,
        data.mediaPath    || null,
        data.mediaFilename|| null,
        data.mediaMime    || null,
        data.ptt          ? 1 : 0,
        data.callerService|| null,
        data.callerUser   || null,
        'sent',
      ]
    );
    return result.insertId;
  } catch (e) {
    logErr('guardarSaliente', e);
    return null;
  }
}

// ── Webhook a servicio externo (si está configurado en wa_config) ──────────────
async function forwardWebhook(payload) {
  if (!CONFIG.webhookUrl) return;
  try {
    await axios.post(CONFIG.webhookUrl, payload, { timeout: 10000 });
    log('Webhook enviado', { tipo: payload.tipo, from: payload.fromNumber });
  } catch (err) {
    logErr('Falló webhook', err);
  }
}

// ── Conexión Baileys ───────────────────────────────────────────────────────────
async function connectToWhatsApp() {
  connectionState = 'connecting';
  qrCode = null;

  const { state, saveCreds } = await useMultiFileAuthState(CONFIG.authDir);
  const { version }          = await fetchLatestBaileysVersion();
  log('Iniciando Baileys', { version });

  sock = makeWASocket({
    version,
    auth: {
      creds: state.creds,
      keys:  makeCacheableSignalKeyStore(state.keys, logger),
    },
    printQRInTerminal:          false,
    logger:                     logger.child({ level: 'silent' }),
    generateHighQualityLinkPreview: false,
    getMessage:                 async () => undefined,
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      qrCode = qr;
      log('QR listo — escanear con WhatsApp');
      qrTerminal.generate(qr, { small: true });
    }

    if (connection === 'open') {
      connectionState = 'open';
      qrCode = null;
      log('✅ WhatsApp conectado');
    }

    if (connection === 'close') {
      connectionState = 'disconnected';
      const code      = lastDisconnect?.error?.output?.statusCode;
      const loggedOut = code === DisconnectReason.loggedOut;
      logErr('Conexión cerrada', { code, loggedOut });
      if (!loggedOut) {
        log(`Reconectando en ${CONFIG.reconnectDelay}s...`);
        setTimeout(connectToWhatsApp, CONFIG.reconnectDelay * 1000);
      } else {
        log('Logout detectado. Eliminar ./auth y reiniciar para re-vincular.');
      }
    }
  });

  // ── Mensajes entrantes ──────────────────────────────────────────────────────
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;

    for (const msg of messages) {
      if (msg.key.fromMe) continue;
      if (!msg.message)   continue;

      const fromJid  = msg.key.remoteJid;
      const esGrupo  = fromJid.endsWith('@g.us');
      const senderJid= esGrupo ? msg.key.participant : null;
      const fromNumber = jidToNumber(esGrupo ? senderJid : fromJid);
      const fromName = msg.pushName || msg.verifiedBizName || null;

      if (CONFIG.allowedNumbers && !CONFIG.allowedNumbers.includes(fromJid)) continue;

      const msgType     = Object.keys(msg.message)[0];
      const ctx         = msg.message[msgType]?.contextInfo || msg.message.extendedTextMessage?.contextInfo || null;

      // Contexto: cita y reenvío
      const quotedId    = ctx?.stanzaId    || null;
      const quotedFrom  = ctx?.participant || null;
      const quotedTexto = ctx?.quotedMessage
        ? (ctx.quotedMessage.conversation || ctx.quotedMessage.extendedTextMessage?.text || null)
        : null;
      const esReenviado    = ctx?.isForwarded     ? 1 : 0;
      const vecesReenviado = ctx?.forwardingScore || 0;

      const data = {
        messageId: msg.key.id,
        fromJid,
        fromNumber,
        fromName,
        esGrupo,
        groupJid:   esGrupo ? fromJid    : null,
        groupName:  null,  // Baileys no da el nombre fácil — se puede enriquecer después
        senderJid,
        tipo:       'text',
        texto:      null,
        caption:    null,
        mediaPath:  null,
        mediaMime:  null,
        mediaSizeBytes: null,
        mediaDuracion:  null,
        mediaFilename:  null,
        mediaSha256:    null,
        latitude:   null,
        longitude:  null,
        locationName:    null,
        locationAddress: null,
        contactNombre:   null,
        contactVcard:    null,
        reactionEmoji:   null,
        reactionTarget:  null,
        quotedId,
        quotedTexto,
        quotedFrom,
        esReenviado,
        vecesReenviado,
        tsWa: typeof msg.messageTimestamp === 'object'
          ? msg.messageTimestamp.low
          : msg.messageTimestamp,
      };

      try {
        if (msgType === 'conversation' || msgType === 'extendedTextMessage') {
          data.tipo  = 'text';
          data.texto = msg.message.conversation || msg.message.extendedTextMessage?.text;

        } else if (msgType === 'imageMessage') {
          const m       = msg.message.imageMessage;
          data.tipo     = 'image';
          data.mediaPath= await downloadAndSave(msg, 'jpg');
          data.caption  = m?.caption    || null;
          data.mediaMime= m?.mimetype   || 'image/jpeg';
          data.mediaSizeBytes = m?.fileLength || null;
          data.mediaSha256    = m?.fileSha256 ? Buffer.from(m.fileSha256).toString('hex') : null;

        } else if (msgType === 'audioMessage') {
          const m       = msg.message.audioMessage;
          data.tipo     = m?.ptt ? 'voice' : 'audio';
          data.mediaPath= await downloadAndSave(msg, 'ogg');
          data.mediaMime= m?.mimetype || 'audio/ogg';
          data.mediaDuracion  = m?.seconds    || null;
          data.mediaSizeBytes = m?.fileLength || null;

        } else if (msgType === 'videoMessage') {
          const m       = msg.message.videoMessage;
          data.tipo     = 'video';
          data.mediaPath= await downloadAndSave(msg, 'mp4');
          data.caption  = m?.caption    || null;
          data.mediaMime= m?.mimetype   || 'video/mp4';
          data.mediaDuracion  = m?.seconds    || null;
          data.mediaSizeBytes = m?.fileLength || null;

        } else if (msgType === 'documentMessage') {
          const m       = msg.message.documentMessage;
          const ext     = m?.fileName?.split('.').pop() || 'bin';
          data.tipo     = 'document';
          data.mediaPath    = await downloadAndSave(msg, ext);
          data.mediaFilename= m?.fileName  || null;
          data.mediaMime    = m?.mimetype  || 'application/octet-stream';
          data.mediaSizeBytes = m?.fileLength || null;

        } else if (msgType === 'stickerMessage') {
          const m       = msg.message.stickerMessage;
          data.tipo     = 'sticker';
          data.mediaPath= await downloadAndSave(msg, 'webp');
          data.mediaMime= m?.mimetype || 'image/webp';

        } else if (msgType === 'locationMessage') {
          const m       = msg.message.locationMessage;
          data.tipo     = 'location';
          data.latitude = m?.degreesLatitude  || null;
          data.longitude= m?.degreesLongitude || null;
          data.locationName    = m?.name    || null;
          data.locationAddress = m?.address || null;

        } else if (msgType === 'contactMessage') {
          const m       = msg.message.contactMessage;
          data.tipo     = 'contact';
          data.contactNombre = m?.displayName || null;
          data.contactVcard  = m?.vcard       || null;

        } else if (msgType === 'reactionMessage') {
          const m       = msg.message.reactionMessage;
          data.tipo     = 'reaction';
          data.reactionEmoji  = m?.text       || null;
          data.reactionTarget = m?.key?.id    || null;

        } else {
          data.tipo = msgType;
          log('Tipo de mensaje no manejado', { msgType });
        }

        // Guardar en BD
        await guardarEntrante(data);
        await upsertContacto(esGrupo ? senderJid : fromJid, fromName, false, 'entrante');
        if (esGrupo) await upsertContacto(fromJid, null, true, 'entrante');

        log('Mensaje entrante guardado', { tipo: data.tipo, from: fromNumber });

        // Reenviar al webhook si está configurado
        await forwardWebhook(data);

      } catch (err) {
        logErr('Error procesando mensaje entrante', err);
      }
    }
  });
}

// ── API Express ────────────────────────────────────────────────────────────────
const app = express();
app.use(express.json({ limit: '50mb' }));

function requireConnected(res) {
  if (connectionState !== 'open') {
    res.status(503).json({ ok: false, error: 'WhatsApp no conectado', state: connectionState });
    return false;
  }
  return true;
}

// GET /api/status
app.get('/api/status', (req, res) => {
  res.json({ ok: true, state: connectionState, qr: qrCode });
});

// POST /api/send/text  { to, message, caller_service?, caller_user? }
app.post('/api/send/text', async (req, res) => {
  if (!requireConnected(res)) return;
  const { to, message, caller_service, caller_user } = req.body;
  if (!to || !message) return res.status(400).json({ ok: false, error: 'to y message requeridos' });
  try {
    const jid    = formatJid(to);
    const result = await sock.sendMessage(jid, { text: message });
    await guardarSaliente({
      messageIdWa: result?.key?.id,
      toJid: jid, toNumber: jidToNumber(jid),
      tipo: 'text', texto: message,
      callerService: caller_service, callerUser: caller_user,
    });
    await upsertContacto(jid, null, false, 'saliente');
    res.json({ ok: true, to: jid, message_id: result?.key?.id });
  } catch (err) {
    logErr('send/text', err);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// POST /api/send/image  { to, filePath|base64, caption?, caller_service?, caller_user? }
app.post('/api/send/image', async (req, res) => {
  if (!requireConnected(res)) return;
  const { to, caption, caller_service, caller_user } = req.body;
  const src = getMediaSource(req.body);
  if (!to || !src) return res.status(400).json({ ok: false, error: 'to y filePath/base64 requeridos' });
  try {
    const jid    = formatJid(to);
    const result = await sock.sendMessage(jid, { image: { url: src.filePath }, caption: caption || '' });
    await guardarSaliente({
      messageIdWa: result?.key?.id,
      toJid: jid, toNumber: jidToNumber(jid),
      tipo: 'image', caption, mediaPath: src.filePath, mediaMime: 'image/jpeg',
      callerService: caller_service, callerUser: caller_user,
    });
    await upsertContacto(jid, null, false, 'saliente');
    res.json({ ok: true, to: jid, message_id: result?.key?.id });
  } catch (err) {
    logErr('send/image', err);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// POST /api/send/audio  { to, filePath|base64, ptt?, caller_service?, caller_user? }
app.post('/api/send/audio', async (req, res) => {
  if (!requireConnected(res)) return;
  const { to, ptt = true, caller_service, caller_user } = req.body;
  const src = getMediaSource(req.body);
  if (!to || !src) return res.status(400).json({ ok: false, error: 'to y filePath/base64 requeridos' });
  try {
    const jid    = formatJid(to);
    const result = await sock.sendMessage(jid, {
      audio: { url: src.filePath }, ptt: Boolean(ptt), mimetype: 'audio/ogg; codecs=opus',
    });
    await guardarSaliente({
      messageIdWa: result?.key?.id,
      toJid: jid, toNumber: jidToNumber(jid),
      tipo: ptt ? 'voice' : 'audio', mediaPath: src.filePath,
      mediaMime: 'audio/ogg', ptt: Boolean(ptt),
      callerService: caller_service, callerUser: caller_user,
    });
    await upsertContacto(jid, null, false, 'saliente');
    res.json({ ok: true, to: jid, message_id: result?.key?.id });
  } catch (err) {
    logErr('send/audio', err);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// POST /api/send/document  { to, filePath|base64, fileName?, mimetype?, caller_service?, caller_user? }
app.post('/api/send/document', async (req, res) => {
  if (!requireConnected(res)) return;
  const { to, fileName, mimetype, caller_service, caller_user } = req.body;
  const src = getMediaSource(req.body);
  if (!to || !src) return res.status(400).json({ ok: false, error: 'to y filePath/base64 requeridos' });
  try {
    const jid      = formatJid(to);
    const fname    = fileName || path.basename(src.filePath);
    const mime     = mimetype || 'application/octet-stream';
    const result   = await sock.sendMessage(jid, { document: { url: src.filePath }, fileName: fname, mimetype: mime });
    await guardarSaliente({
      messageIdWa: result?.key?.id,
      toJid: jid, toNumber: jidToNumber(jid),
      tipo: 'document', mediaPath: src.filePath, mediaFilename: fname, mediaMime: mime,
      callerService: caller_service, callerUser: caller_user,
    });
    await upsertContacto(jid, null, false, 'saliente');
    res.json({ ok: true, to: jid, message_id: result?.key?.id });
  } catch (err) {
    logErr('send/document', err);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// POST /api/send/video  { to, filePath|base64, caption?, caller_service?, caller_user? }
app.post('/api/send/video', async (req, res) => {
  if (!requireConnected(res)) return;
  const { to, caption, caller_service, caller_user } = req.body;
  const src = getMediaSource(req.body);
  if (!to || !src) return res.status(400).json({ ok: false, error: 'to y filePath/base64 requeridos' });
  try {
    const jid    = formatJid(to);
    const result = await sock.sendMessage(jid, { video: { url: src.filePath }, caption: caption || '' });
    await guardarSaliente({
      messageIdWa: result?.key?.id,
      toJid: jid, toNumber: jidToNumber(jid),
      tipo: 'video', caption, mediaPath: src.filePath, mediaMime: 'video/mp4',
      callerService: caller_service, callerUser: caller_user,
    });
    await upsertContacto(jid, null, false, 'saliente');
    res.json({ ok: true, to: jid, message_id: result?.key?.id });
  } catch (err) {
    logErr('send/video', err);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// GET /api/mensajes?numero=573001234567&limite=50
app.get('/api/mensajes', async (req, res) => {
  const { numero, limite = 50 } = req.query;
  try {
    const cond = numero ? 'WHERE from_number = ?' : 'WHERE 1=1';
    const params = numero ? [numero, parseInt(limite)] : [parseInt(limite)];
    const rows = await dbRun(
      `SELECT * FROM wa_mensajes_entrantes ${cond} ORDER BY created_at DESC LIMIT ?`,
      params
    );
    res.json({ ok: true, total: rows.length, mensajes: rows });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// GET /api/contactos
app.get('/api/contactos', async (req, res) => {
  try {
    const rows = await dbRun(
      'SELECT * FROM wa_contactos ORDER BY ultimo_contacto DESC LIMIT 200'
    );
    res.json({ ok: true, total: rows.length, contactos: rows });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// ── Arranque ───────────────────────────────────────────────────────────────────
app.listen(CONFIG.port, () => log(`API escuchando en puerto ${CONFIG.port}`));
cargarConfig().then(() => connectToWhatsApp()).catch((err) => logErr('Error en arranque', err));
