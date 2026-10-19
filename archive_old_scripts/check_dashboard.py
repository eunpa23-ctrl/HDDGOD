import asyncio, websockets, json

async def check():
    uri = 'ws://127.0.0.1:8000/ws/dashboard'
    async with websockets.connect(uri) as ws:
        msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
        data = json.loads(msg)
        clients = data.get('clients', {})
        for cid, info in clients.items():
            nf = info.get('netflix_status')
            ver = info.get('version')
            ip = info.get('ip')
            print(f'[{cid}] IP={ip} netflix={nf} version={ver}')

asyncio.run(check())
