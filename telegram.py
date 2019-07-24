from client import ChatPlugService
import os
import asyncio
import json
from aiogram import Bot, Dispatcher, executor, types

_loop = asyncio.get_event_loop()

conf_fields = [{'type': 'STRING', 'hint': 'Your telegram bot token',
                            'defaultValue': '', 'optional': False, 'mask': True}]

class TelegramService(ChatPlugService):
    async def on_message_received(self, msg):
        message = msg["message"]
        target_id = msg["targetThreadId"]
        await self.bot.send_message(int(target_id), "*" + message["author"]["username"] + "*: " + message["body"], parse_mode="Markdown")
        for attachment in message["attachments"]:
            await self.bot.send_photo(int(target_id), attachment["sourceUrl"])
    
    async def on_configuration_received(self, conf):
        with open('config.' + self.instance_id + '.json', 'w') as outfile:
            json.dump({'botToken': conf['fieldValues'][0]}, outfile)
        await self.init_bot()

    async def on_connected(self):
        if not os.path.exists('config.' + self.instance_id + '.json'):
            await self.subscribe_configuration(conf_fields)
        else:
            await self.init_bot()

    async def init_bot(self):
        self.user_photos = {}

        config = self.get_config()
        self.bot = Bot(token=config["botToken"])
        self.dp = Dispatcher(self.bot)
        self.dp.register_message_handler(self.handleMessage)
        await self.dp.start_polling()
    
    async def handleMessage(self, message):
        if not str(message["from"]["id"]) in self.user_photos:
            pics = await self.bot.get_user_profile_photos(message["from"]["id"])
            file = await self.bot.get_file(pics["photos"][0][-2]["file_id"])
            file_path = self.bot.get_file_url(file["file_path"])
            self.user_photos[str(message["from"]["id"])] = file_path

        await self.send_message(
            message["text"],
            str(message["message_id"]), 
            str(message["chat"]["id"]), 
            message["from"]["username"], 
            str(message["from"]["id"]), 
            self.user_photos[str(message["from"]["id"])], [])
        print(message)


    def get_config(self):
        with open('config.' + self.instance_id + '.json') as json_file:
            data = json.load(json_file)
            return data

cp = TelegramService(os.environ["INSTANCE_ID"], os.environ["WS_ENDPOINT"], os.environ["HTTP_ENDPOINT"])

loop = asyncio.get_event_loop()
loop.run_until_complete(cp.connect())
loop.close()