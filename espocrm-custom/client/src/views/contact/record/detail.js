define('custom:views/contact/record/detail',
    ['crm:views/contact/record/detail', 'custom:data/ciudades-colombia'],
    function (Dep, CiudadesData) {

    return Dep.extend({

        setup: function () {
            Dep.prototype.setup.call(this);

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

    });
});
