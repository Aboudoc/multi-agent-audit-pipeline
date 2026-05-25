// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Intentionally vulnerable example for the demo pipeline.
/// Contains a textbook reentrancy and a textbook access-control bug.
/// Do NOT use this anywhere real.
contract Vault {
    address public owner;
    mapping(address => uint256) public balances;

    constructor() {
        owner = msg.sender;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // BUG (reentrancy): sends ETH out BEFORE zeroing the balance, so a malicious
    // receiver can re-enter withdraw() and drain the contract.
    function withdraw() external {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "nothing to withdraw");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
        balances[msg.sender] = 0;
    }

    // BUG (access control): no owner check — anyone can seize ownership.
    function setOwner(address newOwner) external {
        owner = newOwner;
    }

    // Note for the integer-overflow agent: this is Solidity 0.8, so the `+` in
    // deposit() reverts on overflow by default. There is no arithmetic bug here —
    // a correct agent should return nothing.
}
