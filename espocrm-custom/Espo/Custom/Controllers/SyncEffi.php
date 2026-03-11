<?php
namespace Espo\Custom\Controllers;

use Espo\Core\Api\Request;
use stdClass;

/**
 * Controller para disparar sincronización bidireccional EspoCRM ↔ Effi.
 * Endpoint: POST /api/v1/SyncEffi/action/triggerSync
 * Llama al webhook server Flask (puerto 5050) — endpoint /trigger-sync.
 */
class SyncEffi extends \Espo\Core\Controllers\Base
{
    public function postActionTriggerSync(Request $request): stdClass
    {
        $url = 'http://172.18.0.1:5050/trigger-sync';

        $context = stream_context_create([
            'http' => [
                'method'        => 'POST',
                'header'        => "Content-Type: application/json\r\n",
                'content'       => '{}',
                'timeout'       => 12,
                'ignore_errors' => true,
            ],
        ]);

        $raw = @file_get_contents($url, false, $context);

        if ($raw === false) {
            return (object) [
                'status'  => 'error',
                'message' => 'No se pudo conectar con el servidor de sincronización. Verifica que el servicio effi-webhook esté activo.',
            ];
        }

        $data = json_decode($raw) ?? (object) [];

        return (object) [
            'status'  => $data->status  ?? 'unknown',
            'message' => $data->message ?? '',
        ];
    }
}
