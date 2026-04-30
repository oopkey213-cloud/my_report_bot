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
        # 산업 리포트: 엄격한 10줄 + 수혜주 3개
        prompt = (
            "너는 전문 애널리스트야. 주어진 텍스트 내용 '안에 있는 정보'로만 작성해.\n"
            "1. 주가 전망 같은 뻔한 소리는 빼고, 산업의 구조적 변화를 1번부터 10번까지 번호를 붙여 10줄로 요약해.\n"
            "2. 마지막 11행에는 본문에 언급된 '수혜 기업' 3개를 '관련 기업: 기업1, 기업2, 기업3' 형식으로 적어.\n"
            "3. 본문에 없는 기업(하이닉스 등)을 지어내면 절대 안 돼. 없으면 '관련 기업: 없음'이라고 해."
        )
    else:
        # 기업 리포트: 목표가 상향 근거 3줄
        prompt = "이 기업의 '목표주가 상향 이유'를 리포트 본문 근거로 딱 3줄 요약해줘. 본문에 없는 내용은 쓰지 마."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"리포트 본문 내용:\n{text[:7000]}"}
            ],
            temperature=0 # 환각 방지를 위해 창의성 0
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"요약 생성 실패: {e}"

def get_real_pdf_url(detail_url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(detail_url, headers=headers, timeout=10)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, 'html.parser')
        file_div = soup.select_one('div.view_file')
        if file_div and file_div.select_one('a'):
            return file_div.select_one('a')['href']
    except: return None

def process_pdf(pdf_url):
    try:
        r = requests.get(pdf_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        with open("temp.pdf", "wb") as f: f.write(r.content)
        doc = fitz.open("temp.pdf")
        text = ""
        for i in range(min(len(doc), 5)): text += doc[i].get_text()
        return text.strip()
    except Exception as e:
        print(f"   - PDF 읽기 실패: {e}")
        return ""

def check_and_run(url, report_type):
    print(f"\n--- {report_type} 리포트 탐색 시작 ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    
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
            print(f"👉 확인 중: {title}")
            
            # 1. 중복 체크
            if title in sent_titles:
                print("   - 이미 보낸 리포트입니다. 스킵!")
                continue
            
            # 2. 기업 리포트 상향 필터
            if report_type == "기업" and not any(k in title for k in ["상향", "↑"]):
                print("   - 상향 리포트가 아닙니다. 스킵!")
                continue

            # 3. 상세 페이지 -> PDF 추출
            detail_url = "https://finance.naver.com/research/" + a_tag['href']
            pdf_url = get_real_pdf_url(detail_url)
            if not pdf_url: 
                print("   - PDF 링크를 못 찾았습니다.")
                continue
            
            pdf_text = process_pdf(pdf_url)
            if not pdf_text or len(pdf_text) < 100:
                print("   - PDF 내용이 비어있거나 읽을 수 없는 형식입니다.")
                continue
            
            # 4. 요약 및 전송
            print("   - AI 요약 중...")
            summary = get_summary(pdf_text, report_type)
            
            msg = f"📢 *[{report_type} 분석]*\n📌 {title}\n\n{summary}\n\n🔗 [원문보기]({pdf_url})"
            send_tg(msg)
            
            # 기록 업데이트
            with open(sent_file, "a", encoding="utf-8") as f:
                f.write(title + "\n")
            print(f"✅ 전송 완료: {title}")
            time.sleep(3)
            
    except Exception as e:
        print(f"🚨 에러 발생: {e}")

if __name__ == "__main__":
    check_and_run("https://finance.naver.com/research/industry_list.naver", "산업")
    check_and_run("https://finance.naver.com/research/company_list.naver", "기업")
