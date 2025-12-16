import asyncio

async def loudmouthPenguin(magic_number: int):
    print(
     'I am a super special talking penguin. Far cooler than that printer. '
     'By the way, my lucky number is: {}.'.format(magic_number)
    )

    return magic_number

loop = asyncio.get_event_loop()

task = loop.create_task(loudmouthPenguin(1))
task = loop.create_task(loudmouthPenguin(2))
task = loop.create_task(loudmouthPenguin(3))

tasks = asyncio.all_tasks(loop=loop)
print('tasks:', tasks)

group = asyncio.gather(*tasks, return_exceptions=True)
print('group:', group)

result = loop.run_until_complete(group)

loop.close()

print(result)
