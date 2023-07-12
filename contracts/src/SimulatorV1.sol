// SPDX-License-Identifier: MIT
pragma solidity ^0.8.9;

import "openzeppelin-contracts/contracts/utils/math/SafeMath.sol";

import "./protocols/uniswap/UniswapV2Library.sol";
import "./protocols/uniswap/IQuoterV2.sol";

contract SimulatorV1 {
    using SafeMath for uint256;

    struct SwapParams {
        uint8 protocol; // 0 (UniswapV2), 1 (UniswapV3), 2 (Curve Finance)
        address factoryQuoter;
        address pool; // used in Curve Finance
        address tokenIn;
        address tokenOut;
        uint24 fee; // only used in Uniswap V3
        uint256 amount; // amount in (1 USDC = 1,000,000 / 1 MATIC = 1 * 10 ** 18)
    }

    constructor() {}

    function simulateSwapIn(
        SwapParams[] memory paramsArray
    ) public returns (uint256) {
        uint256 amountOut = 0;

        for (uint256 i; i < paramsArray.length - 1; ) {
            SwapParams memory params = paramsArray[i];

            if (amountOut == 0) {
                amountOut = params.amount;
            } else {
                params.amount = amountOut;
            }

            if (params.protocol == 0) {
                amountOut = simulateUniswapV2SwapIn(params);
            } else if (params.protocol == 1) {
                amountOut = simulateUniswapV3SwapIn(params);
            }

            unchecked {
                i++;
            }
        }

        return amountOut;
    }

    function simulateUniswapV2SwapIn(
        SwapParams memory params
    ) public view returns (uint256 amountOut) {
        (uint reserveIn, uint reserveOut) = UniswapV2Library.getReserves(
            params.factoryQuoter,
            params.tokenIn,
            params.tokenOut
        );
        amountOut = UniswapV2Library.getAmountOut(
            params.amount,
            reserveIn,
            reserveOut
        );
    }

    function simulateUniswapV3SwapIn(
        SwapParams memory params
    ) public returns (uint256 amountOut) {
        IQuoterV2 quoter = IQuoterV2(params.factoryQuoter);
        IQuoterV2.QuoteExactInputSingleParams memory quoterParams;
        quoterParams.tokenIn = params.tokenIn;
        quoterParams.tokenOut = params.tokenOut;
        quoterParams.amountIn = params.amount;
        quoterParams.fee = params.fee;
        quoterParams.sqrtPriceLimitX96 = 0;
        (amountOut, , , ) = quoter.quoteExactInputSingle(quoterParams);
    }
}
