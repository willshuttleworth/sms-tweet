# TODO: add flow for browser-only auth 
#   user goes to some auth endpoint, gives phone, authorizes from there
#   this is how you authenticate if your sms access does not have internet access

# TODO: change all html to templates

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, Response
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
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
        <p>Reviving Twitter via SMS. <br><br>Text 'tweet' to (218) 319-7248 to start.</p>
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

    endpoint = 'https://twitter.com/i/oauth2/authorize'

    client_id = f'client_id={cid}'

    # TODO: change this to prod value and change in twitter dev console
    redir_uri = 'http://localhost:80/new'
    # redir_uri = 'https://smstweet.org/new'
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
        <p>by authenticating with twitter, you opt in to receiving messages from smstweet. </p>
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
        # TODO: send message with usage instructions to new user
        return '<p>successfully authenticated</p>'

@app.post('/sms', response_class=Response)
async def sms(Body: str = Form(...), From: str = Form(...)):
    # TODO: opt in structure: users are asked to opt in after first message, authorizing via twitter counts as opting in

    # TODO: check for existence of phone in db
    #   if phone exists, check token validity (bearer, refresh)
    #       tweet or reauth
    #   else, auth
    phone = From[1:]
    print(f'received message: {Body} from {phone}')
    response = MessagingResponse()
    response.message(f'you tweeted {Body}')

    query = 'SELECT * FROM users WHERE phone = ?'
    res = cur.execute(query, [phone])
    # new phone, authenticate
    if res.fetchall() == []:
        print(f'phone number {From} is not registered with sms-tweet')
        # respond with auth link
        # TODO: change to prod link
        link = f'http://localhost:80/auth?phone={phone}'
        # link = f'https://smstweet.org/auth?phone={From}'
        msg = '''
            Use the following link to authenticate with Twitter. Authenticating also opts in to allowing sms-tweet to message this device. 
            Communications from sms-tweet will only be essential updates and will never include promotional or marketing material. 
            Text \STOP to opt out at any time. Link: {link}
        '''
        response.message(f'msg')
        # return Response(content=str(response), media_type="application/xml")
    # returning user, attempt to tweet their message
    await tweet(Body, phone)

async def tweet(msg, phone):
    # get bearer token, use refresh, handle failure, etc
    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    query = 'SELECT * FROM users WHERE phone = ?'
    res = cur.execute(query, [phone])
    # record is tuple of (phone, bearer, bearer_exp, refresh, refresh_exp)
    record = res.fetchone() 

    # refresh token expired, need to reauth
    if now > record[4]:
        # TODO: reroute to auth endpoint         
        return
    # bearer token expired, use refresh token to get a new one
    if now > record[2]:
        auth = f'{cid}:{secret}'
        encoded = base64.b64encode(auth.encode('utf-8')).decode('utf-8')
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {encoded}'
        }
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': record[3],
        }

        response = requests.post(
            'https://api.x.com/2/oauth2/token',
            headers=headers,
            data=data
        )
        if response.status_code != 200:
            print(f'error: {response.json()}')
            # TODO: reroute to /auth to attempt to recover
            return
        tokens = (response.json()['access_token'], response.json()['refresh_token'])
        # TODO: update db with new bearer, refresh tokens
        query = 'DELETE FROM users WHERE phone = ?'
        cur.execute(query, [phone])
        # insert new user
        query = "INSERT INTO users VALUES (?, ?, DATETIME(CURRENT_TIMESTAMP, '+2 hours'), ?, DATETIME(CURRENT_TIMESTAMP, '+6 months'))"
        cur.execute(query, [phone, tokens[0], tokens[1]])
        con.commit()
        res = cur.execute("SELECT * FROM users")
        for s in res.fetchall():
            print(s)
    
    # send tweet
    query = 'SELECT * FROM users WHERE phone = ?'
    res = cur.execute(query, [phone])
    # record is tuple of (phone, bearer, bearer_exp, refresh, refresh_exp)
    record = res.fetchone() 
    bearer = record[1]
    url = 'https://api.twitter.com/2/tweets'

    headers = {
        'Authorization': f'Bearer {bearer}',
        'Content-Type': 'application/json',
    }

    payload = {
        'text': f'{msg}'
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 201:
        print('Tweet posted successfully!')
        print('Response:', response.json())
    else:
        print(f'Failed to post tweet. Status code: {response.status_code}')
        print('Error:', response.json())

