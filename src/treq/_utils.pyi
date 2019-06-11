# src for treq._utils (Python 3)
from typing import Optional

from twisted.internet.interfaces import IReactorTime
from twisted.web.client import HTTPConnectionPool

def default_reactor(reactor: Optional[IReactorTime]): ...
def get_global_pool() -> HTTPConnectionPool: ...
def set_global_pool(pool: HTTPConnectionPool) -> None: ...
def default_pool(
    reactor: Optional[IReactorTime],
    pool: Optional[HTTPConnectionPool],
    persistent: bool,
) -> HTTPConnectionPool: ...
