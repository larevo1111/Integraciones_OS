define('custom:handlers/sync-effi', [], function () {

    var Handler = function (view) {
        this.view = view;
    };

    Handler.prototype.actionSincronizarConEffi = function () {
        Espo.Ui.notify('Iniciando sincronización bidireccional con Effi...');

        Espo.Ajax.postRequest('SyncEffi/action/triggerSync', {})
            .then(function (response) {
                var msg = response.message || 'Sincronización iniciada.';
                if (response.status === 'started' || response.status === 'ok') {
                    Espo.Ui.success(msg);
                } else if (response.status === 'busy') {
                    Espo.Ui.warning(msg);
                } else {
                    Espo.Ui.error(msg);
                }
            })
            .catch(function () {
                Espo.Ui.error('Error al conectar con el servidor de sincronización.');
            });
    };

    return Handler;
});
