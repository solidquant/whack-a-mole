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

    def __init__(self):
        self.client = InfluxDBClientAsync(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG
        )
        self.write_api = self.client.write_api()

    async def send(self, measurement: str, data: Dict[str, float]):
        points = [
            Point(measurement).field(k, v)
            for k, v in data.items()
        ]
        await self.write_api.write(
            bucket=INFLUXDB_BUCKET,
            org=INFLUXDB_ORG,
            record=points
        )

    async def close(self):
        await self.client.close()


async def test_send():
    influxdb = InfluxDB()
    await influxdb.send('test', {'data1': 1, 'data2': 2})
    await influxdb.close()


if __name__ == '__main__':
    import asyncio

    asyncio.run(test_send())
