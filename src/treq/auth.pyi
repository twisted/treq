# src for treq.auth (Python 3)
from typing import Optional, Tuple

from twisted.internet.defer import Deferred
from twisted.web.http_headers import Headers
from twisted.web.iweb import IAgent, IBodyProducer, IResponse

class UnknownAuthConfig(Exception):
    def __init__(self, config: object) -> None: ...

class _RequestHeaderSettingAgent:
    def __init__(self, agent: IAgent, request_headers: Headers) -> None: ...
    def request(
        self,
        method: bytes,
        uri: bytes,
        headers: Optional[Headers] = ...,
        bodyProducer: Optional[IBodyProducer] = ...,
    ) -> Deferred[IResponse]: ...

def add_basic_auth(
    agent: IAgent, username: str, password: str
) -> _RequestHeaderSettingAgent: ...
def add_auth(
    agent: IAgent, auth_config: Tuple[str, str]
) -> _RequestHeaderSettingAgent: ...
