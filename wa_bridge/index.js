/**
 * wa_bridge — WhatsApp HTTP Bridge para OS
 * Arquitectura: daemon Node.js mantiene WebSocket con WhatsApp.
 * Python (u otro servicio) llama los endpoints REST para enviar.
 * Mensajes entrantes se reenvían al webhook Python vía POST.
 */

const {
  default: makeWASocket,
  DisconnectReason,
  useMultiFileAuthState,
  downloadMediaMessage,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
} = require('@whiskeysockets/baileys');

const express = require('express');
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const pino = require('pino');

// ── Configuración ──────────────────────────────────────────────────────────────
const CONFIG = {
  port: 3100,
  pythonWebhook: process.env.WA_WEBHOOK_URL || 'http://localhost:5100/webhook/whatsapp',
  authDir: path.join(__dirname, 'auth'),
  mediaDir: path.join(__dirname, 'media'),
  // null = acepta de todos; ['573001234567@s.whatsapp.net'] = filtro
  allowedNumbers: null,
  // Reintento de reconexión en segundos
  reconnectDelay: 3,
};

// ── Logger ─────────────────────────────────────────────────────────────────────
const logger = pino({ level: 'info' }, pino.destination('./wa_bridge.log'));
const log = (msg, data = {}) => {
  logger.info(data, msg);
  console.log(`[wa_bridge] ${msg}`, Object.keys(data).length ? data : '');
};
const logErr = (msg, err) => {
  logger.error({ err }, msg);
  console.error(`[wa_bridge] ERROR ${msg}`, err?.message || err);
};

// ── Estado global ──────────────────────────────────────────────────────────────
let sock = null;
let connectionState = 'disconnected'; // 'disconnected' | 'connecting' | 'open'
let qrCode = null;

// ── Helpers ────────────────────────────────────────────────────────────────────
function formatJid(number) {
  // Acepta "573001234567" o "573001234567@s.whatsapp.net"
  const clean = number.toString().replace(/[^0-9]/g, '');
  return `${clean}@s.whatsapp.net`;
}

function mediaFilename(ext) {
  return path.join(CONFIG.mediaDir, `${Date.now()}.${ext}`);
}

async function downloadAndSave(message, ext) {
  const buffer = await downloadMediaMessage(message, 'buffer', {});
  const filePath = mediaFilename(ext);
  fs.writeFileSync(filePath, buffer);
  return filePath;
}

function getMediaSource(body) {
  if (body.filePath) return { filePath: body.filePath };
  if (body.base64) {
    const ext = body.ext || 'bin';
    const filePath = mediaFilename(ext);
    fs.writeFileSync(filePath, Buffer.from(body.base64, 'base64'));
    return { filePath };
  }
  return null;
}

// ── Webhook a Python ───────────────────────────────────────────────────────────
async function forwardToPython(payload) {
  try {
    await axios.post(CONFIG.pythonWebhook, payload, { timeout: 10000 });
    log('Webhook enviado a Python', { type: payload.type, from: payload.from });
  } catch (err) {
    logErr('Falló webhook a Python', err);
  }
}

// ── Conexión Baileys ───────────────────────────────────────────────────────────
async function connectToWhatsApp() {
  connectionState = 'connecting';
  qrCode = null;

  const { state, saveCreds } = await useMultiFileAuthState(CONFIG.authDir);
  const { version } = await fetchLatestBaileysVersion();
  log('Iniciando Baileys', { version });

  sock = makeWASocket({
    version,
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, logger),
    },
    printQRInTerminal: true,
    logger: logger.child({ level: 'silent' }),
    generateHighQualityLinkPreview: false,
    getMessage: async () => undefined,
  });

  // Guardar credenciales al actualizar
  sock.ev.on('creds.update', saveCreds);

  // Estado de conexión
  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      qrCode = qr;
      log('QR listo — escanear con WhatsApp');
    }

    if (connection === 'open') {
      connectionState = 'open';
      qrCode = null;
      log('✅ WhatsApp conectado');
    }

    if (connection === 'close') {
      connectionState = 'disconnected';
      const code = lastDisconnect?.error?.output?.statusCode;
      const loggedOut = code === DisconnectReason.loggedOut;
      logErr('Conexión cerrada', { code, loggedOut });

      if (!loggedOut) {
        log(`Reconectando en ${CONFIG.reconnectDelay}s...`);
        setTimeout(connectToWhatsApp, CONFIG.reconnectDelay * 1000);
      } else {
        log('Sesión cerrada (logout). Eliminar ./auth y reiniciar para re-vincular.');
      }
    }
  });

  // Mensajes entrantes
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;

    for (const msg of messages) {
      if (msg.key.fromMe) continue; // ignorar mensajes propios
      if (!msg.message) continue;

      const from = msg.key.remoteJid;

      // Filtro de números permitidos
      if (CONFIG.allowedNumbers && !CONFIG.allowedNumbers.includes(from)) continue;

      const msgType = Object.keys(msg.message)[0];
      const payload = {
        from,
        fromMe: false,
        messageId: msg.key.id,
        timestamp: msg.messageTimestamp,
        type: 'text',
        text: null,
        mediaPath: null,
        mimetype: null,
        caption: null,
        latitude: null,
        longitude: null,
      };

      try {
        if (msgType === 'conversation' || msgType === 'extendedTextMessage') {
          payload.type = 'text';
          payload.text = msg.message.conversation || msg.message.extendedTextMessage?.text;

        } else if (msgType === 'imageMessage') {
          payload.type = 'image';
          payload.mediaPath = await downloadAndSave(msg, 'jpg');
          payload.caption = msg.message.imageMessage?.caption || null;
          payload.mimetype = 'image/jpeg';

        } else if (msgType === 'audioMessage') {
          payload.type = 'audio';
          payload.mediaPath = await downloadAndSave(msg, 'ogg');
          payload.mimetype = 'audio/ogg';

        } else if (msgType === 'videoMessage') {
          payload.type = 'video';
          payload.mediaPath = await downloadAndSave(msg, 'mp4');
          payload.caption = msg.message.videoMessage?.caption || null;
          payload.mimetype = 'video/mp4';

        } else if (msgType === 'documentMessage') {
          const doc = msg.message.documentMessage;
          const ext = doc.fileName?.split('.').pop() || 'bin';
          payload.type = 'document';
          payload.mediaPath = await downloadAndSave(msg, ext);
          payload.fileName = doc.fileName || null;
          payload.mimetype = doc.mimetype || 'application/octet-stream';

        } else if (msgType === 'stickerMessage') {
          payload.type = 'sticker';
          payload.mediaPath = await downloadAndSave(msg, 'webp');
          payload.mimetype = 'image/webp';

        } else if (msgType === 'locationMessage') {
          payload.type = 'location';
          payload.latitude = msg.message.locationMessage.degreesLatitude;
          payload.longitude = msg.message.locationMessage.degreesLongitude;

        } else {
          payload.type = msgType;
          log('Tipo de mensaje no manejado', { msgType });
        }

        await forwardToPython(payload);

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

// POST /api/send/text  { to, message }
app.post('/api/send/text', async (req, res) => {
  if (!requireConnected(res)) return;
  const { to, message } = req.body;
  if (!to || !message) return res.status(400).json({ ok: false, error: 'to y message requeridos' });
  try {
    const jid = formatJid(to);
    await sock.sendMessage(jid, { text: message });
    res.json({ ok: true, to: jid });
  } catch (err) {
    logErr('send/text', err);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// POST /api/send/image  { to, filePath|base64, caption? }
app.post('/api/send/image', async (req, res) => {
  if (!requireConnected(res)) return;
  const { to, caption } = req.body;
  const src = getMediaSource(req.body);
  if (!to || !src) return res.status(400).json({ ok: false, error: 'to y filePath/base64 requeridos' });
  try {
    const jid = formatJid(to);
    await sock.sendMessage(jid, {
      image: { url: src.filePath },
      caption: caption || '',
    });
    res.json({ ok: true, to: jid });
  } catch (err) {
    logErr('send/image', err);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// POST /api/send/audio  { to, filePath|base64, ptt? }
app.post('/api/send/audio', async (req, res) => {
  if (!requireConnected(res)) return;
  const { to, ptt = true } = req.body;
  const src = getMediaSource(req.body);
  if (!to || !src) return res.status(400).json({ ok: false, error: 'to y filePath/base64 requeridos' });
  try {
    const jid = formatJid(to);
    await sock.sendMessage(jid, {
      audio: { url: src.filePath },
      ptt: Boolean(ptt),
      mimetype: 'audio/ogg; codecs=opus',
    });
    res.json({ ok: true, to: jid });
  } catch (err) {
    logErr('send/audio', err);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// POST /api/send/document  { to, filePath|base64, fileName?, mimetype? }
app.post('/api/send/document', async (req, res) => {
  if (!requireConnected(res)) return;
  const { to, fileName, mimetype } = req.body;
  const src = getMediaSource(req.body);
  if (!to || !src) return res.status(400).json({ ok: false, error: 'to y filePath/base64 requeridos' });
  try {
    const jid = formatJid(to);
    await sock.sendMessage(jid, {
      document: { url: src.filePath },
      fileName: fileName || path.basename(src.filePath),
      mimetype: mimetype || 'application/octet-stream',
    });
    res.json({ ok: true, to: jid });
  } catch (err) {
    logErr('send/document', err);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// POST /api/send/video  { to, filePath|base64, caption? }
app.post('/api/send/video', async (req, res) => {
  if (!requireConnected(res)) return;
  const { to, caption } = req.body;
  const src = getMediaSource(req.body);
  if (!to || !src) return res.status(400).json({ ok: false, error: 'to y filePath/base64 requeridos' });
  try {
    const jid = formatJid(to);
    await sock.sendMessage(jid, {
      video: { url: src.filePath },
      caption: caption || '',
    });
    res.json({ ok: true, to: jid });
  } catch (err) {
    logErr('send/video', err);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// ── Arranque ───────────────────────────────────────────────────────────────────
app.listen(CONFIG.port, () => {
  log(`API escuchando en puerto ${CONFIG.port}`);
});

connectToWhatsApp().catch((err) => logErr('Error en connectToWhatsApp', err));
