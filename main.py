import asyncio
import nest_asyncio

from strategies.dex_arb_base import main


if __name__ == '__main__':
    nest_asyncio.apply()
    asyncio.run(main())
