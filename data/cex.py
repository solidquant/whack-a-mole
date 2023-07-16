import ccxt
from typing import List


class CEX:
    """
    Use CCXT to build CEX execution

    The Python project is a prototype CEX-DEX arb. bot,
    use as much of what others have built already
    """

    def __init__(self, trading_symbols: List[str]):
        self.trading_symbols = trading_symbols


if __name__ == '__main__':
    """
    Test with Binance, OKX, Bybit
    These are the top 3 derivatives exchanges
    """
    from configs import TRADING_SYMBOLS

    cex = CEX(TRADING_SYMBOLS)

    # print(ccxt.exchanges)
    #
    # binance = ccxt.binance({'options': {'defaultType': 'future'}})
    # markets = binance.load_markets()
    # print(markets)