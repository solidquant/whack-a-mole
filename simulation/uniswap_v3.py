import numpy as np


class UniswapV3Simulator:
    """
    For the time being, V3 simulator limits swap simulations to
    single tick swaps for simplicity

    This is a design to enforce less price impact on swap actions.
    It also makes sense to limit swaps to single tick swaps, because that is how
    arbitrage/market making is done in most cases using limit orders.

    Strategies don't utilize market orders (in the case of CEXs) or multi-tick swaps
    that much when slippage is an important factor in profitability.

    TODO: Add TickMap and TickMath to support simulation of multi-tick swaps
    However, I mark this as TODO.
    Market orders / Multi-tick swaps can help to increase order size and reduce leg outs,
    so this is a feature that should be implemented in the future.

    * Reference: https://blog.uniswap.org/uniswap-v3-math-primer
    """

    def __init__(self):
        pass

    def sqrtx96_to_price(self,
                         sqrtx96: float,
                         decimals0: int,
                         decimals1: int,
                         token0_in: bool):
        """
        Returns the quote price of buying token_out with 1 token_in

        - token_in_is_token0 == true: price of buying token1 with 1 token0
        - token_in_is_token1 == false: price of buying token0 with 1 token1
        """
        price = ((sqrtx96 / (2 ** 96)) ** 2) * (10 ** (decimals0 - decimals1))
        return price if token0_in else 1 / price

    def tick_to_price_range(self,
                            current_tick: float,
                            tick_spacing: float,
                            decimals0: float,
                            decimals1: float,
                            token0_in: bool):
        """
        Returns the tick price range of a single tick
        """
        lower_tick = tick_spacing * (current_tick // tick_spacing)
        upper_tick = tick_spacing * (current_tick // tick_spacing + 1)
        ticks = np.array([lower_tick, upper_tick])
        tick_range = 1.0001 ** ticks
        price_range = tick_range * (10 ** (decimals0 - decimals1))
        return price_range if token0_in else (1 / price_range)[::-1]

    def get_amount_out(self):
        pass

    def get_amount_in(self):
        pass



if __name__ == '__main__':
    pass