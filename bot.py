import requests
from bs4 import BeautifulSoup
import os
import fitz  # PyMuPDF
from openai import OpenAI
import time

# 1. 정보 설정
TOKEN = "8674194148:AAEEseoUojsIS1bbVNqvyM_3gFXPbTRjVeA"
CHAT_ID = "1674011615"
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def send_tg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=10)
    except:
        pass

def get_summary(text, report_type):
    if not api_key: return "API 키 없음"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "주식 애널리스트로서 리포트 내용을 핵심 3줄로 요약해줘."},
                {"role": "user", "content": text[:4000]}
            ]
        )
        return response.choices[0].message.content
    except: return "요약 생성 중 오류"

def process_pdf(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        with open("temp.pdf", "wb") as f: f.write(r.content)
        doc = fitz.open("temp.pdf")
        text = ""
        for i in range(min(len(doc), 2)): text += doc[i].get_text()
        return text
    except: return None

def check_and_run(url, report_type):
    print(f"\n🔎 {report_type} 리포트 분석 중...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'euc-kr'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 모든 행을 가져옵니다.
        rows = soup.find_all('tr')
        print(f"전체 행 수: {len(rows)}")

        count = 0
        for row in rows:
            # 2. 각 행에서 칸(td)들을 가져옵니다.
            cols = row.find_all('td')
            # 네이버 리포트 표는 보통 칸이 4개 이상입니다.
            if len(cols) < 3: continue 
            
            # 3. 보통 두 번째 칸(index 1)에 제목과 링크가 있습니다.
            a_tag = cols[1].find('a')
            if not a_tag: continue
            
            title = a_tag.get_text().strip()
            link = "https://finance.naver.com/research/" + a_tag['href']
            brokerage = cols[2].get_text().strip() # 세 번째 칸(index 2)이 증권사
            
            # 4. 기업 리포트일 때 '상향' 필터링 (테스트를 위해 잠시 해제하고 '전체' 발송)
            # if report_type == "기업" and not any(k in title for k in ["상향", "↑", "매수"]): continue

            print(f"✨ 발견: {title}")
            
            pdf_text = process_pdf(link)
            summary = get_summary(pdf_text, report_type) if pdf_text else "내용 요약 불가"
            
            # 메시지 전송 (특수문자 에러 방지를 위해 간단히 구성)
            msg = f"📢 *신규 {report_type} 리포트*\n제목: {title}\n증권사: {brokerage}\n\n🤖 *AI 요약*\n{summary}\n\n🔗 [원문보기]({link})"
            send_tg(msg)
            
            count += 1
            if count >= 2: break # 한 분야당 2개씩만 테스트 발송
            time.sleep(2)
            
    except Exception as e:
        print(f"🚨 에러 발생: {e}")

if __name__ == "__main__":
    send_tg("🚀 로봇 가동! 최신 리포트를 수집하여 요약을 시작합니다.")
    check_and_run("https://finance.naver.com/research/industry_list.naver", "산업")
    check_and_run("https://finance.naver.com/research/company_list.naver", "기업")
    print("🏁 모든 작업 완료")
