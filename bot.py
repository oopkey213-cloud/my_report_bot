import requests
from bs4 import BeautifulSoup

# 정보 설정
TOKEN = "8674194148:AAEEseoUojsIS1bbVNqvyM_3gFXPbTRjVeA"
CHAT_ID = "1674011615"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    r = requests.get(url, params=params)
    return r.status_code

def check_reports():
    print("1. 사이트 접속 시도 중...")
    url = "http://consensus.hankyung.com/apps.analysis/analysis.list?skinType=industry"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 리포트 목록이 있는 테이블 찾기
        table_rows = soup.select('tr')
        print(f"2. 데이터 분석 중... (발견된 행 수: {len(table_rows)})")

        if len(table_rows) <= 1:
            print("(!) 리포트 목록을 찾지 못했습니다. 사이트 구조를 확인해야 합니다.")
            return

        # 최신 3개만 발송
        for row in table_rows[1:4]:
            title_element = row.select_one('.text_l')
            if not title_element: continue
            
            title = title_element.text.strip()
            brokerage = row.select_one('.nm').text.strip() if row.select_one('.nm') else "증권사 미상"
            
            link_element = row.select_one('a')
            link = "http://consensus.hankyung.com" + link_element['href'] if link_element else "링크 없음"
            
            message = f"📢 *신규 산업 리포트*\n\n📌 *제목:* {title}\n🏢 *증권사:* {brokerage}\n🔗 [PDF 보기]({link})"
            
            status = send_message(message)
            if status == 200:
                print(f"✅ 전송 성공: {title}")
            else:
                print(f"❌ 전송 실패 (코드: {status})")

    except Exception as e:
        print(f"🚨 에러 발생: {e}")

if __name__ == "__main__":
    check_reports()
