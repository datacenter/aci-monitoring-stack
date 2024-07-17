# Webex How To


- Create a new Webex Space

## Create a Bot
- Go to: https://developer.webex.com/my-apps
- Create a new Bot
- (Re)generate Access Token: This the token you set in the `credentials` field of Alertmanager config for Webex
- Add the Bot to the Webex Space
    - Go to People
    - Add People
    - Search the name of your Bot

## Get you Space/Room ID:

- Go to https://developer.webex.com/docs/api/v1/rooms/list-rooms
- Disable: `Use personal access token` otherwise we are gonna retrieve ALL the rooms...  
- In `Bearer` paste the Access Token generated in the previous step
- You should see 1 or 2 rooms, find the one with the right name and copy the `id` in the `room_id` field of Alertmanager config for Webex

