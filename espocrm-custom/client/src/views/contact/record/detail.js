define('custom:views/contact/record/detail',
    ['crm:views/contact/record/detail', 'custom:data/ciudades-colombia'],
    function (Dep, CiudadesData) {

    return Dep.extend({

        setup: function () {
            Dep.prototype.setup.call(this);

            // Botón "Enviar a Effi" (pendientes CRM → Effi)
            this.addButton({
                name:  'enviarAEffi',
                label: 'Enviar a Effi',
                style: 'success',
                title: 'Enviar todos los contactos CRM pendientes a Effi',
            });

            // Cascading: cuando cambia departamento → filtrar municipios
            this.listenTo(this.model, 'change:departamento', function () {
                this._filtrarMunicipios();
            }, this);
        },

        afterRender: function () {
            Dep.prototype.afterRender.call(this);
            // Aplicar filtro inicial si ya hay departamento seleccionado
            this._filtrarMunicipios();
        },

        _filtrarMunicipios: function () {
            var fieldView = this.getFieldView('ciudadNombre');
            if (!fieldView) return;

            var depto    = this.model.get('departamento');
            var opciones = [''];

            if (depto && CiudadesData[depto]) {
                opciones = opciones.concat(CiudadesData[depto]);
            } else {
                // Sin departamento: mostrar todos los municipios
                Object.keys(CiudadesData).sort().forEach(function (d) {
                    opciones = opciones.concat(CiudadesData[d]);
                });
            }

            fieldView.params.options = opciones;
            if (fieldView.isRendered()) {
                fieldView.reRender();
            }
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
