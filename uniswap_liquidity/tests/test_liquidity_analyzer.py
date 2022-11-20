import os
import subprocess
import unittest
from web3 import Web3
from uniswap_liquidity.uni_v3_pool import V3LiquidityPool
from uniswap_liquidity.liquidity_analyzer import get_tokens_to_target_price, sqrt_x96_price_to_sqrt_price
from uniswap_liquidity.uni_v3_router_abi import UNI_V3_ROUTER_ABI
from uniswap_liquidity.erc20_abi import ERC_20_SIMPLE_ABI
import json
import time

ETHEREUM_RPC_URL = os.environ.get("ETHEREUM_RPC_URL")
DAI_ETH_POOL_ADDRESS = "0xC2e9F25Be6257c210d7Adf0D4Cd6E3E881ba25f8"
V3_ROUTER_ADDRESS = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
WETH_ADDRESS="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

class TestLiquidityAnalyzer(unittest.TestCase):
    def setUp(self) -> None:
        print(ETHEREUM_RPC_URL)
        self.process = subprocess.Popen(
            [
                "ganache-cli",
                "--fork",
                f"{ETHEREUM_RPC_URL}@15737814",
                "--account_keys_path",
                "uniswap_liquidity/tests/keys.json",
                "--defaultBalanceEther",
                "100000",
            ],
            stdout=subprocess.PIPE,
        )
        while True:
            line = str(self.process.stdout.readline())

            if "error" in line.lower():
                raise RuntimeError(f"Could not fork mainnet: {line}")
            if "RPC Listening on" in line:
                break

        self.provider = Web3.HTTPProvider("http://localhost:8545")
        self.w3 = Web3(self.provider)

        with open("uniswap_liquidity/tests/keys.json") as f:
            d = json.load(f)

        self.account: str = self.w3.toChecksumAddress(
            list(d["private_keys"].items())[0][0]
        )
        self.private_key: bytes = self.w3.toBytes(
            hexstr=list(d["private_keys"].items())[0][1]
        )
        
        print(f"balance of account: {self.w3.eth.get_balance(self.account)}")

        self.router = self.w3.eth.contract(V3_ROUTER_ADDRESS, abi=UNI_V3_ROUTER_ABI)
        self.weth_contract = self.w3.eth.contract(WETH_ADDRESS, abi=ERC_20_SIMPLE_ABI)

        nonce = self.w3.eth.getTransactionCount(self.account)
        deposit = self.weth_contract.functions.deposit().build_transaction({"from": self.account, "value": 10000*10**18, "nonce": nonce})
        signed_deposit = self.w3.eth.account.sign_transaction(deposit, private_key=self.private_key)
        self.w3.eth.send_raw_transaction(signed_deposit.rawTransaction)

    def tearDown(self) -> None:
        self.process.kill()

    def test_liquidity_analyzer(self):
        dai_eth_pool = V3LiquidityPool(DAI_ETH_POOL_ADDRESS, self.w3)
        token = self.w3.eth.contract(dai_eth_pool.token1, abi=ERC_20_SIMPLE_ABI)
        print(f"Weth Balance: {token.caller.balanceOf(self.account)}")
        _approve_token(self.w3, token, self.router.address, self.account, self.private_key)

        current_sqrt_price = sqrt_x96_price_to_sqrt_price(dai_eth_pool.sqrt_price_x96)
        print(f"current sqrt price: {current_sqrt_price}")

        target_sqrt_price = current_sqrt_price * 1.02
        amount_out = get_tokens_to_target_price(dai_eth_pool, target_sqrt_price)
        params = (
            dai_eth_pool.token1,
            dai_eth_pool.token0,
            dai_eth_pool.fee,
            self.account,
            int(time.time()) + 10 * 60,
            int(amount_out),
            10**30,
            0,
        )
        print(params)
        nonce = self.w3.eth.getTransactionCount(self.account)
        tx = self.router.functions.exactOutputSingle(params).build_transaction({"from": self.account, "value": 0, "nonce": nonce})
        print(tx)
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.private_key)
        self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        dai_eth_pool.update()
        new_sqrt_price = sqrt_x96_price_to_sqrt_price(dai_eth_pool.sqrt_price_x96)
        self.assertAlmostEqual(new_sqrt_price, target_sqrt_price, places=8)

def _approve_token(w3, token, spender_address, account, private_key):

    nonce=w3.eth.get_transaction_count(account)
    tx = token.functions.approve(spender_address, Web3.toWei(2**64-1,'ether')).build_transaction({"from": account, "nonce": nonce})
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
    res = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    print("Approved transaction: ", res.hex())
    return tx

"""
    {
        "tokenIn": dai_eth_pool.token1,
        "tokenOut": dai_eth_pool.token0,
        "fee": dai_eth_pool.fee,
        "recipient": self.account,
        "deadline": 9999999999999999,
        "amountOut": amount_out,
        "amountInMaximum": 0,
        "sqrtPriceLimitX96": 0,
    },
"""