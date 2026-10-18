# -*- coding: utf-8 -*-
import asyncio
import base64
import json
import sys
import websockets

async def capture_one_frame(client_id, output_path, timeout=10):
    uri = f"ws://127.0.0.1:8000/ws/remote_view/{client_id}"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as ws:
            print("Connected! Waiting for frame...")
            start_time = asyncio.get_event_loop().time()
            while True:
                if asyncio.get_event_loop().time() - start_time > timeout:
                    print("Timeout waiting for frame!")
                    return False
                msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
                # msg might be raw base64 or json string
                if not msg:
                    continue
                data_bytes = None
                try:
                    # check if json
                    data = json.loads(msg)
                    if isinstance(data, dict) and "frame" in data:
                        raw_b64 = data["frame"]
                    else:
                        raw_b64 = msg
                except Exception:
                    raw_b64 = msg
                
                # strip data:image/jpeg;base64, prefix if present
                if "," in raw_b64:
                    raw_b64 = raw_b64.split(",", 1)[1]
                
                try:
                    data_bytes = base64.b64decode(raw_b64)
                except Exception as e:
                    print(f"Decode error: {e}")
                    continue
                
                if data_bytes and len(data_bytes) > 100:
                    with open(output_path, "wb") as f:
                        f.write(data_bytes)
                    print(f"Successfully captured frame to {output_path} ({len(data_bytes)} bytes)")
                    return True
    except Exception as e:
        print(f"Capture error: {e}")
        return False

if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "PC-02"
    out = sys.argv[2] if len(sys.argv) > 2 else "pc02_test.jpg"
    asyncio.run(capture_one_frame(cid, out))
