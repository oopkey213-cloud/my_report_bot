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
    requests.post(url, data=payload, timeout=10)

def get_summary(text, report_type):
    if not api_key: return "API 키 없음"
    
    if report_type == "산업":
        # [수정] 번호 매기기 + 가상 기업 금지 + 산업 핵심 집중
        prompt = (
            "너는 주식 분석 전문가야. 제공된 리포트 텍스트만 바탕으로 요약해.\n"
            "1. 뻔한 소리(AI, 친환경 등) 하지 말고 리포트의 핵심 산업 내용을 1번부터 10번까지 번호를 붙여 10줄로 요약해.\n"
            "2. 마지막 11행에는 리포트에서 언급된 '실제 수혜 기업' 혹은 '핵심 기업' 3개를 찾아서 '관련 기업: 기업명1, 기업명2, 기업명3'으로 적어.\n"
            "3. 리포트에 없는 기업은 절대 지어내지 마."
        )
    else:
        # [수정] 목표가 상향 근거에 집중
        prompt = "전문 애널리스트로서 이 기업의 '목표주가 상향 이유'와 '향후 실적 전망'을 핵심 3줄로 요약해줘."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"리포트 내용:\n{text[:8000]}"} # 더 많은 텍스트 전달
            ],
            temperature=0.0 # 정확도를 위해 창의성을 0으로 설정
        )
        return response.choices[0].message.content
    except:
        return "요약 실패"

def process_pdf(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        with open("temp.pdf", "wb") as f: f.write(r.content)
        doc = fitz.open("temp.pdf")
        text = ""
        # 텍스트 추출 성능 향상 (5페이지까지 읽기)
        for i in range(min(len(doc), 5)):
            text += doc[i].get_text()
        return text if text.strip() else None
    except: return None

def check_and_run(url, report_type):
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
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 3: continue 
            a_tag = cols[1].find('a')
            if not a_tag: continue
            
            title = a_tag.get_text().strip()
            
            # 1. 중복 패스
            if title in sent_titles: continue
            
            # 2. 기업 리포트 '상향' 필터링 (아주 엄격하게)
            if report_type == "기업":
                if not any(k in title for k in ["상향", "↑"]):
                    continue

            link = "https://finance.naver.com/research/" + a_tag['href']
            brokerage = cols[2].get_text().strip()
            
            pdf_text = process_pdf(link)
            if not pdf_text: continue # 텍스트 못 읽으면 패스
            
            summary = get_summary(pdf_text, report_type)
            
            msg = f"📢 *[{report_type} 핵심 브리핑]*\n📌 {title}\n🏢 {brokerage}\n\n{summary}\n\n🔗 [원문보기]({link})"
            send_tg(msg)
            
            sent_titles.append(title)
            with open(sent_file, "a", encoding="utf-8") as f:
                f.write(title + "\n")
            time.sleep(3) # AI 과부하 방지
            
    except Exception as e:
        print(f"에러: {e}")

if __name__ == "__main__":
    check_and_run("https://finance.naver.com/research/industry_list.naver", "산업")
    check_and_run("https://finance.naver.com/research/company_list.naver", "기업")
