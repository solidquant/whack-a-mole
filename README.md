# Whack-A-Mole

<p align="center">
    <img src = "https://github.com/solidquant/whack-a-mole/assets/134243834/841a91df-728b-489b-b4af-4af948c03c35" width="450px">
</p>

The image is of Dugtrio from Pokemon.

### What the heck?

Whack-A-Mole is a CEX-DEX arbitrage bot written in Python.

Arbitrage strategies are like the global Whack-A-Mole game played in parallel.

Multiple players participate to find the mole that pops up, and jump to capture that opportunity.

Who knows who'll win...

What we know for certain is that you'll need a fast pair of eyes on the market at all times,
and an extra fast execution engine to capture the moment without latency.

Will our beloved Python be able to accomplish this? We'll see 😎

### Example Strategy #1: DEX Arbitrage Base

This branch has an example strategy that supports DEX arbitrages.

The smart contracts for WhackAMoleBotV1 and SimulatorV1 can be found in **contracts/src**.

```bash
forge compile
```

Running the above Foundry forge command will compile the contracts for you creating an "out" directory.

The starting point for this example is "main.py" file.

```python
import asyncio

from strategies.dex_arb_base import main


if __name__ == '__main__':
    asyncio.run(main())
```

Running this code will run the main function in **strategies/dex_arb_base.py**.

Before running though, make sure to check whether you have your .env file setup correctly.

```bash
ETHEREUM_HTTP_RPC_URL=
POLYGON_HTTP_RPC_URL=
ARBITRUM_HTTP_RPC_URL=

ETHEREUM_WS_RPC_URL=
POLYGON_WS_RPC_URL=
ARBITRUM_WS_RPC_URL=

INFLUXDB_TOKEN=
INFLUXDB_URL=
INFLUXDB_ORG=
INFLUXDB_BUCKET=

FLASHBOTS_SIGNING_KEY=
FLASHBOTS_PRIVATE_KEY=

BLOCKNATIVE_TOKEN=

TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=

ETHEREUM_BOT_ADDRESS=
ETHEREUM_SIMULATOR_ADDRESS=
```

This example runs on Ethereum only, so filling in the required variables for Ethereum
related fields will do the trick. And the usage of InfluxDB and Telegram are optional.

If you leave the fields blank, it'll simply ignore InfluxDB/Telegram.

However, this example uses Blocknative's gas estimator service, thus, the "BLOCKNATIVE_TOKEN" field
is necessary.