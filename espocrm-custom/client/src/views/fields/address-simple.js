define('custom:views/fields/address-simple', ['views/fields/address'], function (Dep) {

    return Dep.extend({

        afterRender: function () {
            Dep.prototype.afterRender.call(this);
            // Template edit-4: street → city → .row(country|state|postal)
            // Ocultar la fila inferior (país, estado/dist, código postal)
            var $row = this.$el.find('[data-name="addressCountry"]').closest('.row');
            if ($row.length) {
                $row.hide();
            }
        },

    });
});
