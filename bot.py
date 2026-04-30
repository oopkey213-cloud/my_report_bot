import requests
from bs4 import BeautifulSoup
import os

# 입력해주신 정보
TOKEN = "8674194148:AAEEseoUojsIS1bbVNqvyM_3gFXPbTRjVeA"
CHAT_ID = "1674011615"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.get(url, params=params)

def check_reports():
    # 한경 컨센서스 산업분석 페이지
    url = "http://consensus.hankyung.com/apps.analysis/analysis.list?skinType=industry"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 리포트 목록 가져오기
    table = soup.select('tr')
    
    # 최신 리포트 3개만 확인 (너무 많이 오면 스팸 같으니까요!)
    for row in table[1:4]:
        try:
            title = row.select_one('.text_l').text.strip() # 제목
            brokerage = row.select_one('.nm').text.strip() # 증권사
            link_element = row.select_one('a')
            
            if link_element:
                link = "http://consensus.hankyung.com" + link_element['href']
                message = f"📢 *신규 산업 리포트 발견!*\n\n📌 *제목:* {title}\n🏢 *증권사:* {brokerage}\n🔗 [리포트 보기]({link})"
                send_message(message)
        except Exception as e:
            print(f"에러 발생: {e}")

if __name__ == "__main__":
    check_reports()
