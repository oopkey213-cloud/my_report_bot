import requests
from bs4 import BeautifulSoup

TOKEN = "8674194148:AAEEseoUojsIS1bbVNqvyM_3gFXPbTRjVeA"
CHAT_ID = "1674011615"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    # 에러를 일으키던 특수문자 설정(parse_mode)을 제거했습니다.
    params = {"chat_id": CHAT_ID, "text": text}
    r = requests.get(url, params=params)
    print(f"텔레그램 응답: {r.status_code} - {r.text}") # 왜 안 보내졌는지 이유를 출력합니다.
    return r.status_code

def check_reports():
    print("1. 테스트 메시지 전송 시도...")
    send_message("로봇이 정상적으로 작동을 시작했습니다! (연결 테스트)")

    print("2. 사이트 접속 시도 중...")
    url = "http://consensus.hankyung.com/apps.analysis/analysis.list?skinType=industry"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        table_rows = soup.select('tr')
        print(f"3. 데이터 분석 중... (발견된 행 수: {len(table_rows)})")

        if len(table_rows) <= 1:
            print("(!) 리포트 목록을 찾지 못했습니다. 사이트 구조가 바뀌었거나 차단되었습니다.")
            return

        for row in table_rows[1:4]:
            title_element = row.select_one('.text_l')
            if not title_element: continue
            
            title = title_element.text.strip()
            brokerage = row.select_one('.nm').text.strip() if row.select_one('.nm') else "증권사 미상"
            
            link_element = row.select_one('a')
            link = "http://consensus.hankyung.com" + link_element['href'] if link_element else "링크 없음"
            
            # 꾸밈없이 단순한 텍스트로 보냅니다.
            message = f"신규 산업 리포트\n\n제목: {title}\n증권사: {brokerage}\n링크: {link}"
            
            send_message(message)

    except Exception as e:
        print(f"🚨 에러 발생: {e}")

if __name__ == "__main__":
    check_reports()
