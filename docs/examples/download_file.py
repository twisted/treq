from twisted.internet.task import react

import treq


async def download_file(reactor, url, destination_filename):
    with open(destination_filename, "wb") as destination:
        response = await treq.get(url, unbuffered=True)
        await treq.collect(response, destination.write)


react(download_file, ["https://httpbin.org/get", "download.txt"])
