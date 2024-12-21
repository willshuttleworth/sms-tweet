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
    - regardless of what their first message is, send them auth link in form of `https://<domain.xyz>/auth/?phone=<phone_number>`
    - success: message that auth is successful, any subsequent messages will be tweeted
    - failure: auth failed, message again to try again

special commands
- escape sequences to allow user actions once authenticated (\STOP, invalidate auth tokens, delete user from db)

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

[twitter docs example](https://github.com/xdevplatform/Twitter-API-v2-sample-code/blob/main/Manage-Tweets/create_tweet.py)
- tweeting images or link previews? special ways to handle this over sms?

### sqlite

schema: phone (primary key), bearer token, bearer expiration, refresh token, refresh expiration

operations
- userExists: is there a record for a specific phone number?
    - called whenever a user messages
- bearerValid
    - called when attempting to tweet
- refreshValid
    - called when attempting to tweet **and** bearer token is expired
- addCreds: add newly acquired bearer and refresh tokens to db
    - delete old record (to confirm that primary key constraint wont be violated and only one set of tokens will exist for a given user)
    - insert new record

### docker

networking
- keep using port 80? 
-how to point fastapi to the actual network interface and not localhost?

volume mounts
- persist db file across container lifetimes



