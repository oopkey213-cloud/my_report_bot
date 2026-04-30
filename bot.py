import requests
from bs4 import BeautifulSoup
import os
import fitz  # PyMuPDF
from openai import OpenAI
import time

# 1. 설정
TOKEN = "8674194148:AAEEseoUojsIS1bbVNqvyM_3gFXPbTRjVeA"
CHAT_ID = "1674011615"
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def send_tg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, data=payload, timeout=10)

def get_summary(text):
    if not api_key: return "API 키 없음"
    
    prompt = (
        "너는 거시 경제와 산업 트렌드를 분석하는 최고 수준의 애널리스트야.\n"
        "아래 제공된 '리포트 원문'만을 분석해서 다음 규칙을 엄격히 지켜 요약해줘.\n"
        "1. 원문에 없는 내용(특히 엉뚱한 기업명)은 절대 지어내지 마.\n"
        "2. 단순한 주가 설명은 제외하고, 산업의 구조적 변화, 핵심 논거, 매크로 환경을 1번부터 10번까지 번호를 매겨 딱 10줄로 깊이 있게 요약해.\n"
        "3. 11번째 줄에는 리포트 원문에 실제로 언급된 '핵심 수혜 기업' 3개를 골라 '관련 기업: 기업명1, 기업명2, 기업명3' 형식으로 적어.\n"
        "4. 원문에 기업이 언급되지 않았다면 '관련 기업: 원문 언급 없음'으로 명시해."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"리포트 원문:\n{text[:8000]}"}
            ],
            temperature=0.0 # 소설 쓰는 것(환각)을 완벽 차단
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"요약 에러: {e}"

def get_real_pdf_url(detail_url):
    """상세 페이지에서 진짜 '.pdf'로 끝나는 파일 주소를 찾습니다."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(detail_url, headers=headers, timeout=10)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for a_tag in soup.find_all('a', href=True):
            if '.pdf' in a_tag['href'].lower():
                return a_tag['href']
        return None
    except: return None

def process_pdf(pdf_url):
    """실제 PDF 파일을 다운받아 글자를 추출합니다."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(pdf_url, headers=headers, timeout=20)
        
        # 파일이 정상적인 PDF인지 매직 넘버(%PDF)로 검사
        if not r.content.startswith(b'%PDF'):
            print("   ❌ 다운받은 파일이 PDF 포맷이 아닙니다.")
            return None
            
        with open("temp.pdf", "wb") as f:
            f.write(r.content)
            
        doc = fitz.open("temp.pdf")
        text = ""
        # 산업 리포트는 깊이가 중요하므로 앞 6페이지까지 넉넉히 정독
        for i in range(min(len(doc), 6)): 
            text += doc[i].get_text()
            
        return text.strip() if len(text.strip()) > 200 else None
    except Exception as e:
        print(f"   ❌ PDF 처리 실패: {e}")
        return None

def check_industry_reports():
    print("🔎 산업 리포트 전용 봇 가동 시작...")
    url = "https://finance.naver.com/research/industry_list.naver"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
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
            
            # 이미 보낸 리포트 패스
            if title in sent_titles: continue
            
            print(f"\n👉 타겟 발견: {title}")
            detail_url = "https://finance.naver.com/research/" + a_tag['href']
            brokerage = cols[2].get_text().strip()
            
            # 1. 가짜 링크 거르고 진짜 PDF 링크 확보
            pdf_url = get_real_pdf_url(detail_url)
            if not pdf_url:
                print("   ❌ 상세 페이지에 PDF 파일이 없습니다.")
                continue
            
            # 2. PDF에서 텍스트 뽑기 (텍스트 없으면 요약 취소)
            print("   - PDF 파일 분석 중...")
            pdf_text = process_pdf(pdf_url)
            if not pdf_text:
                print("   ❌ 텍스트를 읽을 수 없는 PDF입니다. 건너뜁니다.")
                continue
            
            # 3. AI 분석 및 텔레그램 전송
            print("   - AI 요약 진행 중...")
            summary = get_summary(pdf_text)
            
            msg = f"📢 *[산업 심층 브리핑]*\n📌 {title}\n🏢 {brokerage}\n\n{summary}\n\n🔗 [원문 PDF 보기]({pdf_url})"
            send_tg(msg)
            
            print(f"✅ 텔레그램 전송 완료: {title}")
            
            # 성공한 리포트만 수첩에 기록
            with open(sent_file, "a", encoding="utf-8") as f:
                f.write(title + "\n")
            
            time.sleep(5)
            
    except Exception as e:
        print(f"🚨 에러 발생: {e}")

if __name__ == "__main__":
    check_industry_reports()
