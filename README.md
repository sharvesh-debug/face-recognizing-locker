# face-recognizing-locker
I builded an face recognized door lock system with real time alerts via telegram bot , which can run on  raspberry pi
hardware component used
raspberry pi 3 B+, solenoid lock (12v),relay module for connecting raspberry pi with solenoid lock, web cam , 12v adopter for solenoid lock , 5v adopter for raspberry pi.
create your own telegram  bot using BotFather copy that token and get your chat id by following steps
 Steps to Get the Chat ID with Your Bot
Send a message to your bot:

Open Telegram and search for your bot (e.g., @YourBotName)

Start the chat and type something (e.g., "hi")

Use Telegram API to fetch updates:

Open your browser and go to this URL:

bash
Copy
Edit
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
🔁 Replace <YOUR_BOT_TOKEN> with your actual bot token (looks like: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11)

Check the JSON response — it will look something like this:

json
Copy
Edit
{
  "ok": true,
  "result": [
    {
      "update_id": 12345678,
      "message": {
        "message_id": 1,
        "from": {
          "id": 123456789,  ← this is YOUR user ID
          "is_bot": false,
          "first_name": "YourName"
        },
        "chat": {
          "id": 123456789, ← this is the **chat ID**
          "first_name": "YourName",
          "type": "private"
        },
        "text": "hi"
      }
    }
  ]
}
✅ So here, "chat": { "id": 123456789 } is your chat ID with the bot.
rplace your token,chat id then the code works
