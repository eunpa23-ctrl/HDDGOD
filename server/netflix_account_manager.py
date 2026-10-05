import asyncio
from common.config import NETFLIX_ACCOUNT_POOL
import logging

logger = logging.getLogger(__name__)

class NetflixAccountManager:
    def __init__(self):
        self.accounts = NETFLIX_ACCOUNT_POOL
        # IP or client_id -> list of allocated accounts, or just track 'in_use' dynamically.
        # 넷플릭스는 1계정당 4명 접속 가능.
        # 여기서는 간단히 각 계정별로 현재 할당된 클라이언트 수를 추적.
        self.allocations = {acc['email']: 0 for acc in self.accounts}
        self.client_to_email = {}
        self.lock = asyncio.Lock()
        
    async def get_credential(self, client_id: str):
        async with self.lock:
            # 이미 할당받은 경우 기존 계정 반환
            if client_id in self.client_to_email:
                email = self.client_to_email[client_id]
                for acc in self.accounts:
                    if acc['email'] == email:
                        return acc
                        
            # 남는 계정 찾기 (할당 수 기준 오름차순, 가장 널널한 계정)
            best_email = min(self.allocations, key=self.allocations.get)
            if self.allocations[best_email] >= 4:
                logger.warning("모든 넷플릭스 계정이 포화 상태(4명 이상)입니다! 그래도 가장 널널한 계정 할당.")
                
            self.allocations[best_email] += 1
            self.client_to_email[client_id] = best_email
            
            for acc in self.accounts:
                if acc['email'] == best_email:
                    logger.info(f"[{client_id}] 넷플릭스 계정 할당: {best_email} (현재 접속: {self.allocations[best_email]}/4)")
                    return acc
                    
            return None

    async def release_credential(self, client_id: str):
        async with self.lock:
            if client_id in self.client_to_email:
                email = self.client_to_email[client_id]
                self.allocations[email] = max(0, self.allocations[email] - 1)
                del self.client_to_email[client_id]
                logger.info(f"[{client_id}] 넷플릭스 계정 반환: {email} (현재 접속: {self.allocations[email]}/4)")

account_manager = NetflixAccountManager()
