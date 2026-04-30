import requests
from bs4 import BeautifulSoup
import os
import fitz  # PyMuPDF
from openai import OpenAI
import time

# 1. 기본 설정 (입력하신 정보)
TOKEN = "8674194148:AAEEseoUojsIS1bbVNqvyM_3gFXPbTRjVeA"
CHAT_ID = "1674011615"
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def send_tg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

def get_summary(text, report_type):
    if not api_key: return "API 키 설정 필요"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "주식 애널리스트로서 리포트 핵심을 3줄 요약해줘."},
                {"role": "user", "content": text[:4000]}
            ]
        )
        return response.choices[0].message.content
    except: return "요약 생성 실패"

def process_pdf(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        with open("temp.pdf", "wb") as f: f.write(r.content)
        doc = fitz.open("temp.pdf")
        text = ""
        for i in range(min(len(doc), 2)): text += doc[i].get_text()
        return text
    except: return None

def check_and_run(url, report_type):
    print(f"\n--- {report_type} 리포트 분석 시작 ---")
    
    # [핵심] 더 사람처럼 보이게 하는 헤더 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Referer': 'https://finance.naver.com/'
    }
    
    try:
        response = requests.get(url, headers=headers)
        # [핵심] 네이버 전용 한글 깨짐 방지 설정
        response.encoding = 'euc-kr' 
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 리포트가 담긴 표의 행(tr)들을 모두 가져옴
        rows = soup.select('table.type_1 tr')
        print(f"찾은 데이터 행 수: {len(rows)}개")

        count = 0
        for row in rows:
            # 제목 칸 찾기
            title_td = row.select_one('td.text_l')
            if not title_td or not title_td.select_one('a'): continue
            
            title = title_td.text.strip()
            
            # 2번 기능: 기업 리포트 '상향' 필터 (테스트를 위해 '유지'도 포함)
            if report_type == "기업":
                if not any(k in title for k in ["상향", "↑", "매수", "Buy", "유지"]):
                    continue

            print(f"발견: {title}")
            link = "https://finance.naver.com/research/" + title_td.select_one('a')['href']
            brokerage = row.select('td')[2].text.strip()
            
            pdf_text = process_pdf(link)
            summary = get_summary(pdf_text, report_type) if pdf_text else "내용 요약 불가"
            
            msg = f"📢 *신규 {report_type} 리포트*\n📌 {title}\n🏢 {brokerage}\n\n🤖 *AI 핵심 요약*\n{summary}\n\n🔗 [원문보기]({link})"
            send_tg(msg)
            
            count += 1
            if count >= 2: break # 한 번에 2개씩만 테스트
            time.sleep(2)
            
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    send_tg("🚀 로봇이 네이버 증권에 접속하여 분석을 시작합니다.")
    # 산업 리포트 확인
    check_and_run("https://finance.naver.com/research/industry_list.naver", "산업")
    # 기업 리포트 확인
    check_and_run("https://finance.naver.com/research/company_list.naver", "기업")
    print("모든 작업 종료")
