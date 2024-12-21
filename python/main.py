# TODO: add flow for browser-only auth 
#   user goes to some auth endpoint, gives phone, authorizes from there
#   this is how you authenticate if your sms access does not have internet access

# TODO: change all html to templates

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

import secrets
import pkce
import requests
import base64
import json
import sqlite3

app = FastAPI()

@app.on_event('startup')
def on_startup():
    f = open('python/creds.txt').readlines()
    global cid, secret
    cid = f[0].strip()
    secret = f[1].strip()

    global code_verifier, code
    code_verifier, code = pkce.generate_pkce_pair()

    global global_state
    global_state = {}

    # db setup
    global con, cur
    con = sqlite3.connect('sms-tweet.db')
    cur = con.cursor()
    res = cur.execute("SELECT name FROM sqlite_master WHERE name='users'")
    # users table does not currently exist, set it up
    if res.fetchone() is None:
        query = """
            CREATE TABLE users (
                phone TEXT PRIMARY KEY NOT NULL,
                bearer TEXT NOT NULL,
                bearerExpiration TIMESTAMP NOT NULL,
                refresh TEXT NOT NULL,
                refreshExpiration TIMESTAMP NOT NULL
        );
        """
        cur.execute(query)

@app.on_event('shutdown')
def on_shutdown():
    con.close()

@app.get('/', response_class=HTMLResponse)
async def root():
    return '''
    <head>
        <title>tweet via sms</title>
    </head>
    <body>
        <p>Reviving Twitter via SMS. <br><br>Text 'tweet' to +1 (855) 926-0117 to start.</p>
    </body>
    '''

@app.get('/auth', response_class=HTMLResponse)
async def auth(phone: str | None = None):
    if phone is None:
        return '''
        <head>
            <title>tweet via sms</title>
        </head>
        <body>
            <p>no phone number provided for auth</p>
        </body>
        '''
    query = 'SELECT * FROM users WHERE phone = ?'
    res = cur.execute(query, [phone])
    # phone number already in use
    # TODO: change phone formatting after twilio integration
    if res.fetchall() != []:
        return f'''
        <head>
            <title>tweet via sms</title>
        </head>
        <body>
            <p>phone number ({phone[0:3]}) {phone[3:6]}-{phone[6:]} already in use</p>
        </body>
        '''

    endpoint = 'https://twitter.com/i/oauth2/authorize'

    client_id = f'client_id={cid}'

    # TODO: change this to prod value and change in twitter dev console
    redir_uri = 'http://localhost:80/new'
    redir = f'redirect_uri={redir_uri}'

    scope = 'scope=tweet.write+tweet.read+users.read+offline.access'

    s = secrets.token_urlsafe(16)
    global_state[s] = (phone, s)
    print(global_state[s])

    code_challenge = f'code_challenge={code}'
    challenge_method = 'code_challenge_method=S256'

    url = f'{endpoint}?response_type=code&{client_id}&{redir}&{scope}&state={s}&{code_challenge}&{challenge_method}'
    print(url)
    return f'''
    <head>
        <title>tweet via sms</title>
    </head>
    <body>
        <a href={url}>authenticate with twitter</a>
    </body>
    '''

@app.get('/new', response_class=HTMLResponse)
async def new(state: str, code: str | None = None, error: str | None = None):
    if error == 'access_denied':
        return '<p>error, access denied</p>'

    if global_state[state][1] != state:
        print('global: ', global_state, ' returned state: ', state)
        return '<p>error, state values do not match</p>'

    url = 'https://api.twitter.com/2/oauth2/token'
    auth = f'{cid}:{secret}'
    encoded = base64.b64encode(auth.encode('utf-8')).decode('utf-8')
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {encoded}',
    }
    data = {
        'code': f'{code}',
        'grant_type': 'authorization_code',
        'client_id': f'{cid}',
        'redirect_uri': 'http://localhost:80/new',
        'code_verifier': f'{code_verifier}',
    }
    response = requests.post(url, headers=headers, data=data)
    print(response.headers)
    print(response.text) 
    if response.status_code == 200:
        phone = global_state[state][0] 
        r = json.loads(response.text)
        bearer = r['access_token']
        refresh = r['refresh_token']

        # delete any existing user with specified phone number
        query = 'DELETE FROM users WHERE phone = ?'
        cur.execute(query, [phone])
        # insert new user
        query = "INSERT INTO users VALUES (?, ?, DATETIME(CURRENT_TIMESTAMP, '+2 hours'), ?, DATETIME(CURRENT_TIMESTAMP, '+6 months'))"
        cur.execute(query, [phone, bearer, refresh])
        con.commit()
        res = cur.execute("SELECT * FROM users")
        for s in res.fetchall():
            print(s)
        return '<p>successfully authenticated</p>'
