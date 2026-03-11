<?php
namespace Espo\Custom\Controllers;

use Espo\Core\Api\Request;
use stdClass;

/**
 * Controller para disparar importación de contactos CRM → Effi a demanda.
 * Endpoint: POST /api/v1/ImportEffi/triggerImport
 * Llama al webhook server Flask corriendo en el host (puerto 5050).
 */
class ImportEffi extends \Espo\Core\Controllers\Base
{
    public function postActionTriggerImport(Request $request): stdClass
    {
        $url = 'http://172.18.0.1:5050/trigger';

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
                'message' => 'No se pudo conectar con el servidor de importación. Verifica que el servicio effi-webhook esté activo.',
            ];
        }

        $data = json_decode($raw) ?? (object) [];

        return (object) [
            'status'  => $data->status  ?? 'unknown',
            'message' => $data->message ?? '',
        ];
    }
}
