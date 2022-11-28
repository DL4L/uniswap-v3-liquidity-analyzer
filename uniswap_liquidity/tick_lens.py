from abc import ABC, abstractmethod
from uniswap_liquidity.abi.tick_lens_abi import TICK_LENS_ABI
from web3 import Web3


class TickLens(ABC):
    def __init__(
        self,
        w3: Web3, 
        address="0xbfd8137f7d1516D3ea5cA83523914859ec47F573",
    ):

        try:
            self._tick_lens_contract = w3.eth.contract(address=address, abi=TICK_LENS_ABI)
        except:
            raise RuntimeError(f"Could not create TickLens contract for {address}")