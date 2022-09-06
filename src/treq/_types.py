import io
from http.cookiejar import CookieJar
from typing import Any, Iterable, Mapping, Union

from hyperlink import DecodedURL, EncodedURL
from twisted.internet.interfaces import (IReactorPluggableNameResolver,
                                         IReactorTCP, IReactorTime)
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer


class _ITreqReactor(IReactorTCP, IReactorTime, IReactorPluggableNameResolver):
    """
    The kind of reactor treq needs for type-checking purposes.

    This is an approximation of the actual requirement, which comes from the
    `twisted.internet.endpoints.HostnameEndpoint` used by the `Agent`
    implementation:

    > Provider of IReactorTCP, IReactorTime and either
    > IReactorPluggableNameResolver or IReactorPluggableResolver.

    We don't model the `IReactorPluggableResolver` option because it is
    deprecated.
    """


_S = Union[bytes, str]

_URLType = Union[
    str,
    bytes,
    EncodedURL,
    DecodedURL,
]

_ParamsType = Union[
    Mapping[str, Union[str, tuple[str, ...], list[str]]],
    list[tuple[str, str]],
]

_HeadersType = Union[
    Headers,
    dict[_S, _S],
    dict[_S, list[_S]],
]

_CookiesType = Union[
    CookieJar,
    Mapping[str, str],
]

_WholeBody = Union[
    bytes,
    io.BytesIO,
    io.BufferedReader,
    IBodyProducer,
]
"""
Types that define the entire HTTP request body, including those coercible to
`IBodyProducer`.
"""

# Concrete types are used here because the handling of the *data* parameter
# does lots of isinstance checks.
_BodyFields = Union[
    dict[str, str],
    list[tuple[str, str]],
]
"""
Types that will be URL- or multipart-encoded before being sent as part of the
HTTP request body.
"""

_DataType = Union[_WholeBody, _BodyFields]
"""
Values accepted for the *data* parameter

Note that this is a simplification. Only `_BodyFields` may be supplied if the
*files* parameter is passed.
"""

_FileValue = Union[
    str,
    bytes,
    tuple[str, str, IBodyProducer],
]
"""
Either a scalar string, or a file to upload as (filename, content type,
IBodyProducer)
"""

_FilesType = Union[
    Mapping[str, _FileValue],
    Iterable[tuple[str, _FileValue]],
]
"""
Values accepted for the *files* parameter.
"""

# Soon... 🤞 https://github.com/python/mypy/issues/731
_JSONType = Any
