import os.path
import re
import base64
import logging
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

# Gmail APIのスコープ設定
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None
    # トークンファイルが存在する場合、そこから認証情報を読み込む
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # 認証情報が無効な場合、再認証を行う
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    # Gmail APIサービスを構築
    service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
    
    return service

def get_one_time_key(service, start_time):
    end_time = time.time() + 120  # 30秒後のタイムアウト時間
    query = f"from:info@eonet.ne.jp subject:ワンタイムキー after:{int(start_time.timestamp())}"
    while time.time() < end_time:
        try:
            results = service.users().messages().list(userId='me', labelIds=['INBOX'], q=query).execute()
            messages = results.get('messages', [])
            if messages:
                for msg in messages:
                    msg = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                    msg_internal_date = int(msg['internalDate']) / 1000  # milliseconds to seconds
                    if datetime.fromtimestamp(msg_internal_date) > start_time:
                        if 'payload' in msg:
                            if 'parts' in msg['payload']:
                                for part in msg['payload']['parts']:
                                    if part['mimeType'] == 'text/plain':
                                        data = part['body']['data']
                                        text = base64.urlsafe_b64decode(data.encode('ASCII')).decode('utf-8')
                                        match = re.search(r"次のワンタイムキーを10分以内に画面へ入力してください。\n\n(\d{6})", text)
                                        if match:
                                            return match.group(1)
                            elif 'body' in msg['payload']:
                                if 'data' in msg['payload']['body']:
                                    data = msg['payload']['body']['data']
                                    text = base64.urlsafe_b64decode(data.encode('ASCII')).decode('utf-8')
                                    match = re.search(r"次のワンタイムキーを10分以内に画面へ入力してください。\n\n(\d{6})", text)
                                    if match:
                                        return match.group(1)
            else:
                time.sleep(10)  # 10秒ごとにメールをチェック
        except Exception as e:
            time.sleep(10)  # エラーが発生した場合でも少し待機します
    return None

# Chromeの設定
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# ChromeDriverの自動インストールと初期化
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

try:
    # mineoのマイページにアクセス
    driver.get("https://mineo.jp/service/tool/mypage/")
    
    # 指定されたリンクを探してクリック
    link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="wrapper"]/main/article/section[1]/div/p/a'))
    )
    link.click()

    # ページ遷移を待つ
    WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))

    # 新しいタブに切り替え
    original_window = driver.current_window_handle
    new_window = [window for window in driver.window_handles if window != original_window][0]
    driver.switch_to.window(new_window)

    # 元のタブを閉じる
    driver.switch_to.window(original_window)
    driver.close()

    # 新しいタブに再度切り替え
    driver.switch_to.window(new_window)

    # メールアドレス入力フォームを探してクリック
    email_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="eoID"]'))
    )
    email_field.click()
    email_field.send_keys("mukaiyama.yusuke0424@gmail.com")

    # 次へボタンをクリック
    next_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="btnSubmit"]'))
    )
    next_button.click()

    # パスワード入力フォームを探してクリック
    password_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="password"]'))
    )
    password_field.click()
    password_field.send_keys("nk02hmp424")

    # 次へボタンをクリック
    login_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="btnSubmit"]'))
    )
    login_button.click()

    time.sleep(3)

    # Gmail APIを使用してワンタイムキーを取得
    service = get_gmail_service()
    start_time = datetime.now()
    one_time_key = get_one_time_key(service, start_time)
    if one_time_key:
        # ワンタイムキー入力フォームにワンタイムキーを入力
        one_time_key_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="oneTimeKey"]'))
        )
        one_time_key_field.click()
        one_time_key_field.send_keys(one_time_key)

        # ログインボタンをクリック
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="btnSubmit"]'))
        )
        submit_button.click()

        # ページ遷移を待機
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="boxData"]/div[1]/div[4]/p/input')))

        # 要素をクリック
        button = driver.find_element(By.XPATH, '//*[@id="boxData"]/div[1]/div[4]/p/input')
        button.click()

        # ボタンの状態が変化するまで待機し、その後のテキストを取得
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element((By.XPATH, '//*[@id="boxData"]/div[1]/div[4]/p/input'), "変化後のテキスト")
        )
        changed_button_text = driver.find_element(By.XPATH, '//*[@id="boxData"]/div[1]/div[4]/p/input').get_attribute('value')
        print(f"ボタンのテキストが変化しました: {changed_button_text}")
    else:
        print("ワンタイムキーの取得に失敗しました。タイムアウトしました。")

finally:
    # ブラウザを閉じる
    driver.quit()
