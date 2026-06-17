"""Utilidades de red: distinguir peticiones locales de las que llegan por la LAN
o a través del proxy de acceso remoto (Cloudflare Tunnel)."""

from starlette.requests import Request

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}
_PROXY_HEADERS = ("cf-connecting-ip", "x-forwarded-for", "x-forwarded-host")


def is_local_request(request: Request) -> bool:
    """True solo si la petición viene directamente de la máquina local (la app
    Electron o un navegador en el propio PC), NO de la LAN ni del túnel remoto.

    El túnel (cloudflared) corre en la misma máquina, así que su peer también es
    loopback; por eso, además del peer loopback, exigimos que NO traiga cabeceras
    de proxy. Reserva endpoints de setup (p. ej. crear el tenant) al equipo local
    aunque el backend esté expuesto a internet.
    """
    peer = request.client.host if request.client else ""
    if peer not in _LOOPBACK:
        return False
    return not any(request.headers.get(h) for h in _PROXY_HEADERS)
