define('custom:views/contact/list', ['crm:views/contact/list'], function (Dep) {

    return Dep.extend({

        setup: function () {
            Dep.prototype.setup.call(this);
        },

        afterRender: function () {
            Dep.prototype.afterRender.call(this);

            var self = this;

            var $btn = $(
                '<button class="btn btn-default btn-sm action" style="margin-left:8px;" id="btn-sinc-effi">' +
                '<span class="fas fa-sync-alt"></span> Sincronizar con Effi' +
                '</button>'
            );

            $btn.on('click', function () {
                self.actionSincronizarConEffi();
            });

            // Insertar junto al botón Create (en la cabecera de la lista)
            this.$el.find('.page-header .btn-group').first().append($btn);
            if (!this.$el.find('.page-header .btn-group').length) {
                this.$el.find('.page-header').append($btn);
            }
        },

        actionSincronizarConEffi: function () {
            var self = this;
            var $btn = this.$el.find('#btn-sinc-effi');
            $btn.prop('disabled', true).html('<span class="fas fa-spinner fa-spin"></span> Sincronizando...');

            Espo.Ui.notify('Iniciando sincronización bidireccional con Effi...');

            self.ajaxPostRequest('SyncEffi/action/triggerSync', {})
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
                })
                .finally(function () {
                    $btn.prop('disabled', false).html('<span class="fas fa-sync-alt"></span> Sincronizar con Effi');
                });
        },

    });
});
