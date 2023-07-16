import os
from typing import Dict
from dotenv import load_dotenv
from influxdb_client import Point
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

load_dotenv(override=True)

INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_URL = os.getenv('INFLUXDB_URL')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET')


class InfluxDB:
    """
    Used to collect real-time data from bot.
    If all init args are None, InfluxDB won't do anything.
    """

    def __init__(self,
                 token: str = INFLUXDB_TOKEN,
                 url: str = INFLUXDB_URL,
                 org: str = INFLUXDB_ORG,
                 bucket: str = INFLUXDB_BUCKET):

        self.token = token
        self.url = url
        self.org = org
        self.bucket = bucket

        if token:
            self.client = InfluxDBClientAsync(
                url=url,
                token=token,
                org=org
            )
            self.write_api = self.client.write_api()
        else:
            self.client = None
            self.write_api = None

    async def send(self, measurement: str, data: Dict[str, float]):
        if self.write_api:
            points = [
                Point(measurement).field(k, v)
                for k, v in data.items()
            ]
            await self.write_api.write(
                bucket=self.bucket,
                org=self.org,
                record=points
            )

    async def close(self):
        if self.client:
            await self.client.close()


async def test_send():
    influxdb = InfluxDB()
    await influxdb.send('test', {'data1': 1, 'data2': 2})
    await influxdb.close()


if __name__ == '__main__':
    import asyncio

    asyncio.run(test_send())
