class Rock:
	def __await__(self):
		valueSentIn = yield 7
		print('Rock.__await__ resuming with value: {}.'.format(valueSentIn))
		return valueSentIn

async def runRockTask():
	print('Beginning coroutine runRockTask().')
	rock = Rock()
	print('Awaiting rock...')
	value = await rock
	print('Coroutine received value: {} from rock.'.format(value))
	return 23

coroutine = runRockTask()
result = coroutine.send(None)
print('Coroutine paused and returned value: {}.'.format(result))

print('Resuming coroutine and sending in value: 42.')
try:
	coroutine.send(42)
except StopIteration as e:
	result = e.value
print('Coroutine completed and returned value: {}.'.format(result))

# asyncio.run() 사용
import asyncio

class Rock:
	def __await__(self):
		yield
		print('Rock.__await__ resuming.')
		return 42

async def runRockTask():
	print('Beginning coroutine runRockTask().')
	rock = Rock()
	print('Awaiting rock...')
	value = await rock
	print('Coroutine received value: {} from rock.'.format(value))
	return 23

result = asyncio.run(runRockTask())
print('Coroutine completed and returned value: {}.'.format(result))
