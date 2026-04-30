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
    
    if report_type == "산업":
        # 산업 리포트용 프롬프트 (10줄 요약 + 3개 기업)
        prompt = (
            "너는 주식 시장의 거시 흐름을 분석하는 전문 전략가야. "
            "다음 산업 리포트를 읽고 아래 형식을 엄격히 지켜서 요약해줘.\n"
            "1. 현재 주가 흐름이나 단순 가격 설명은 제외할 것.\n"
            "2. 산업의 구조적 변화, 기술적 트렌드, 매크로 환경에 집중하여 상세하게 10줄로 요약할 것.\n"
            "3. 마지막 11번째 줄에는 이 산업과 관련된 핵심 기업 3개만 '관련 기업: 기업A, 기업B, 기업C' 형식으로 적을 것."
        )
    else:
        # 기업 리포트용 프롬프트
        prompt = "전문 애널리스트로서 이 기업의 목표주가 상향 근거를 핵심 3줄로 요약해줘."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text[:6000]}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except:
        return "요약 생성 중 오류 발생"

def process_pdf(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        with open("temp.pdf", "wb") as f: f.write(r.content)
        doc = fitz.open("temp.pdf")
        text = ""
        for i in range(min(len(doc), 4)): text += doc[i].get_text() # 더 깊은 분석을 위해 4페이지까지
        return text
    except: return None

def check_and_run(url, report_type):
    print(f"\n🔎 {report_type} 리포트 필터링 중...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
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
        
        count = 0
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 3: continue 
            
            a_tag = cols[1].find('a')
            if not a_tag: continue
            
            title = a_tag.get_text().strip()
            
            # [필터 로직]
            if title in sent_titles: continue # 중복 제외
            
            if report_type == "기업":
                # 기업 리포트는 '상향' 혹은 '↑'가 제목에 있는 경우만 엄격히 선별
                if not any(k in title for k in ["상향", "↑"]):
                    continue
            
            # 산업 리포트는 모든 신규 리포트를 보되, 요약을 10줄로 상세화함
            
            print(f"🎯 신규 타겟 발송: {title}")
            link = "https://finance.naver.com/research/" + a_tag['href']
            brokerage = cols[2].get_text().strip()
            
            pdf_text = process_pdf(link)
            summary = get_summary(pdf_text, report_type) if pdf_text else "요약 실패"
            
            msg = f"📢 *[{report_type} 분석]*\n📌 {title}\n🏢 {brokerage}\n\n🤖 *AI 분석 리포트*\n{summary}\n\n🔗 [원문보기]({link})"
            send_tg(msg)
            
            sent_titles.append(title)
            count += 1
            if count >= 5: break # 너무 많은 도배 방지를 위해 한 번에 최대 5개까지만
            time.sleep(2)
            
        with open(sent_file, "w", encoding="utf-8") as f:
            f.write("\n".join(sent_titles[-100:]))
            
    except Exception as e:
        print(f"🚨 에러: {e}")

if __name__ == "__main__":
    # 산업 리포트: 모든 신규 리포트를 10줄+3사 형식으로 요약
    check_and_run("https://finance.naver.com/research/industry_list.naver", "산업")
    # 기업 리포트: 상향 리포트만 선별하여 요약
    check_and_run("https://finance.naver.com/research/company_list.naver", "기업")
