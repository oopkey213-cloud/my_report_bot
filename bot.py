import requests
from bs4 import BeautifulSoup
import os
import fitz  # PyMuPDF
from openai import OpenAI
import time

TOKEN = "8674194148:AAEEseoUojsIS1bbVNqvyM_3gFXPbTRjVeA"
CHAT_ID = "1674011615"
# 금고에서 키를 가져옵니다.
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def send_tg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def get_summary(text, report_type):
    if not api_key:
        return "에러: OpenAI API 키가 설정되지 않았습니다."
    
    prompt = f"너는 전문 주식 애널리스트야. 다음 {report_type} 리포트를 읽고 '투자 포인트 3줄'과 '리스크 1줄'로 요약해줘."
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
    except Exception as e:
        return f"요약 생성 실패: {str(e)}"

def process_pdf(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        with open("temp.pdf", "wb") as f:
            f.write(r.content)
        doc = fitz.open("temp.pdf")
        text = ""
        for i in range(min(len(doc), 2)): # 앞 2페이지만
            text += doc[i].get_text()
        return text
    except:
        return None

def check_and_run(url, report_type):
    print(f"--- {report_type} 리포트 확인 시작 ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.select('table.type_1 tr')
    
    sent_file = "last_title.txt"
    sent_titles = []
    if os.path.exists(sent_file):
        with open(sent_file, "r", encoding="utf-8") as f:
            sent_titles = f.read().splitlines()

    new_count = 0
    for row in rows:
        title_td = row.select_one('td.text_l')
        if not title_td or not title_td.select_one('a'): continue
        
        title = title_td.text.strip()
        
        # 기업 리포트 필터링 (상향, ↑, 매수)
        if report_type == "기업" and not any(k in title for k in ["상향", "↑", "매수", "Buy"]):
            continue
            
        if title in sent_titles: continue

        print(f"발견: {title}")
        link = "https://finance.naver.com/research/" + title_td.select_one('a')['href']
        brokerage = row.select('td')[2].text.strip()
        
        pdf_text = process_pdf(link)
        summary = get_summary(pdf_text, report_type) if pdf_text else "PDF 읽기 실패"
        
        msg = f"📢 *신규 {report_type} 리포트*\n📌 {title}\n🏢 {brokerage}\n\n🤖 *AI 요약*\n{summary}\n\n🔗 [원문]({link})"
        send_tg(msg)
        sent_titles.append(title)
        new_count += 1
        time.sleep(2)

    with open(sent_file, "w", encoding="utf-8") as f:
        f.write("\n".join(sent_titles[-100:]))
    print(f"--- {report_type} 완료 (새로 보낸 개수: {new_count}) ---")

if __name__ == "__main__":
    # 실행되자마자 텔레그램으로 신호를 보냅니다.
    send_tg("🤖 리포트 수집 로봇이 가동되었습니다. 새로운 리포트를 탐색합니다.")
    check_and_run("https://finance.naver.com/research/industry_list.naver", "산업")
    check_and_run("https://finance.naver.com/research/company_list.naver", "기업")
