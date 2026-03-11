define('custom:views/fields/address-simple', ['views/fields/address'], function (Dep) {

    return Dep.extend({

        afterRender: function () {
            Dep.prototype.afterRender.call(this);
            // Ocultar país, estado/dist y código postal — solo mostrar calle y ciudad
            var $country = this.$el.find('[name="addressCountry"]');
            var $state   = this.$el.find('[name="addressState"]');
            var $postal  = this.$el.find('[name="addressPostalCode"]');

            // Los tres están en el mismo .row, ocultarlo completo
            var $row = $country.closest('.row');
            if ($row.length) {
                $row.hide();
            } else {
                // fallback si no están en .row
                $country.parent().hide();
                $state.parent().hide();
                $postal.parent().hide();
            }
        },

    });
});
