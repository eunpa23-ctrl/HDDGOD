import asyncio
import websockets
import json

async def check():
    async with websockets.connect('ws://127.0.0.1:8000/ws/dashboard') as ws:
        msg = await ws.recv()
        data = json.loads(msg)
        clients = data.get('clients', {})
        for cid in ['PC-01', 'PC-02', 'PC-04', 'PC-06', 'PC-07', 'PC-08']:
            info = clients.get(cid, {})
            print(f"{cid}: status={info.get('status')} | pica_status={info.get('pica_status')} | ver={info.get('version')}")

if __name__ == '__main__':
    asyncio.run(check())
