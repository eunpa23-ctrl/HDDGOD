import sys, os, time, asyncio
sys.path.insert(0, '.')
from client.netflix_bot import NetflixBot
from common.protocol import NetflixStatus
from server.mail_otp_extractor import NateMailOTPExtractor

print('='*50)
print('넷플릭스 2단계 로그인 + OTP 자동 추출 풀 테스트')
print('='*50)
time.sleep(2)

bot = NetflixBot()
print('\n[1/4] 크롬 브라우저를 엽니다...')
bot.launch_chrome_with_cdp()
time.sleep(5) 

print('\n[2/4] 자동 로그인을 시작합니다. 화면을 지켜보세요!')
status = bot.check_and_handle_login()
print(f'첫 번째 로그인 시도 반환 상태: {status}')

print('\n화면 전환을 위해 5초 대기...')
time.sleep(5)

print('\n현재 화면 상태를 다시 점검합니다...')
status = bot.check_and_handle_login()
print(f'현재 상태: {status}')

if status == NetflixStatus.OTP_WAITING:
    print('\n[3/4] OTP 인증 화면 감지됨! 네이버 메일에서 인증번호를 가져옵니다 (최대 30초 대기)...')
    extractor = NateMailOTPExtractor()
    code = asyncio.run(extractor.poll_netflix_otp(timeout_sec=30))
    
    if code:
        print(f'\n[4/4] 인증번호 [{code}] 추출 성공! 넷플릭스에 자동 입력합니다.')
        bot.input_otp_code(code)
    else:
        print('\n[실패] 메일에서 인증번호를 찾지 못했습니다.')
else:
    print('\n[알림] OTP 화면이 아니거나 이미 로그인되었습니다.')

print('\n[테스트 완료] 15초 뒤에 창이 자동으로 닫힙니다...')
time.sleep(15)
