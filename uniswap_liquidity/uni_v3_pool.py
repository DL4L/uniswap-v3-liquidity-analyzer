from abc import ABC, abstractmethod
from uniswap_liquidity.uni_v3_lp_abi import V3_LP_ABI
from web3 import Web3

class BaseV3LiquidityPool(ABC):
    def __init__(self, address, w3: Web3):
        self.address = address

        try:
            self._pool_contract = w3.eth.contract(
                address=address, abi=V3_LP_ABI
            )
        except:
            raise RuntimeError(f"Could not create contract for {address}")

        try:
            self.token0 = self._pool_contract.caller.token0()
            self.token1 = self._pool_contract.caller.token1()
            self.fee = self._pool_contract.caller.fee()
            self.slot0 = self._pool_contract.caller.slot0()
            self.liquidity = self._pool_contract.caller.liquidity()
            self.tick_spacing = self._pool_contract.caller.tickSpacing()
            self.sqrt_price_x96 = self.slot0[0]
            self.tick = self.slot0[1]
        except:
            raise RuntimeError(f"Could not get pool info for {address}")

    def update(self):
        updates = False
        try:
            if (slot0 := self._pool_contract.caller.slot0()) != self.slot0:
                updates = True
                self.slot0 = slot0
                self.sqrt_price_x96 = self.slot0[0]
                self.tick = self.slot0[1]
            if (
                liquidity := self._pool_contract.caller.liquidity()
            ) != self.liquidity:
                updates = True
                self.liquidity = liquidity

        except Exception as e:
            raise RuntimeError(f"Could not update pool info for {self.address}") from e
            
        else:
            return updates, {
                "slot0": self.slot0,
                "liquidity": self.liquidity,
                "sqrt_price_x96": self.sqrt_price_x96,
                "tick": self.tick,
            }


class V3LiquidityPool(BaseV3LiquidityPool):
    pass