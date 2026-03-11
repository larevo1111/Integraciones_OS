define('custom:views/contact/record/edit',
    ['crm:views/contact/record/detail', 'custom:data/ciudades-colombia'],
    function (Dep, CiudadesData) {

    return Dep.extend({

        setup: function () {
            Dep.prototype.setup.call(this);

            this.listenTo(this.model, 'change:departamento', function () {
                this._filtrarMunicipios();
            }, this);
        },

        afterRender: function () {
            Dep.prototype.afterRender.call(this);
            try {
                this._filtrarMunicipios();
            } catch (e) {
                // No romper la vista si el cascading falla
            }
        },

        _filtrarMunicipios: function () {
            if (!this.getFieldView('ciudadNombre')) return;

            var depto    = this.model.get('departamento');
            var opciones = [''];

            if (depto && CiudadesData[depto]) {
                opciones = opciones.concat(CiudadesData[depto]);
            } else {
                Object.keys(CiudadesData).sort().forEach(function (d) {
                    opciones = opciones.concat(CiudadesData[d]);
                });
            }

            this.setFieldOptionList('ciudadNombre', opciones);
        },

    });
});
