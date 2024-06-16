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

# ログの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(level)name)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('gmail', 'v1', credentials=creds)
    return service

def get_one_time_key(service):
    start_time = time.time()
    end_time = start_time + 30  # 30秒後のタイムアウト時間
    print("A")
    while time.time() < end_time:
        logger.info("ワンタイムキーのメールを探しています...")
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], q="from:info@eonet.ne.jp subject:ワンタイムキー").execute()
        messages = results.get('messages', [])
        if messages:
            logger.info("メールを受信しました。内容を確認しています...")
            for msg in messages:
                msg = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                if 'payload' in msg:
                    if 'parts' in msg['payload']:
                        for part in msg['payload']['parts']:
                            if part['mimeType'] == 'text/plain':
                                data = part['body']['data']
                                text = base64.urlsafe_b64decode(data.encode('ASCII')).decode('utf-8')
                                match = re.search(r"次のワンタイムキーを10分以内に画面へ入力してください。\n\n(\d{6})", text)
                                if match:
                                    logger.info("ワンタイムキーを見つけました。")
                                    return match.group(1)
                    elif 'body' in msg['payload']:
                        if 'data' in msg['payload']['body']:
                            data = msg['payload']['body']['data']
                            text = base64.urlsafe_b64decode(data.encode('ASCII')).decode('utf-8')
                            match = re.search(r"次のワンタイムキーを10分以内に画面へ入力してください。\n\n(\d{6})", text)
                            if match:
                                logger.info("ワンタイムキーを見つけました。")
                                return match.group(1)
        else:
            logger.info("まだメールが届いていません。少し待機します...")
            time.sleep(10)  # 10秒ごとにメールをチェック

    logger.error("ワンタイムキーのメールが見つかりませんでした。タイムアウトしました。")
    return None

# Chromeの設定
chrome_options = Options()
# chrome_options.add_argument("--headless")  # ヘッドレスモードを無効化
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# ChromeDriverの自動インストールと初期化
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)


# mineoのマイページにアクセス
driver.get("https://mineo.jp/service/tool/mypage/")
logger.info("マイページにアクセスしました。URL: %s", driver.current_url)

# 指定されたリンクを探してクリック
link = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.XPATH, '//*[@id="wrapper"]/main/article/section[1]/div/p/a'))
)
link.click()
logger.info("リンクをクリックしました。")

# ページ遷移を待つ
WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
logger.info("ページ遷移が完了しました。")

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
logger.info("メールアドレス入力欄が見つかり、メールアドレスを入力しました。")

# 次へボタンをクリック
next_button = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.XPATH, '//*[@id="btnSubmit"]'))
)
next_button.click()
logger.info("次へボタンをクリックしました。")

# パスワード入力フォームを探してクリック
password_field = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, '//*[@id="password"]'))
)
password_field.click()
password_field.send_keys("nk02hmp424")
logger.info("パスワード入力欄が見つかり、パスワードを入力しました。")

# 次へボタンをクリック
login_button = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.XPATH, '//*[@id="btnSubmit"]'))
)
login_button.click()
logger.info("ログインボタンをクリックしました。")

time.sleep(3)

# Gmail APIを使用してワンタイムキーを取得
service = get_gmail_service()
one_time_key = get_one_time_key(service)
if one_time_key:
    logger.info("ワンタイムキーを取得しました: %s", one_time_key)

    # ワンタイムキー入力フォームにワンタイムキーを入力
    logger.info("ワンタイムキー入力欄を探しています...")
    one_time_key_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="oneTimeKey"]'))
    )
    logger.info("ワンタイムキー入力欄が見つかりました。")
    one_time_key_field.click()
    one_time_key_field.send_keys(one_time_key)
    logger.info("ワンタイムキーを入力しました。")

    # ログインボタンをクリック
    logger.info("ログインボタンを探しています...")
    submit_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="btnSubmit"]'))
    )
    logger.info("ログインボタンが見つかりました。")
    submit_button.click()
    logger.info("ログインボタンをクリックしました。")
else:
    logger.error("ワンタイムキーの取得に失敗しました。タイムアウトしました。")


# ブラウザを閉じる
driver.quit()
