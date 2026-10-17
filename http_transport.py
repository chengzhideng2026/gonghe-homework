"""Small shared API transport policy. No redirects and no automatic retries."""
import ipaddress
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener


class TransportError(ValueError):
    pass


def validate_url(url, endpoint=False):
    if not isinstance(url, str) or not url or any(ord(c) <= 32 or ord(c) == 127 for c in url) or '\\' in url:
        raise TransportError('API URL must not contain whitespace, control characters or backslashes')
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise TransportError('Invalid API URL or port') from exc
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname
            or parsed.username is not None or parsed.password is not None or parsed.fragment
            or '%' in parsed.hostname or (endpoint and parsed.query)
            or (port is not None and not 1 <= port <= 65535)):
        raise TransportError('API URL must be HTTP(S), without embedded credentials or fragments; base URLs cannot have a query')
    if parsed.scheme == 'http':
        host = parsed.hostname.lower()
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = host == 'localhost'
        if not loopback:
            raise TransportError('Plain HTTP is allowed only for loopback development; use HTTPS for remote APIs')
    return url.rstrip('/') if endpoint else url


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if fp is not None:
            fp.close()
        raise HTTPError(req.full_url, code, 'API redirects are disabled', {}, None)


def safe_urlopen(request, timeout):
    validate_url(request.full_url)
    # Defaults retain certificate/hostname verification and trusted OS proxy
    # configuration. Neither destinations nor proxies are model arguments.
    return build_opener(_NoRedirect()).open(request, timeout=timeout)


def read_body(response, max_bytes):
    try:
        headers = getattr(response, 'headers', {})
        length = headers.get('Content-Length')
        if length is not None:
            try:
                declared = int(length)
            except (TypeError, ValueError) as exc:
                raise TransportError('Invalid API Content-Length') from exc
            if declared < 0 or declared > max_bytes:
                raise TransportError('API response exceeds the configured byte limit')
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise TransportError('API response exceeds the configured byte limit')
        return raw.decode('utf-8')
    finally:
        response.close()


def redact(message, secrets=(), limit=700):
    text = str(message)
    for secret in sorted({str(s) for s in secrets if s}, key=len, reverse=True):
        text = text.replace(secret, '[REDACTED]')
    return text.replace('\r', ' ').replace('\n', ' ')[:limit]


def http_error_detail(error, secrets=(), limit=700):
    try:
        if 300 <= error.code < 400:
            return 'API redirect refused; configure the final trusted endpoint explicitly'
        # Read only a bounded prefix even when an error server sends a huge body.
        raw = error.read(4096).decode('utf-8', errors='replace')
        return redact(raw, secrets, limit)
    finally:
        error.close()
