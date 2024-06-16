import os.path
import re
import base64
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
from datetime import datetime, timezone, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow

# Gmail APIのスコープ設定
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    service = build('gmail', 'v1', credentials=creds)
    return service


def get_one_time_key(service):
    #print("関数 get_one_time_key が呼び出されました")
    jst = timezone(timedelta(hours=9))  # 日本標準時 (JST)
    start_time_jst = datetime.now(jst) - timedelta(seconds=60)  # 現在の時刻から60秒前を計算
    # UNIXタイムスタンプに変換
    start_time_unix = int(start_time_jst.timestamp())
    query = f"from:info@eonet.ne.jp subject:【オプテージ】ワンタイムキーのお知らせ after:{start_time_unix}"

    end_time = datetime.now(jst) + timedelta(seconds=60)  # 終了時刻を現在時刻から60秒後に設定

    while datetime.now(jst) < end_time:
        try:
            #print("メールの検索を開始します")
            results = service.users().messages().list(userId='me', labelIds=['INBOX'], q=query).execute()
            messages = results.get('messages', [])
            #print(f"見つかったメールの数: {len(messages)}")

            if messages:
                for msg in messages:
                    #print("メールの詳細を取得します")
                    msg = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                    msg_internal_date = int(msg['internalDate']) / 1000  # milliseconds to seconds
                    msg_internal_date_jst = datetime.fromtimestamp(msg_internal_date, tz=jst)
                    #print(f"メールの受信日時 (JST): {msg_internal_date_jst}")

                    if msg_internal_date_jst > start_time_jst:
                        #print("メールが開始時刻以降に受信されました")

                        if 'payload' in msg:
                            #print("メールのペイロードを解析します")

                            if 'parts' in msg['payload']:
                                for part in msg['payload']['parts']:
                                    if part['mimeType'] == 'text/plain':
                                        data = part['body']['data']
                                        text = base64.urlsafe_b64decode(data.encode('ASCII')).decode('utf-8')
                                        #print("メール本文:")
                                        #print(text)  # 本文を出力
                                        match = re.search(r"次のワンタイムキーを10分以内に画面へ入力してください。\n\n(\d{6})", text)
                                        if match:
                                            #print("ワンタイムキーが見つかりました")
                                            return match.group(1)

                            elif 'body' in msg['payload']:
                                if 'data' in msg['payload']['body']:
                                    data = msg['payload']['body']['data']
                                    text = base64.urlsafe_b64decode(data.encode('ASCII')).decode('utf-8')
                                    #print("メール本文:")
                                    #print(text)  # 本文を出力
                                    match = re.search(r"次のワンタイムキーを10分以内に画面へ入力してください。\n\n(\d{6})", text)
                                    if match:
                                        #print("ワンタイムキーが見つかりました")
                                        return match.group(1)
            #else:
                #print("メールが見つかりませんでした。")

        except Exception as e:
            #print(f"エラーが発生しました: {e}")  # エラーメッセージを出力
            pass
        
        #print("ワンタイムキーが見つかりませんでした。10秒後に再試行します。")
        time.sleep(10)

    return None



# Chromeの設定
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--headless")
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
    start_time = datetime.now(timezone.utc)
    one_time_key = get_one_time_key(service)
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

        # スクロールしてターゲットボタンが表示されるまで待機
        target_button = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="boxData"]/div[1]/div[4]/p/input'))
        )

        # JavaScriptでスクロール
        driver.execute_script("arguments[0].scrollIntoView(true);", target_button)

        # ターゲットボタンをクリック
        target_button.click()

        #changed_button_text = driver.find_element(By.XPATH, '//*[@id="boxData"]/div[1]/div[4]/p/input').get_attribute('value')
        #print(f"ボタンのテキストが変化しました: {changed_button_text}")
        print("最後まで行ったよ")
    else:
        #print("ワンタイムキーの取得に失敗しました。タイムアウトしました。")
        pass

finally:
    # ブラウザを閉じる
    driver.quit()
