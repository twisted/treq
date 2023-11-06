# Copyright (c) The treq Authors.
# See LICENSE for details.
import io
from http.cookiejar import CookieJar
from typing import Any, Dict, Iterable, List, Mapping, Tuple, Union

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
    Mapping[str, Union[str, Tuple[str, ...], List[str]]],
    List[Tuple[str, str]],
]

_HeadersType = Union[
    Headers,
    Dict[_S, _S],
    Dict[_S, List[_S]],
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
    Dict[str, str],
    List[Tuple[str, str]],
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
    Tuple[str, str, IBodyProducer],
]
"""
Either a scalar string, or a file to upload as (filename, content type,
IBodyProducer)
"""

_FilesType = Union[
    Mapping[str, _FileValue],
    Iterable[Tuple[str, _FileValue]],
]
"""
Values accepted for the *files* parameter.
"""

# Soon... 🤞 https://github.com/python/mypy/issues/731
_JSONType = Any
