import sys, os, time, base64, asyncio, websockets, json, logging
sys.path.insert(0, '.')
from client.netflix_bot import NetflixBot

logging.basicConfig(level=logging.INFO)
bot = NetflixBot()
bot.launch_chrome_with_cdp()
time.sleep(5)

status = bot.check_and_handle_login()
time.sleep(5)  # Wait for login to complete and page to load

# Now take screenshot
artifact_dir = r'C:\Users\USER\.gemini\antigravity\brain\36085afd-6c99-45b2-8ff8-4ac77cbb1e5b'
img_path = os.path.join(artifact_dir, 'netflix_login_result.png')

async def capture():
    if bot.connect_cdp():
        async with websockets.connect(bot.ws_url) as ws:
            await ws.send(json.dumps({'id': 1, 'method': 'Page.captureScreenshot'}))
            while True:
                res = json.loads(await ws.recv())
                if res.get('id') == 1:
                    data = res['result']['data']
                    with open(img_path, 'wb') as f:
                        f.write(base64.b64decode(data))
                    print('Screenshot saved!')
                    break

asyncio.run(capture())
