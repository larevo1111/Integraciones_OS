// Re-export del helper central del repo raíz.
// Los scripts usan `require('./lib/timezone')` desde `scripts/`; este archivo sólo reexporta.
module.exports = require('../../lib/timezone')
