from twisted.internet.task import react

import treq


async def main(reactor):
    print("List of tuples")
    resp = await treq.get(
        "https://httpbin.org/get", params=[("foo", "bar"), ("baz", "bax")]
    )
    content = await resp.text()
    print(content)

    print("Single value dictionary")
    resp = await treq.get(
        "https://httpbin.org/get", params={"foo": "bar", "baz": "bax"}
    )
    content = await resp.text()
    print(content)

    print("Multi value dictionary")
    resp = await treq.get(
        "https://httpbin.org/get", params={b"foo": [b"bar", b"baz", b"bax"]}
    )
    content = await resp.text()
    print(content)

    print("Mixed value dictionary")
    resp = await treq.get(
        "https://httpbin.org/get",
        params={"foo": [1, 2, 3], "bax": b"quux", b"bar": "foo"},
    )
    content = await resp.text()
    print(content)

    print("Preserved query parameters")
    resp = await treq.get("https://httpbin.org/get?foo=bar", params={"baz": "bax"})
    content = await resp.text()
    print(content)


react(main)
