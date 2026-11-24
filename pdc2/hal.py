"""A small HAL client (application/hal+json): PDC2 knows an entry address and follows links.

This is the HATEOAS side of the services PDC2 reads (docs/pdc2-api-contract.md): the client never builds
an address itself; it takes the `href` of a named link and fills in a templated link (RFC 6570, the
forms `{name}`, `{?a,b}` and `{&a,b}`). A transport fetches a document: over HTTP with a token, or from
the fake services in pdc2/fake.py.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request

HAL = "application/hal+json"


class HalError(Exception):
    """A service could not be reached, refused the request, or answered something unexpected."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


_TEMPLATE = re.compile(r"\{([?&]?)([^}]+)\}")


def expand(template, **params):
    """Fill in a templated link. Parameters that are not given are left out of a query form."""
    def fill(match):
        operator, names = match.group(1), [n.strip() for n in match.group(2).split(",")]
        if not operator:
            value = params.get(names[0])
            if value is None:
                raise HalError("Link template {} needs '{}'.".format(template, names[0]))
            return urllib.parse.quote(str(value), safe="")
        pairs = [(n, params[n]) for n in names if params.get(n) is not None]
        if not pairs:
            return ""
        query = urllib.parse.urlencode([(n, str(v)) for n, v in pairs])
        return ("?" if operator == "?" else "&") + query

    return _TEMPLATE.sub(fill, template)


class Resource(dict):
    """A HAL document: its own fields, plus links and embedded resources."""

    def __init__(self, data, client, url):
        super().__init__(data)
        self._client = client
        self.url = url

    def link(self, rel):
        link = (self.get("_links") or {}).get(rel)
        if not link or "href" not in link:
            raise HalError("{} has no link '{}'.".format(self.url, rel))
        return link

    def has_link(self, rel):
        return rel in (self.get("_links") or {})

    def follow(self, rel, **params):
        link = self.link(rel)
        href = expand(link["href"], **params) if link.get("templated") else link["href"]
        return self._client.get(href)

    def embedded(self, name):
        items = (self.get("_embedded") or {}).get(name) or []
        return [Resource(item, self._client, self.url) for item in items]


class Client:
    def __init__(self, entry, transport):
        self.entry = entry
        self.transport = transport

    def root(self):
        return self.get(self.entry)

    def get(self, href):
        url = urllib.parse.urljoin(self.entry, href)
        status, data = self.transport(url)
        if status != 200:
            message = data.get("fout") if isinstance(data, dict) else None
            raise HalError(message or "{} answered {}.".format(url, status), status)
        return Resource(data, self, url)


class HttpTransport:
    """GET over HTTP with the consumer's token (inside the server network)."""

    def __init__(self, token, timeout=10):
        self.token = token
        self.timeout = timeout

    def __call__(self, url):
        request = urllib.request.Request(url, headers={
            "Accept": HAL + ", application/json", "Authorization": "Bearer {}".format(self.token)})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            try:
                body = json.loads(error.read().decode("utf-8"))
            except ValueError:
                body = {}
            return error.code, body
        except (urllib.error.URLError, OSError, ValueError) as error:
            raise HalError("{} cannot be reached: {}".format(url, error))
