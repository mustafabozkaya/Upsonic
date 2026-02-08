"""Test script for Upsonic Ollama integration."""

import os
import asyncio
from upsonic import Task, Agent

# Set Ollama environment variables
os.environ['OLLAMA_BASE_URL'] = 'http://localhost:11434/v1'
os.environ['OLLAMA_API_KEY'] = 'api-key-not-set'


async def test():
    print('Testing Upsonic Agent with Ollama...')
    try:
        print('Creating agent with model: qwen2.5:7b')
        agent = Agent(model='ollama/qwen2.5:7b')
        print('Agent created successfully')
        
        print('Creating task...')
        task = Task('What is Python?')
        print('Task created successfully')
        
        print('Executing task...')
        result = await agent.print_do_async(task)
        print(f'Result: {result}')
        
    except Exception as e:
        print(f'Error: {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(test())
