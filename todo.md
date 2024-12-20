# 2 sides: client to sms server, server to twitter api

#### architecture: self hosted on raspberry pi, both sms gateway and tweet server

### sms

server knows which phone number each request is coming from, that serves as auth (for my service)

if server has not seen phone number before
- request oauth creds
- ux? type creds via text (simplest) vs some web ui (hosting? less friction but more complex)
- once creds are received, tell user that they are ready to tweet 

phone number recognized
- read incoming request, map the phone number to the stored oauth creds
- run tweet python code

#### twilio

offload sms server
- cost: number is $2/month, each message is $0.008
- **much more affordable and simple than self hosted gateway**

#### sms gateway

[self hosted sms gateway](https://blog.haschek.at/2021/raspberry-pi-sms-gateway.html)
- need cheap sim and sim dongle for pi (cost?)
- does this guide work with 4g?

### api

##### authorization

user opens get request to [https://x.com/i/authorize]()
- pass my x app's client_id 
- pass redirect url, which is a site hosted by me that checks for valid token generation and informs user of success or failure
- `state` field: randomly generated value ([google example](https://developers.google.com/identity/protocols/oauth2/web-server#python_1)) to verify that the request came from my service
- code_challenge: is this necessary for me? what does it mitigate?

x api responds with auth_code
- use this code to make post request to [https://api.x.com/2/oauth2/token]()
- this request returns the auth token

save auth token to pass with future requests on behalf of this specific user
- when does token need regenerated?
    - handling failures due to invalid/expired token

auth cases:
1. new user, no db entry, authenticate for first time
2. returning user
    1. bearer token valid (only lasts for 2 hours)
        - use bearer token
    2. bearer token expired, refresh token valid
        - use refresh token to request new bearer token
    3. bearer token expired, refresh token expired
        - user my reauthenticate

##### tweeting

[twitter docs example](https://github.com/xdevplatform/Twitter-API-v2-sample-code/blob/main/Manage-Tweets/create_tweet.py)
- tweeting images or link previews? special ways to handle this over sms?

