import sys, os, time, logging
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from client.netflix_bot import NetflixBot

logging.basicConfig(level=logging.INFO, format="[%(message)s]")

bot = NetflixBot()
print('--- 1. Launching Chrome ---')
bot.launch_chrome_with_cdp()
time.sleep(5)

print('--- 2. Checking Status ---')
status = bot.check_and_handle_login()
print('Returned Status:', status)

print('--- 3. Waiting 10 seconds to observe ---')
time.sleep(10)
print('--- Test Complete ---')
