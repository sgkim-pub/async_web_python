import asyncio

async def adelay(delay):
    try:
        delta = 1/delay
        await asyncio.sleep(delta)
        return delay
    except asyncio.CancelledError:
        raise
        # return None
    except Exception as e:
        return delay
