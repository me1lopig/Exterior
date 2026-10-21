"""Errores controlados del nucleo cientifico."""


class ErrorCalculoGeotecnico(ValueError):
    """Error de entrada o de dominio que debe mostrarse al usuario."""


class FueraDeDominio(ErrorCalculoGeotecnico):
    """La correlacion no permite evaluar el dato solicitado."""

