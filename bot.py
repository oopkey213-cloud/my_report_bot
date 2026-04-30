import requests
from bs4 import BeautifulSoup
import os

TOKEN = "8674194148:AAEEseoUojsIS1bbVNqvyM_3gFXPbTRjVeA"
CHAT_ID = "1674011615"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": text}
    requests.get(url, params=params)

def check_reports():
    # 1. 네이버 증권 산업분석 사이트 접속
    url = "https://finance.naver.com/research/industry_list.naver"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    # 2. 리포트 목록 가져오기
    rows = soup.select('table.type_1 tr')
    reports = []
    
    for row in rows:
        if row.select_one('.file') is None: # 빈 줄 건너뛰기
            continue
            
        title_td = row.select('td')[1]
        title = title_td.text.strip()
        link_a = title_td.select_one('a')
        
        if not link_a: continue
        
        link = "https://finance.naver.com/research/" + link_a['href']
        brokerage = row.select('td')[2].text.strip()
        
        reports.append({'title': title, 'brokerage': brokerage, 'link': link})
        if len(reports) >= 5: # 최신 5개까지만 확인
            break
            
    reports.reverse() # 오래된 것부터 보내기 위해 순서 뒤집기

    # 3. 로봇의 수첩(기억력) 읽어오기
    sent_titles = []
    if os.path.exists("last_title.txt"):
        with open("last_title.txt", "r", encoding="utf-8") as f:
            sent_titles = f.read().splitlines()

    # 4. 새로운 리포트만 골라서 텔레그램 전송
    new_sent = sent_titles.copy()
    for report in reports:
        if report['title'] in sent_titles:
            continue # 이미 수첩에 있는 제목이면 패스!
        
        message = f"📢 신규 산업 리포트\n\n제목: {report['title']}\n증권사: {report['brokerage']}\n링크: {report['link']}"
        send_message(message)
        new_sent.append(report['title']) # 수첩에 새 제목 추가

    # 5. 수첩 덮어쓰기 (최근 50개까지만 기억)
    with open("last_title.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(new_sent[-50:]))

if __name__ == "__main__":
    check_reports()
