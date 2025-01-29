# smstweet: rebuilding Twitter via SMS

### about

smstweet is intended for moments where you want to tweet a quick thought without being bombarded by your timeline. this service supports sending tweets by messaging an sms number. **this service is currently unavailable. i was not able to receive twilio verification so the sms number is not operational**.

### architecture

message sending/receiving is handled by twilio's sms api. twitter's api is used for authentication and tweeting. oauth2.0 is used for authentication, and credentials are stored in a sqlite database.

### example usage

1. message 'tweet' to the service's phone number
2. the service responds with a link for authentication
3. upon successful authentication, any subsequent messages sent to the number will be tweeted
4. the service responds with success/failure notifications after attempting to send a tweet
