import requests
from bs4 import BeautifulSoup
import os
import fitz  # PyMuPDF
from openai import OpenAI
import time

# 설정
TOKEN = "8674194148:AAEEseoUojsIS1bbVNqvyM_3gFXPbTRjVeA"
CHAT_ID = "1674011615"
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def send_tg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

def get_summary(text, report_type):
    if not api_key: return "API 키 없음"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "주식 애널리스트로서 리포트 내용을 '핵심 3줄'로 요약해줘."},
                {"role": "user", "content": text[:4000]}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"요약 실패: {e}"

def process_pdf(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        with open("temp.pdf", "wb") as f:
            f.write(r.content)
        doc = fitz.open("temp.pdf")
        text = ""
        for i in range(min(len(doc), 2)): text += doc[i].get_text()
        return text
    except: return None

def force_check(url, report_type):
    print(f"--- {report_type} 리포트 강제 수집 중 ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.select('table.type_1 tr')
    
    count = 0
    for row in rows:
        title_td = row.select_one('td.text_l')
        if not title_td or not title_td.select_one('a'): continue
        
        title = title_td.text.strip()
        link = "https://finance.naver.com/research/" + title_td.select_one('a')['href']
        brokerage = row.select('td')[2].text.strip()
        
        # 강제로 첫 2개만 보냅니다.
        print(f"발견 및 전송 중: {title}")
        pdf_text = process_pdf(link)
        summary = get_summary(pdf_text, report_type) if pdf_text else "요약 불가"
        
        msg = f"📢 *[강제전송] {report_type} 리포트*\n📌 {title}\n🏢 {brokerage}\n\n🤖 *AI 요약*\n{summary}\n\n🔗 [원문보기]({link})"
        send_tg(msg)
        
        count += 1
        if count >= 2: break # 한 번에 너무 많이 오면 놀라시니까 2개씩만!
        time.sleep(2)

if __name__ == "__main__":
    send_tg("🚀 로봇이 강제 전송 모드로 가동되었습니다! 잠시만 기다려 주세요.")
    force_check("https://finance.naver.com/research/industry_list.naver", "산업")
    force_check("https://finance.naver.com/research/company_list.naver", "기업")
