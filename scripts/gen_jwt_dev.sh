#!/bin/bash
# Genera un JWT para login automático en gestion.oscomunidad.com / ia.oscomunidad.com
# Uso: ./gen_jwt_dev.sh
# Output: el token a stdout — copiar y usar con evaluate_script en Chrome DevTools MCP

node -e "
const crypto = require('crypto');
const SECRET = '30e4cfa02643f4f05b846aab50974c7a5df85b1f05c990b3fe64e297538adbc2';
const b64u = s => Buffer.from(s).toString('base64').replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');
const header = b64u(JSON.stringify({alg:'HS256',typ:'JWT'}));
const now = Math.floor(Date.now()/1000);
const payload = b64u(JSON.stringify({
  tipo:'final',
  email:'larevo1111@gmail.com',
  nombre:'SYSOP',
  foto:'',
  nivel:9,
  tema:'dark',
  perfil:null,
  empresa_activa:'Ori_Sil_2',
  empresa_nombre:'Origen Silvestre',
  empresa_siglas:'OS',
  iat:now,
  exp:now+604800
}));
const sig = crypto.createHmac('sha256',SECRET).update(header+'.'+payload).digest('base64').replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');
console.log(header+'.'+payload+'.'+sig);
"
