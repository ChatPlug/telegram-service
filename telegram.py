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
        with open('config.' + self.access_token + '.json', 'w') as outfile:
            json.dump({'botToken': conf['fieldValues'][0]}, outfile)
        await self.init_bot()

    async def on_connected(self):
        if not os.path.exists('config.' + self.access_token + '.json'):
            await self.subscribe_configuration(conf_fields)
        else:
            await self.init_bot()

    async def init_bot(self):
        self.user_photos = {}

        config = self.get_config()
        self.bot = Bot(token=config["botToken"])
        self.dp = Dispatcher(self.bot)
        self.dp.register_message_handler(self.handleTelegramMessage, content_types=[
                                         types.ContentType.PHOTO, types.ContentType.TEXT, types.ContentType.STICKER])
        await self.dp.start_polling()

    async def handleTelegramMessage(self, message):
        print(message)
        # Cache user profile images
        if not str(message["from"]["id"]) in self.user_photos:
            pics = await self.bot.get_user_profile_photos(message["from"]["id"])
            file = await self.bot.get_file(pics["photos"][0][-2]["file_id"])
            file_path = self.bot.get_file_url(file["file_path"])
            self.user_photos[str(message["from"]["id"])] = file_path

        attachments = []
        # Handle photos
        if "photo" in message: # message["photo"] != null 
            file = await self.bot.get_file(message["photo"][-1]["file_id"])
            file_path = self.bot.get_file_url(file["file_path"])
            attachments = [{
                "sourceUrl": file_path,
                "type": "IMAGE",
                "originId": message["photo"][-1]["file_id"], 
            }]

        # Handle stickers
        if "sticker" in message: # message["sticker"] != null 
            file = await self.bot.get_file(message["sticker"]["file_id"])
            file_path = self.bot.get_file_url(file["file_path"])
            attachments = [{
                "sourceUrl": file_path,
                "type": "IMAGE",
                "originId": message["sticker"]["file_id"], 
            }]

        await self.send_message(
            message["text"] or "",  # body
            str(message["message_id"]),  # originId
            str(message["chat"]["id"]),  # originThreadId
            message["from"]["username"],  # author.username
            str(message["from"]["id"]),  # author.originId
            self.user_photos[str(message["from"]["id"])],  # author.avatarUrl
            attachments  # attachments
        )

    def get_config(self):
        with open('config.' + self.access_token + '.json') as json_file:
            data = json.load(json_file)
            return data


cp = TelegramService(
    os.environ["ACCESS_TOKEN"], os.environ["WS_ENDPOINT"], os.environ["HTTP_ENDPOINT"])

loop = asyncio.get_event_loop()
loop.run_until_complete(cp.connect())
loop.close()
