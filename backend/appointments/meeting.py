"""
Proveedor de link de videollamada para telepsicología — abstraído y swappable.

La tecnología de video es una variable, no una restricción: el proveedor se elige
por configuración (`MEETING_PROVIDER`), no está cableado al dominio. El default es
Jitsi Meet (sala única e inadivinable, conexión cifrada, sin credenciales), apto
para el MVP; se puede cambiar a un proveedor con certificación clínica vía `.env`
sin tocar el código de turnos.
"""
import secrets
from typing import Protocol

from config import settings


class MeetingLinkProvider(Protocol):
    def generate(self) -> str:
        """Devuelve la URL de una sala de videollamada nueva."""
        ...


class JitsiProvider:
    """Genera una URL de sala Jitsi con un token aleatorio inadivinable.

    La sala se crea sola al primer ingreso; no requiere API ni credenciales.
    """
    def __init__(self, base_url: str) -> None:
        self._base = base_url.rstrip("/")

    def generate(self) -> str:
        room = f"conflur-{secrets.token_urlsafe(12)}"
        return f"{self._base}/{room}"


def _build_provider() -> MeetingLinkProvider:
    provider = settings.MEETING_PROVIDER.lower()
    if provider == "jitsi":
        return JitsiProvider(settings.MEETING_JITSI_BASE)
    raise ValueError(f"MEETING_PROVIDER no soportado: {settings.MEETING_PROVIDER}")


def generate_meeting_link() -> str:
    """Punto de entrada del dominio: link de videollamada nuevo, según el provider configurado."""
    return _build_provider().generate()
