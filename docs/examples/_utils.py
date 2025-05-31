import treq


async def print_response(response):
    print(response.code, response.phrase)
    print(response.headers)
    print(await treq.text_content(response))
