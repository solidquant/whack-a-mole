# Whack-A-Mole

<p align="center">
    <img src = "https://github.com/solidquant/whack-a-mole/assets/134243834/841a91df-728b-489b-b4af-4af948c03c35" width="450px">
</p>

The image is of Dugtrio from Pokemon.

*And the banner is... Pokemon. I'm a Pokemon fan, what more can I say?*

---

### What the heck?

Whack-A-Mole is a CEX-DEX arbitrage bot written in Python.

Arbitrage strategies are like the global Whack-A-Mole game played in parallel.

Multiple players participate to find the mole that pops up, and jump to capture that opportunity.

Who knows who'll win...

What we know for certain is that you'll need a fast pair of eyes on the market at all times,
and an extra fast execution engine to capture the moment without latency.

Will our beloved Python be able to accomplish this? We'll see 😎

### Example Strategy #1: DEX arbitrage

The **main** branch is likely to go through a lot of changes, so to run an example that runs without breaking,
you should switch to the **examples/strategy/dex_arb_base** branch before running **main.py**. Run:

```
git checkout examples/strategy/dex_arb_base
```

### Example Strategy #2: CEX-DEX arbitrage

#### You said this is a CEX-DEX arbitrage bot, where the f is it?

I know...🥲 I'm still actively researching the CEX-DEX arbitrage space.

Everyone interested in the process can go visit my other repository which is actually a derivative of Whack-A-Mole:

https://github.com/solidquant/cex-dex-arb-research

This research template is an attempt to find alphas within the crypto space.

You can focus on DEX only arbs, CEX only arbs, and also CEX-DEX arbs using this template.

### 🛠 Recent Updates (2023.08.08):

1. **asyncio error**: added nest_asyncio
2. **.env error**: added some randomly generated sample private keys, addresses for people that want a complete testing environment
3. **requirements.txt**: web3, flashbots, websockets often times have conflicting versions. You sometimes need to delete their fields in the requirements.txt file and install them manually
4. **Telegram bot**: updated the code so that the bot runs without having to set the Telegram token in .env

Now with these issues resolved, you can easily test this bot out. It is set to debug, and the private keys are set at random,
so you don't need to worry! Just run:

```python
import asyncio
import nest_asyncio

from strategies.dex_arb_base import main


if __name__ == '__main__':
    nest_asyncio.apply()
    asyncio.run(main())
```

This code is in **main.py**.

```bash
python main.py
```

---

Check out my blog post describing in detail what this project attempts to do, and how you can use it.

[Go to blog 👉](https://medium.com/@solidquant/how-i-built-my-first-mev-arbitrage-bot-introducing-whack-a-mole-66d91657152e)

---

⚡️ For readers that want to talk about MEV and any other quant related stuff with people, please join my Discord! There’s currently no one on the Discord server, so it’s not too active yet, but I hope to meet new people there! 🌎🪐

https://discord.gg/jjTa8vkP