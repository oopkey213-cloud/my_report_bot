import requests
from bs4 import BeautifulSoup
import os
import fitz  # PyMuPDF
from openai import OpenAI
import time

# 1. 기본 설정 (사용자 정보 반영)
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
        # 산업 리포트: 10줄 요약 + 실제 언급된 수혜주 3개
        prompt = (
            "너는 리서치 센터의 수석 애널리스트야. 반드시 제공된 리포트 '본문 내용'만 바탕으로 작성해.\n"
            "1. 리포트에 없는 기업(하이닉스 등)은 본문에 없으면 절대로 언급하지 마.\n"
            "2. 산업의 구조적 변화와 핵심 논거를 1~10번까지 번호를 붙여 10줄로 요약해.\n"
            "3. 마지막 11행에는 리포트에서 직접 언급된 '수혜 기업' 3개를 '관련 기업: 기업A, 기업B, 기업C' 형식으로 적어.\n"
            "4. 본문에 기업명이 없으면 '관련 기업: 리포트 내 없음'으로 적어."
        )
    else:
        # 기업 리포트: 목표가 상향 이유 중심 3줄
        prompt = "이 기업의 '목표주가 상향 이유'와 '실적 전망'을 리포트 본문 근거로 딱 3줄 요약해줘."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"리포트 본문:\n{text}"}
            ],
            temperature=0.0 # 환각 방지를 위해 창의성 0 설정
        )
        return response.choices[0].message.content
    except:
        return "요약 생성 실패"

def get_real_pdf_url(detail_url):
    """상세 페이지에서 진짜 PDF 파일 링크를 찾아옵니다."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(detail_url, headers=headers)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, 'html.parser')
        # 네이버 상세페이지의 PDF 다운로드 버튼 위치
        file_div = soup.select_one('div.view_file')
        if file_div and file_div.select_one('a'):
            return file_div.select_one('a')['href']
    except:
        return None

def process_pdf(pdf_url):
    """PDF를 다운로드하고 텍스트를 추출합니다."""
    try:
        r = requests.get(pdf_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        with open("temp.pdf", "wb") as f: f.write(r.content)
        doc = fitz.open("temp.pdf")
        text = ""
        # 본문을 정확히 파악하기 위해 앞 5페이지까지 정독
        for i in range(min(len(doc), 5)):
            text += doc[i].get_text()
        return text.strip() if len(text.strip()) > 200 else None
    except:
        return None

def check_and_run(url, report_type):
    print(f"--- {report_type} 리포트 정밀 탐색 시작 ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    
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
            if title in sent_titles: continue
            
            # 기업 리포트 상향 필터
            if report_type == "기업" and not any(k in title for k in ["상향", "↑"]):
                continue

            detail_url = "https://finance.naver.com/research/" + a_tag['href']
            
            # 1. 상세 페이지에서 진짜 PDF 링크 획득
            pdf_url = get_real_pdf_url(detail_url)
            if not pdf_url: continue
            
            # 2. PDF 텍스트 추출
            pdf_text = process_pdf(pdf_url)
            if not pdf_text: continue # 텍스트가 없으면 환각 방지를 위해 패스
            
            # 3. AI 요약 실행
            summary = get_summary(pdf_text, report_type)
            
            msg = f"📢 *[{report_type} 분석]*\n📌 {title}\n\n{summary}\n\n🔗 [원문보기]({pdf_url})"
            send_tg(msg)
            
            # 성공적으로 보내면 기록
            with open(sent_file, "a", encoding="utf-8") as f:
                f.write(title + "\n")
            time.sleep(5) # AI 안정성을 위해 5초 휴식
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_and_run("https://finance.naver.com/research/industry_list.naver", "산업")
    check_and_run("https://finance.naver.com/research/company_list.naver", "기업")
