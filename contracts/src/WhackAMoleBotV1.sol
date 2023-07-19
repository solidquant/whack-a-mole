// SPDX-License-Identifier: MIT
pragma solidity ^0.8.9;

import "openzeppelin-contracts/contracts/utils/math/SafeMath.sol";
import "openzeppelin-contracts/contracts/token/erc20/IERC20.sol";
import "openzeppelin-contracts/contracts/token/erc20/utils/SafeERC20.sol";

import "./protocols/uniswap/IUniswapV2Router.sol";
import "./protocols/uniswap/IUniswapV3SwapRouter.sol";

// Deployment gas: 1,004,388
contract WhackAMoleBotV1 {
    using SafeERC20 for IERC20;

    address internal immutable owner;

    struct SwapParams {
        uint8 protocol;
        address handler;
        address tokenIn;
        address tokenOut;
        uint24 fee;
        uint256 amount;
    }

    error Unauthorized();
    error TradeFailed();

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        _checkOwner();
        _;
    }

    function _checkOwner() internal view virtual {
        if (msg.sender != owner) {
            revert Unauthorized();
        }
    }

    function recoverTokens(address[] calldata tokens) public payable onlyOwner {
        uint length = tokens.length;

        for (uint i; i < length; ) {
            address token = tokens[i];
            IERC20(token).safeTransfer(
                msg.sender,
                IERC20(token).balanceOf(address(this))
            );

            unchecked {
                ++i;
            }
        }
    }

    // 2 tokens, 2 protocols: 142,582 gas
    function approveHandlers(
        address[] calldata tokens,
        address[] calldata protocols
    ) public payable {
        // Used to allow Routers from Uniswap V2, Uniswap V3, etc.
        // the access to tokens held by this contract
        uint maxInt = type(uint256).max;

        uint tokensLength = tokens.length;
        uint protocolsLength = protocols.length;

        for (uint i; i < tokensLength; ) {
            IERC20 token = IERC20(tokens[i]);
            for (uint j; j < protocolsLength; ) {
                address protocol = protocols[j];
                token.safeApprove(protocol, maxInt);

                unchecked {
                    ++j;
                }
            }

            unchecked {
                ++i;
            }
        }
    }

    function whack(
        SwapParams[] calldata paramsArray,
        uint256 minAmountOut
    ) public payable onlyOwner returns (uint256) {
        uint256 amountOut;
        uint256 paramsArrayLength = paramsArray.length;

        for (uint256 i; i < paramsArrayLength; ) {
            SwapParams memory params = paramsArray[i];

            if (amountOut == 0) {
                amountOut = params.amount;
            } else {
                params.amount = amountOut;
            }

            if (params.protocol == 0) {
                amountOut = uniswapV2Swap(params);
            } else if (params.protocol == 1) {
                amountOut = uniswapV3Swap(params);
            }

            unchecked {
                ++i;
            }
        }

        if (amountOut < minAmountOut) {
            revert TradeFailed();
        }

        return amountOut;
    }

    function uniswapV2Swap(
        SwapParams memory params
    ) internal returns (uint256 amountOut) {
        address[] memory path;
        path = new address[](2);
        path[0] = params.tokenIn;
        path[1] = params.tokenOut;

        uint[] memory amounts = IUniswapV2Router(params.handler)
            .swapExactTokensForTokens(
                params.amount,
                0,
                path,
                address(this),
                block.timestamp
            );

        return amounts[1];
    }

    function uniswapV3Swap(
        SwapParams memory params
    ) internal returns (uint256 amountOut) {
        // Sushiswap V3 doesn't have SwapRouter, needs to reimplement this to use Pools
        ISwapRouter.ExactInputSingleParams memory singleParams = ISwapRouter
            .ExactInputSingleParams({
                tokenIn: params.tokenIn,
                tokenOut: params.tokenOut,
                fee: params.fee,
                recipient: address(this),
                deadline: block.timestamp,
                amountIn: params.amount,
                amountOutMinimum: 0,
                sqrtPriceLimitX96: 0
            });

        amountOut = ISwapRouter(params.handler).exactInputSingle(singleParams);
    }
}
