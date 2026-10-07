import sys, os, time, asyncio
sys.path.insert(0, '.')
from client.netflix_bot import NetflixBot
from common.protocol import NetflixStatus
from server.mail_otp_extractor import NateMailOTPExtractor

def main():
    try:
        # 기존 크롬 죽이기 (깔끔한 시작)
        os.system('taskkill /F /IM chrome.exe >nul 2>&1')
        time.sleep(1)
        
        # 테스트를 위해 임시로 하드코딩된 자격 증명 주입
        bot = NetflixBot(email='eunpa23@naver.com', password='@Oep0325')
        bot.launch_chrome_with_cdp()
        time.sleep(5) 
        
        status = bot.check_and_handle_login()
        time.sleep(5)
        status = bot.check_and_handle_login()
        
        if status == NetflixStatus.OTP_WAITING:
            extractor = NateMailOTPExtractor()
            code = asyncio.run(extractor.poll_netflix_otp(timeout_sec=30))
            if code:
                bot.input_otp_code(code)
                time.sleep(3)
                print("SUCCESS")
                return 0
            else:
                print("FAIL_NO_OTP")
                return 1
        elif status == NetflixStatus.LOGGED_IN:
            print("SUCCESS")
            return 0
        else:
            print("FAIL_LOCKED")
            return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    finally:
        os.system('taskkill /F /IM chrome.exe >nul 2>&1')

if __name__ == '__main__':
    sys.exit(main())
