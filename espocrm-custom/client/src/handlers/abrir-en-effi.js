define('custom:handlers/abrir-en-effi', [], function () {

    var Handler = function (view) {
        this.view = view;
    };

    Handler.prototype.actionAbrirEnEffi = function () {
        var numeroId = this.view.model.get('numeroIdentificacion');
        if (!numeroId) {
            Espo.Ui.warning('Este contacto no tiene número de identificación.');
            return;
        }
        var url = 'https://effi.com.co/app/tercero/cliente?numero=' + encodeURIComponent(numeroId);
        window.open(url, '_blank');
    };

    return Handler;
});
