import requests
from bs4 import BeautifulSoup
import os
import fitz  # PyMuPDF
from openai import OpenAI
import time

# 1. 정보 설정 (수정 불필요)
TOKEN = "8674194148:AAEEseoUojsIS1bbVNqvyM_3gFXPbTRjVeA"
CHAT_ID = "1674011615"
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def send_tg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def get_summary(text, report_type):
    prompt = f"너는 전문 주식 애널리스트야. 다음 {report_type} 리포트 내용을 읽고 '핵심 투자 포인트 3줄'과 '주의해야 할 리스크 1줄'로 깔끔하게 요약해줘."
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text[:6000]} # 글자수 제한
            ],
            temperature=0.5
        )
        return response.choices[0].message.content
    except:
        return "요약 생성 중 오류가 발생했습니다."

def process_pdf(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        with open("temp.pdf", "wb") as f:
            f.write(r.content)
        doc = fitz.open("temp.pdf")
        text = ""
        for i in range(min(len(doc), 3)): # 앞 3페이지만 읽기
            text += doc[i].get_text()
        return text
    except:
        return None

def check_and_run(url, report_type):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.select('table.type_1 tr')
    
    # 기억 장치 (이미 보낸 리포트 제외)
    sent_file = "last_title.txt"
    sent_titles = []
    if os.path.exists(sent_file):
        with open(sent_file, "r", encoding="utf-8") as f:
            sent_titles = f.read().splitlines()

    new_sent = sent_titles.copy()
    
    for row in rows:
        title_td = row.select_one('td.text_l')
        if not title_td or not title_td.select_one('a'): continue
        
        title = title_td.text.strip()
        
        # 2번 기능: 기업 리포트일 경우 '상향'이나 '↑'가 있을 때만 진행
        if report_type == "기업" and not any(keyword in title for keyword in ["상향", "↑", "Buy", "매수"]):
            continue
            
        if title in sent_titles: continue

        link = "https://finance.naver.com/research/" + title_td.select_one('a')['href']
        brokerage = row.select('td')[2].text.strip()
        
        # PDF 요약 시작
        pdf_text = process_pdf(link)
        summary = get_summary(pdf_text, report_type) if pdf_text else "내용을 요약할 수 없습니다."
        
        msg = f"📢 *신규 {report_type} 리포트 요약*\n\n📌 *제목:* {title}\n🏢 *증권사:* {brokerage}\n\n🤖 *AI 핵심 요약*\n{summary}\n\n🔗 [리포트 원문 보기]({link})"
        send_tg(msg)
        
        new_sent.append(title)
        time.sleep(2) # 텔레그램 도배 방지

    # 수첩 업데이트
    with open(sent_file, "w", encoding="utf-8") as f:
        f.write("\n".join(new_sent[-100:]))

if __name__ == "__main__":
    print("산업 리포트 확인 중...")
    check_and_run("https://finance.naver.com/research/industry_list.naver", "산업")
    
    print("기업 리포트(상향) 확인 중...")
    check_and_run("https://finance.naver.com/research/company_list.naver", "기업")
