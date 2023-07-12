class UniswapV2Simulator:

    def __init__(self):
        pass

    def get_amount_out(self,
                       amount_in: float,
                       reserve_in: float,
                       reserve_out: float,
                       fee: float = 3):
        """
        Fee in Uniswap V2 variants are 0.3%
        However, for variants that have different fee rates,
        fee can be overrided
        """
        amount_in_with_fee = amount_in * (1000 - fee)
        numerator = amount_in_with_fee * reserve_out
        denominator = (reserve_in * 1000) + amount_in_with_fee
        return int(numerator / denominator)

    def get_amount_in(self,
                      amount_out: float,
                      reserve_in: float,
                      reserve_out: float,
                      fee: float = 3):

        numerator = reserve_in * amount_out * 1000
        denominator = (reserve_out - amount_out) * (1000 - fee)
        return int(numerator / denominator + 1)


if __name__ == '__main__':
    pass