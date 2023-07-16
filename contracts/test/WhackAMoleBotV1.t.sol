// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.9;

import "forge-std/Test.sol";
import "../src/WhackAMoleBotV1.sol";
import "../src/SimulatorV1.sol";

contract FoundryDemoTest is Test {
    WhackAMoleBotV1 bot;
    SimulatorV1 simulator;

    uint256 simulatedAmountOut1;
    uint256 simulatedAmountOut2;
    uint256 simulatedAmountOut3;

    function setUp() public {}

    function testBotDeploy() public {
        bot = new WhackAMoleBotV1();
    }

    function testSimulatorDeploy() public {
        simulator = new SimulatorV1();
    }
}
