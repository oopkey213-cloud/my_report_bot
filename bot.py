import requests
from bs4 import BeautifulSoup
import os
import fitz  # PyMuPDF
from openai import OpenAI
import time

# 1. 기본 설정
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
    # 산업 리포트는 5줄, 기업 리포트는 3줄 요약 요청
    line_count = "5줄" if report_type == "산업" else "3줄"
    prompt = (
        f"너는 전문 주식 애널리스트야. 다음 {report_type} 리포트 내용을 분석해서 "
        f"투자자들이 반드시 알아야 할 핵심 포인트를 딱 {line_count}로 요약해줘. "
        f"숫자나 구체적인 근거가 있다면 포함해줘."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text[:5000]}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content
    except:
        return "요약 생성 중 오류가 발생했습니다."

def process_pdf(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        with open("temp.pdf", "wb") as f: f.write(r.content)
        doc = fitz.open("temp.pdf")
        text = ""
        # 조금 더 자세한 분석을 위해 앞 3페이지만 읽기
        for i in range(min(len(doc), 3)): text += doc[i].get_text()
        return text
    except: return None

def check_and_run(url, report_type):
    print(f"\n🔎 {report_type} 리포트 분석 중...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    # 기억 장치 로드
    sent_file = "last_title.txt"
    sent_titles = []
    if os.path.exists(sent_file):
        with open(sent_file, "r", encoding="utf-8") as f:
            sent_titles = f.read().splitlines()

    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'euc-kr'
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.find_all('tr')
        
        new_sent = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 3: continue 
            
            a_tag = cols[1].find('a')
            if not a_tag: continue
            
            title = a_tag.get_text().strip()
            
            # [핵심 필터링]
            # 1. 이미 보낸 리포트는 패스
            if title in sent_titles: continue
            
            # 2. 기업 리포트는 '상향' 혹은 '↑'가 있는 경우만 보냄
            if report_type == "기업":
                if not any(k in title for k in ["상향", "↑"]):
                    continue

            print(f"✨ 신규 타겟 발견: {title}")
            link = "https://finance.naver.com/research/" + a_tag['href']
            brokerage = cols[2].get_text().strip()
            
            pdf_text = process_pdf(link)
            summary = get_summary(pdf_text, report_type) if pdf_text else "내용 요약 불가"
            
            msg = f"📢 *신규 {report_type} 분석*\n📌 *제목:* {title}\n🏢 *증권사:* {brokerage}\n\n🤖 *AI 핵심 요약*\n{summary}\n\n🔗 [원문보기]({link})"
            send_tg(msg)
            
            sent_titles.append(title)
            time.sleep(2) # 전송 안정성 확보
            
        # 기억 장치 업데이트
        with open(sent_file, "w", encoding="utf-8") as f:
            f.write("\n".join(sent_titles[-100:])) # 최근 100개만 유지
            
    except Exception as e:
        print(f"🚨 에러 발생: {e}")

if __name__ == "__main__":
    check_and_run("https://finance.naver.com/research/industry_list.naver", "산업")
    check_and_run("https://finance.naver.com/research/company_list.naver", "기업")
    print("🏁 모든 작업 완료")
