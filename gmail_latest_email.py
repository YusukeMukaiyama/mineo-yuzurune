import os.path
import base64
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_latest_email():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        # Call the Gmail API
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().messages().list(userId='me', maxResults=1, q="").execute()
        messages = results.get('messages', [])

        if not messages:
            print('No messages found.')
            return

        message = service.users().messages().get(userId='me', id=messages[0]['id']).execute()

        # Function to get the body from the message
        def get_message_body(msg):
            if 'data' in msg['body']:
                return base64.urlsafe_b64decode(msg['body']['data']).decode('utf-8')
            elif 'parts' in msg:
                for part in msg['parts']:
                    if 'data' in part['body']:
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            return ""

        msg_str = get_message_body(message['payload'])

        print('Message snippet: %s' % message['snippet'])
        print('Message body: %s' % msg_str)

    except HttpError as error:
        print(f'An error occurred: {error}')

if __name__ == '__main__':
    get_latest_email()
