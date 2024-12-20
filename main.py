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

f = open('python/creds.txt').readlines()
cid = f[0].strip()
secret = f[1].strip()

code_verifier, code = pkce.generate_pkce_pair()

app = FastAPI()

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
    # TODO: query for existence of phone number in db
    #   if exists, return page saying phone number already in use
    #   else, return page with link to twitter oauth

    endpoint = 'https://twitter.com/i/oauth2/authorize'

    client_id = f'client_id={cid}'

    # TODO: change this to prod value and change in twitter dev console
    redir_uri = 'http://localhost:8000/new'
    redir = f'redirect_uri={redir_uri}'

    scope = 'scope=tweet.write+tweet.read+users.read+offline.access'

    # TODO: is this safe with concurrent connections? could multiple state params be in play same time?
    #   could use dict indexed by phone
    global global_state 
    global_state = secrets.token_urlsafe(16) 
    print(global_state)

    # TODO: use prod values for these fields
    code_challenge = f'code_challenge={code}'
    challenge_method = 'code_challenge_method=S256'

    url = f'{endpoint}?response_type=code&{client_id}&{redir}&{scope}&state={global_state}&{code_challenge}&{challenge_method}'
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

    # TODO: verify state, request token with code, write token to db
    if global_state != state:
        print('global: ', global_state, ' returned state: ', state)
        return '<p>error, state values do not match</p>'

    url = 'https://api.twitter.com/2/oauth2/token'
    auth = f'{cid}:{secret}'
    encoded = base64.b64encode(auth.encode("utf-8")).decode("utf-8")
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {encoded}',
    }
    data = {
        'code': f'{code}',
        'grant_type': 'authorization_code',
        'client_id': f'{cid}',
        'redirect_uri': 'http://localhost:8000/new',
        'code_verifier': f'{code_verifier}',
    }
    response = requests.post(url, headers=headers, data=data)
    print(response.headers)
    print(response.text) 
    if response.status_code == 200:
        return '<p>successfully authenticated</p>'
