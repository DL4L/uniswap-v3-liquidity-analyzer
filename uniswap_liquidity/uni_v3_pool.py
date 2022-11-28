from abc import ABC, abstractmethod
from uniswap_liquidity.abi.uni_v3_lp_abi import V3_LP_ABI
from uniswap_liquidity.tick_lens import TickLens
from web3 import Web3
from web3.eth import Contract
from typing import List, Tuple, Dict, Optional
class BaseV3LiquidityPool(ABC):
    def __init__(self, address, w3: Web3, tick_lens: Contract = None):
        self.address = address

        try:
            self._pool_contract = w3.eth.contract(
                address=address, abi=V3_LP_ABI
            )
        except:
            raise RuntimeError(f"Could not create contract for {address}")

        if tick_lens:
            self.tick_lens = tick_lens
        else:
            try:
                self.tick_lens = TickLens(w3)
            except:
                raise RuntimeError(f"Could not create TickLens contract")
                
        try:
            self.token0 = self._pool_contract.caller.token0()
            self.token1 = self._pool_contract.caller.token1()
            self.fee = self._pool_contract.caller.fee()
            self.slot0 = self._pool_contract.caller.slot0()
            self.liquidity = self._pool_contract.caller.liquidity()
            self.tick_spacing = self._pool_contract.caller.tickSpacing()
            self.sqrt_price_x96 = self.slot0[0]
            self.tick = self.slot0[1]
            self.tick_data = {}
            self.tick_word, _ = self.get_tick_bitmap_position(self.tick)
            self.get_tick_data_at_word(self.tick_word)
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

    def get_tick_data_at_word(self, word_position: int):
        """
        Gets the initialized tick values at a specific word 
        (a 32 byte number representing 256 ticks at the tickSpacing 
        interval), then stores the liquidity values in the `self.tick_data`
        dictionary, using the tick index as the key.
        """
        try:
            tick_data = self.tick_lens._tick_lens_contract.caller.getPopulatedTicksInWord(
                self.address, word_position
            )
        except:
            raise
        else:
            for (tick, liquidityNet, liquidityGross) in tick_data:
                self.tick_data[tick] = liquidityNet, liquidityGross
            return tick_data

    def get_tick_bitmap_position(self, tick) -> Tuple[int, int]:
        """
        Retrieves the wordPosition and bitPosition for the input tick

        This function corrects internally for tick spacing! 

        e.g. tick=600 is the 11th initialized tick for an LP with 
        tickSpacing of 60, starting at 0.

        Calling `get_tick_bitmap_position(600)` returns (0,10), where:
            0 = wordPosition (zero-indexed)
            10 = bitPosition (zero-indexed)
        """
        tick = tick // self.tick_spacing
        word_index = tick >> 8
        tick_index_in_word = tick % 256
        return word_index, tick_index_in_word

class V3LiquidityPool(BaseV3LiquidityPool):
    pass