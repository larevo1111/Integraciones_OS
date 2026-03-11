define('custom:views/contact/record/detail', ['crm:views/contact/record/detail'], function (Dep) {

    return Dep.extend({

        setup: function () {
            Dep.prototype.setup.call(this);

            this.addButton({
                name:  'enviarAEffi',
                label: 'Enviar a Effi',
                style: 'success',
                title: 'Enviar todos los contactos CRM pendientes a Effi',
            });
        },

        actionEnviarAEffi: function () {
            var self = this;

            Espo.Ui.notify(self.translate('Enviando...', 'messages'));

            self.ajaxPostRequest('ImportEffi/action/triggerImport', {})
                .then(function (response) {
                    var msg = response.message || 'Proceso completado.';
                    if (response.status === 'ok' || response.status === 'started') {
                        Espo.Ui.success(msg);
                    } else if (response.status === 'busy') {
                        Espo.Ui.warning(msg);
                    } else {
                        Espo.Ui.error(msg);
                    }
                })
                .catch(function () {
                    Espo.Ui.error('Error al conectar con el servidor de importación.');
                });
        },

    });
});
