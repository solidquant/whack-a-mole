import os
import requests
from telegram import Bot
from dotenv import load_dotenv

load_dotenv(override=True)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


class Telegram:

    def __init__(self,
                 token: str = TELEGRAM_TOKEN,
                 chat_id: str or int = TELEGRAM_CHAT_ID):

        self.token = token
        self.chat_id = int(chat_id)

        if token:
            self.bot = Bot(token=self.token)
        else:
            self.bot = None

    def get_updates(self):
        """
        You can call get_updates to get the chat_id
        """
        url = f'https://api.telegram.org/bot{self.token}/getUpdates'
        updates = requests.get(url)
        return updates.json()

    async def send(self, message: str):
        if self.bot:
            await self.bot.sendMessage(chat_id=self.chat_id, text=message)


async def test_send():
    tele = Telegram()
    await tele.send('hello there')


if __name__ == '__main__':
    import asyncio

    asyncio.run(test_send())
