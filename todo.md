# planning

### sms

sms flow (2 cases)
1. returning user: tweet whatever they message
    - respond with confirmation, '<tweet>' has been succesfully tweeted
    - respond with error message
        - issue with tweet sending (not auth related)
        - issue with auth (refresh token no longer valid)
            - catch this case, treat as new user and have them reauthenticate with twitter (keep db in valid state, do not incorrectly update/insert new creds) 
2. new user
    - regardless of what their first message is, send them auth link in form of `https://smstweet.org/auth/?phone=<phone_number>`
    - success: message that auth is successful, any subsequent messages will be tweeted
    - failure: auth failed, message again to try again

special commands
- escape sequences to allow user actions once authenticated (STOP, invalidate auth tokens, delete user from db)

handling invalid phone numbers
- if user navigates to /auth and passes an invalid phone number, how to failure when trying to message invalid number?
- requests to this endpoint should be limited to those coming from sms referrals
    - generate code and add to auth url: check if this code 

links in sms messages
- does link need `https://` in the beginning?
    - `https://smstweet.org/auth?phone=<phone>`
    - `smstweet.org/auth?phone=<phone>`

#### twilio

offload sms server
- cost: number is $2/month, each message is $0.008
- **much more affordable and simple than self hosted gateway**

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

character limit: check length of tweet before attempting to send to twitter api
- does sms have a limit that will effect this too or no? 
    - i assume an sms message has a limit but twilio will handle messages over that limit by splitting and reconstructing
- return which part of message was within limit

threads
- special command to start thread, each subsequent message is treated as a part of the thread until an ending command is sent
    - check if each tweet in thread is within character limit
- does twitter api have a way of handling/creating threads?
    

[twitter docs example](https://github.com/xdevplatform/Twitter-API-v2-sample-code/blob/main/Manage-Tweets/create_tweet.py)
- tweeting images or link previews? special ways to handle this over sms?


### sqlite

schema: phone (primary key), bearer token, bearer expiration, refresh token, refresh expiration

### docker

networking
- keep using port 80? 
-how to point fastapi to the actual network interface and not localhost?

volume mounts
- persist db file across container lifetimes

### tech debt

- split main.py into multiple files 
    - tweeting, auth, sms, server config can be in separate files
- move all html into templates
- move common operations into functions (especially db)
    - insert new record
    - delete record with given phone number
    - select based on phone
    - print db state
- handle proxy myself, stop using cloudflare

### optimization

- reverse proxy: throw out /wordpress and /wp-admin requests (and other spam/attack requests)
- load testing, scaling, reverse proxy for sms vs auth


