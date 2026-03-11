define('custom:views/contact/list', ['views/list'], function (Dep) {

    return Dep.extend({

        setup: function () {
            Dep.prototype.setup.call(this);
        },

        afterRender: function () {
            Dep.prototype.afterRender.call(this);

            var self = this;

            var $btn = $(
                '<button class="btn btn-default btn-sm" id="btn-sinc-effi" style="margin-left:8px;">' +
                '<span class="fas fa-sync-alt"></span> Sincronizar con Effi' +
                '</button>'
            );

            $btn.on('click', function () {
                self.actionSincronizarConEffi();
            });

            // En EspoCRM la cabecera de lista tiene .page-header con el botón Create
            var $header = this.$el.find('.page-header');
            if ($header.length) {
                $header.find('.btn-group').first().append($btn);
                if (!$header.find('.btn-group').length) {
                    $header.append($btn);
                }
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
