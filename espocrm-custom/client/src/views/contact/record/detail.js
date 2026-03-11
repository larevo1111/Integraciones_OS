define('custom:views/contact/record/detail',
    ['crm:views/contact/record/detail'],
    function (Dep) {

    return Dep.extend({

        setup: function () {
            Dep.prototype.setup.call(this);

            this.listenTo(this.model, 'change:departamento', function () {
                this._filtrarMunicipios();
            }, this);
        },

        afterRender: function () {
            Dep.prototype.afterRender.call(this);
            this._filtrarMunicipios();
        },

        _filtrarMunicipios: function () {
            var self = this;
            if (!this.getFieldView('ciudadNombre')) return;

            try {
                Espo.loader.require('custom:data/ciudades-colombia', function (mod) {
                    var data = mod && mod.default ? mod.default : mod;
                    if (!data) return;

                    var depto = self.model.get('departamento');
                    var opciones = [''];

                    if (depto && data[depto]) {
                        opciones = opciones.concat(data[depto]);
                    } else {
                        Object.keys(data).sort().forEach(function (d) {
                            opciones = opciones.concat(data[d]);
                        });
                    }

                    self.setFieldOptionList('ciudadNombre', opciones);
                });
            } catch (e) {
                // Cascading falla silenciosamente, vista sigue funcionando
            }
        },

    });
});
