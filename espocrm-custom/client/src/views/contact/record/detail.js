define('custom:views/contact/record/detail',
    ['crm:views/contact/record/detail', 'custom:data/ciudades-colombia'],
    function (Dep, CiudadesData) {

    // CSS inyectado una sola vez: ocultar saludo y subcampos de dirección
    if (!document.getElementById('os-contact-hide')) {
        var style = document.createElement('style');
        style.id = 'os-contact-hide';
        style.textContent =
            /* Ocultar dropdown de Título (Sr/Sra/Dr) */
            '[data-name="salutationName"] { display: none !important; }' +
            /* Ocultar ciudad, país, estado, postal de dirección — solo queda calle */
            'input[data-name="addressCity"],' +
            'input[data-name="addressCountry"],' +
            'input[data-name="addressState"],' +
            'input[data-name="addressPostalCode"]' +
            '{ display: none !important; }' +
            /* Ocultar el .row contenedor de país/estado/postal */
            'input[data-name="addressCountry"]' +
            '{ display: none !important; }' +
            '.field[data-name="address"] .row { display: none !important; }';
        document.head.appendChild(style);
    }

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
