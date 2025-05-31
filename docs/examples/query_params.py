from twisted.internet.task import react

import treq


async def query_params(reactor):
    print("List of tuples")
    resp = await treq.get(
        "https://httpbin.org/get", params=[("foo", "bar"), ("baz", "bax")]
    )
    print(await resp.text())

    print("Single value dictionary")
    resp = await treq.get(
        "https://httpbin.org/get", params={"foo": "bar", "baz": "bax"}
    )
    print(await resp.text())

    print("Multi value dictionary")
    resp = await treq.get(
        "https://httpbin.org/get", params={b"foo": [b"bar", b"baz", b"bax"]}
    )
    print(await resp.text())

    print("Mixed value dictionary")
    resp = await treq.get(
        "https://httpbin.org/get",
        params={"foo": [1, 2, 3], "bax": b"quux", b"bar": "foo"},
    )
    print(await resp.text())

    print("Preserved query parameters")
    resp = await treq.get("https://httpbin.org/get?foo=bar", params={"baz": "bax"})
    print(await resp.text())


react(query_params)
