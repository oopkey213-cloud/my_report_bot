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
    try:
        r = requests.post(url, data=payload)
        return r.status_code
    except Exception as e:
        print(f"텔레그램 전송 에러: {e}")
        return 500

def get_summary(text, report_type):
    if not api_key: return "API 키 없음"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "주식 애널리스트로서 리포트를 3줄 요약해줘."},
                {"role": "user", "content": text[:4000]}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"요약 에러: {e}"

def check_and_run(url, report_type):
    print(f"\n🔎 [{report_type} 리포트] 탐색 시작...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 네이버 증권 리스트의 정확한 행 찾기
        rows = soup.select('table.type_1 tr')
        print(f"검사 대상 행 수: {len(rows)}개")

        sent_file = "last_title.txt"
        sent_titles = []
        if os.path.exists(sent_file):
            with open(sent_file, "r", encoding="utf-8") as f:
                sent_titles = f.read().splitlines()

        count = 0
        for row in rows:
            # 제목이 있는 칸 찾기
            title_td = row.select_one('td.text_l')
            if not title_td: continue
            
            a_tag = title_td.select_one('a')
            if not a_tag: continue
            
            title = a_tag.text.strip()
            
            # 기업 리포트일 때 '상향' 필터링 (테스트를 위해 잠시 완화)
            if report_type == "기업":
                is_up = any(k in title for k in ["상향", "↑", "매수", "Buy", "유지"]) # '유지'도 추가해서 테스트
                if not is_up: continue

            if title in sent_titles:
                continue

            print(f"✨ 새 리포트 발견: {title}")
            
            # PDF 링크 추출
            link = "https://finance.naver.com/research/" + a_tag['href']
            brokerage = row.select('td')[2].text.strip() if len(row.select('td')) > 2 else "정보없음"
            
            # 텔레그램 발송 (요약 없이 우선 발송 테스트)
            msg = f"📢 *신규 {report_type} 리포트*\n📌 {title}\n🏢 {brokerage}\n🔗 [원문보기]({link})"
            status = send_tg(msg)
            
            if status == 200:
                print(f"✅ 전송 성공: {title}")
                sent_titles.append(title)
                count += 1
            else:
                print(f"❌ 전송 실패: {title} (상태코드: {status})")
            
            if count >= 3: break # 테스트를 위해 한 번에 3개만
            time.sleep(1)

        with open(sent_file, "w", encoding="utf-8") as f:
            f.write("\n".join(sent_titles[-100:]))
            
    except Exception as e:
        print(f"🚨 작업 중 에러 발생: {e}")

if __name__ == "__main__":
    print("🚀 로봇 가동...")
    # 1단계: 연결 확인용 메시지
    send_tg("🤖 리포트 로봇이 사이트 접속을 시작합니다.")
    
    # 2단계: 리포트 체크
    check_and_run("https://finance.naver.com/research/industry_list.naver", "산업")
    check_and_run("https://finance.naver.com/research/company_list.naver", "기업")
    
    print("🏁 모든 작업 완료.")
