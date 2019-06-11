# This file does not exist at runtime. It is here to `typedef` a couple of commonly
# used types.
#
# DO NOT IMPORT THIS IN A PY FILE!
from http.cookiejar import CookieJar
from typing import IO, Any, Awaitable, Dict, List, Mapping, Sequence, Tuple, Union

from twisted.internet.defer import Deferred as Deferred
from twisted.web.iweb import IBodyProducer

_EitherStr = Union[str, bytes]
_JSON = Union[None, bool, str, int, float, Dict[str, Any], List[Any]]
_ParamType = Union[Sequence[Tuple[Any, Any]], Mapping[Any, Any]]
_DataType = Union[str, IO[str], IBodyProducer]
_CookiesType = Union[Dict[str, Any], CookieJar]
