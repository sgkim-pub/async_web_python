import asyncio

async def loudmouthPenguin(magic_number: int):
    print(
     'I am a super special talking penguin. Far cooler than that printer. '
     'By the way, my lucky number is: {}.'.format(magic_number)
    )

    return magic_number

async def penguins():
    p = await loudmouthPenguin(1)
    p2 = await loudmouthPenguin(2)
    p3 = await loudmouthPenguin(3)

    return [p, p2, p3]

result = asyncio.run(penguins())
# result = asyncio.run(loudmouthPenguin(1))

print(result)
