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
    
    # [수정됨] 차분한 시각화, 줄 띄움 제거, 사용자 맞춤 프롬프트 유지
    prompt = (
        "너는 거시 경제와 산업 트렌드, 섹터 분석을 최고 수준으로 잘하는 애널리스트야.\n"
        "아래 제공된 '리포트 원문'을 분석해서 다음 규칙을 엄격히 지켜 요약해.\n"
        "1. 산업의 구조적 변화, 핵심 트렌드, 매크로 영향을 1번부터 10번까지 번호를 매겨 딱 10줄로 깊이 있게 요약해. (각 줄 사이에 불필요한 빈 줄은 넣지 마)\n"
        "2. [강조] 각 줄에서 가장 중요한 핵심 키워드나 수치는 반드시 **볼드체**로 처리해.\n"
        "3. [시각화] 너무 난잡한 이모지 대신 🔹, ▪️, 📌 등 차분한 도형 이모지를 사용하여 가독성을 깔끔하게 높여줘.\n"
        "4. [수혜주 추천] 요약이 끝난 후, 원문에 기업이 직접 언급되지 않았더라도 이 리포트의 산업 테마와 가장 연관성이 높은 '실제 시장 핵심 수혜 기업' 5개를 너의 배경지식을 동원해 찾아내어 '🎯 *관련 집중 수혜주*: 기업A, 기업B, 기업C, 기업D, 기업E' 형식으로 적어.\n"
        "5. 너의 메세지를 보는 사람들은 투자 전문가 수준이야. 간단한 수준의 내용은 아무런 도움이 안된다는 뜻이지. 요약을 잘 해야할 것이야. 그리고 10줄 요약 후 전체적인 결론을 한 줄로 너무 간단하지 않게 요약해서 결론을 내어줘."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"리포트 원문:\n{text[:8000]}"}
            ],
            temperature=0.4 
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
        
        if not r.content.startswith(b'%PDF'):
            return None
            
        with open("temp.pdf", "wb") as f:
            f.write(r.content)
            
        doc = fitz.open("temp.pdf")
        text = ""
        for i in range(min(len(doc), 6)): 
            text += doc[i].get_text()
            
        return text.strip() if len(text.strip()) > 200 else None
    except: return None

def check_industry_reports():
    print("🔎 네이버 산업 리포트 실전 버전 가동 시작...")
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
            
            # [핵심] 이미 보낸 리포트(수첩에 있는 제목)는 패스합니다.
            if title in sent_titles: continue
            
            detail_url = "https://finance.naver.com/research/" + a_tag['href']
            brokerage = cols[2].get_text().strip()
            
            pdf_url = get_real_pdf_url(detail_url)
            if not pdf_url: continue
            
            pdf_text = process_pdf(pdf_url)
            if not pdf_text: continue
            
            summary = get_summary(pdf_text)
            
            # 텔레그램 발송
            msg = f"📢 *[산업 심층 브리핑]*\n📌 {title}\n🏢 {brokerage}\n\n{summary}\n\n[🔗 원문보기]({pdf_url})"
            send_tg(msg)
            
            # 발송 성공 후 수첩에 제목 기록 (중복 방지)
            with open(sent_file, "a", encoding="utf-8") as f:
                f.write(title + "\n")
            
            time.sleep(5)
            
    except Exception as e:
        print(f"🚨 에러 발생: {e}")

if __name__ == "__main__":
    check_industry_reports()
