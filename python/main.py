from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, Response, PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from twilio.Rest import Client
from datetime import datetime
import secrets
import pkce
import requests
import base64
import json

from db import setup, close, insert, delete, select, print_db

app = FastAPI()

@app.on_event('startup')
def on_startup():
    f = open('python/creds.txt').readlines()
    global cid, secret, sid, token
    # twitter creds
    cid = f[0].strip()
    secret = f[1].strip()
    # twilio creds
    sid = f[2].strip()
    token = f[3].strip()
    global client
    client = Client(sid, token)

    global code_verifier, code
    code_verifier, code = pkce.generate_pkce_pair()

    global global_state
    global_state = {}

    global auth_code
    auth_code = {}

    setup()

@app.on_event('shutdown')
def on_shutdown():
    close()

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

@app.get('/terms', response_class=HTMLResponse)
async def terms():
    terms_file = open('templates/terms.html')
    return terms_file.read()

@app.get('/privacy', response_class=HTMLResponse)
async def privacy():
    privacy_file = open('templates/privacy.html')
    return privacy_file.read()
    

@app.get('/auth', response_class=HTMLResponse)
async def auth(phone: str | None = None, phone_code: str | None = None):
    if phone is None:
        return '''
        <head>
            <title>tweet via sms</title>
        </head>
        <body>
            <p>no phone number provided for auth</p>
        </body>
        '''
    if phone not in auth_code or auth_code[phone] != phone_code:
        return '''
        <head>
            <title>tweet via sms</title>
        </head>
        <body>
            <p>unable to authenticate. please sign up by messaging 'tweet' to (218) 319-7248</p>
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
        <p>by authenticating with twitter, you opt in to receiving messages from smstweet</p>
        <p>click <a href='https://smstweet.org/terms'>here</a> to read the terms and conditions of smstweet</p>
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
        # TODO: change to prod url
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
    
        delete(phone)
        insert(phone, bearer, refresh)
        print_db()
        msg = '''
            You have successfully authenticated with Twitter, and also opted in to receiving messages from smstweet. 
            Messages from smstweet will only be sent as replies to your own messages, such as replying with success or failure of an attempted tweet. 
            Messages will never be promotional. For help, email willshuttle21@gmail.com. To opt out from these messages, please message 'STOP'. Message and data rates may apply.
        '''
        try:
            # TODO: uncomment below once number is approved
            '''
            message = client.messages.create(
                body=msg,
                from_='+12183197248'
                to=phone='+' + phone
            )
            print(f'auth confirmation sent to {phone}')
            '''
            return '<p>successfully authenticated</p>'
        except Exception as e:
            print(f'failed to send auth confirmation to {phone}: {e}')

@app.post('/sms', response_class=Response)
async def sms(Body: str = Form(...), From: str = Form(...)):
    # TODO: change webhook to prod value in twilio console
    #   https://smstweet.org/sms
    # TODO: uncomment all replies
    phone = From[1:]
    response = MessagingResponse()
    if len(body) > 280:
        response.message(f'Your message exceeds the Twitter character limit. \'{Body[280:]}\' exceeds the limit')
        # return Response(content=str(response), media_type="application/xml")

    # STOP message, delete user and their keys from db
    if Body == 'STOP':
        # remove user and their tokens from db
        delete(phone)
        response.message('You have successfully unsubscribed from smstweet')
        # return Response(content=str(response), media_type="application/xml")

    s = secrets.token_urlsafe(7)
    auth_code[phone] = s
    link = f'https://smstweet.org/auth?phone={phone}&phone_code={s}'
    print(f'received message: {Body} from {phone}')

    ret = select(phone)
    # new phone, authenticate
    if ret == None:
        print(f'phone number {From} is not registered with smstweet')
        # respond with auth link
        msg = f'''
            Use the following link to authenticate with Twitter. Authenticating also opts in to allowing smstweet to message this device. 
            Communications from smstweet will only be essential updates and will never include promotional or marketing material. 
            Text STOP to opt out at any time. Link: {link}
        '''
        response.message(f'msg')
        print(link)
        return
        # return Response(content=str(response), media_type="application/xml")
    # returning user, attempt to tweet their message
    ret = await tweet(Body, phone)
    # ret values
    #   -1: auth error, redirect to auth again
    #    0: tweet successful
    #    1: error tweeting
    if ret == -1:
        response.message(f'error, please reauthenticate: {link}')
    elif ret == 0:
        response.message(f"'{Body}' was tweeted successfully")
    elif ret == 1:
        response.message(f'error, could post tweet')
    # return Response(content=str(response), media_type="application/xml")

async def tweet(msg, phone):
    # record is tuple of (phone, bearer, bearer_exp, refresh, refresh_exp)
    record = select(phone)
    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # refresh token expired, need to reauth
    if now > record[4]:
        return -1
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
            return -1
        tokens = (response.json()['access_token'], response.json()['refresh_token'])
        # delete any old instances and insert new one
        delete(phone)
        insert(phone, tokens[0], tokens[1])
        print_db()
    
    # send tweet
    record = select(phone)
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
        print('tweet successful, response:', response.json())
        return 0
    else:
        print(f'tweet failed {response.status_code} error: {response.json()}')
        return 1
