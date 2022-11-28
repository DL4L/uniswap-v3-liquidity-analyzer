from web3 import Web3
from math import log
from uniswap_liquidity.uni_v3_pool import BaseV3LiquidityPool
from collections import namedtuple

Tick = namedtuple("Tick", "liquidityGross liquidityNet feeGrowthOutside0X128 feeGrowthOutside1X128 tickCumulativeOutside secondsPerLiquidityOutsideX128 secondsOutside initialized")

def get_token_amounts(liquidity, sqrt_price_x96, tick_lower_bound, tick_upper_bound, token0_decimal, token1_decimal):
    sqrt_ratio_a = tick_index_price(tick_lower_bound) ** 0.5
    sqrt_ratio_b = tick_index_price(tick_upper_bound) ** 0.5
    current_tick = log((sqrt_price_x96/2**96)**2)//log(1.0001)
    sqrt_price = sqrt_x96_price_to_sqrt_price(sqrt_price_x96)
    amount0wei = 0
    amount1wei = 0
    if current_tick <= tick_lower_bound:
        amount0wei = liquidity * ((sqrt_ratio_b - sqrt_ratio_a) / (sqrt_ratio_a * sqrt_ratio_b))
    if current_tick > tick_upper_bound:
        amount1wei = liquidity * (sqrt_ratio_b - sqrt_ratio_a)
    if tick_lower_bound <= current_tick < tick_upper_bound:
        amount0wei = liquidity * ((sqrt_ratio_b - sqrt_price) / (sqrt_price * sqrt_ratio_b))
        amount1wei = liquidity * (sqrt_price - sqrt_ratio_a)
    
    amount0 = amount0wei / (10 ** token0_decimal)
    amount1 = amount1wei / (10 ** token1_decimal)
    print(f"Amount Token0 wei: {amount0wei}")
    print(f"Amount Token1 wei: {amount1wei}")
    print(f"Amount Token0 : {amount0}")
    print(f"Amount Token1 : {amount1}")
    return amount0wei, amount1wei


# TODO dynamic decimals
def get_liquidity_within_sqrt_price_range(pool: BaseV3LiquidityPool, sqrt_price_low, sqrt_price_high):
    tick_lower_bound = log(sqrt_price_low, 1.0001**0.5)
    tick_upper_bound = log(sqrt_price_high, 1.0001**0.5)


def get_tokens_to_target_price(pool: BaseV3LiquidityPool, sqrt_target_price):
    # how much of X or Y tokens we need to *buy* to get to the target price?
    deltaTokens = 0
    sqrt_price_current = sqrt_x96_price_to_sqrt_price(pool.sqrt_price_x96)
    liquidity = pool.liquidity
    tick = pool.tick
    tick_lower, tick_upper = get_nearest_ticks(tick, pool.tick_spacing)
    sqrt_price_lower = tick_index_price(tick_lower//2)
    sqrt_price_upper = tick_index_price(tick_upper//2)

    if sqrt_target_price > sqrt_price_current:
        # too few Y in the pool; we need to buy some X to increase amount of Y in pool
        while sqrt_target_price > sqrt_price_current:
            if sqrt_target_price > sqrt_price_upper:
                # not in the current price range; use all X in the range
                x = calculate_token0_amount(liquidity, sqrt_price_current,sqrt_price_lower, sqrt_price_upper)
                deltaTokens += x
                # query the blockchain for liquidity in the next tick range
                nextTickRange = Tick(*pool._pool_contract.caller.ticks(tick_upper))
                liquidity += nextTickRange.liquidityNet
                # adjust the price and the range limits
                sqrt_price_current = sqrt_price_upper
                tick_lower = tick_upper
                tick_upper += pool.tick_spacing
                sqrt_price_lower = sqrt_price_upper
                sqrt_price_upper = tick_index_price(tick_upper // 2)
            else:
                # in the current price range
                x = calculate_token0_amount(liquidity, sqrt_price_current, sqrt_price_lower, sqrt_target_price)
                deltaTokens += x
                sqrt_price_current = sqrt_target_price
        print("need to buy {:.10f} X tokens".format(deltaTokens / 10 ** 18))
        

    elif sqrt_target_price < sqrt_price_current:
        # too much Y in the pool; we need to buy some Y to decrease amount of Y in pool
        currentTickRange = None
        while sqrt_target_price < sqrt_price_current:
            if sqrt_target_price < sqrt_price_lower:
                # not in the current price range; use all Y in the range
                y = calculate_token1_amount(liquidity, sqrt_price_current, sqrt_price_lower, sqrt_price_upper)
                deltaTokens += y
                if currentTickRange is None:
                    # query the blockchain for liquidityNet in the *current* tick range
                    currentTickRange = Tick(*pool._pool_contract.caller.ticks(tick_lower))
                liquidity -= currentTickRange.liquidityNet
                # adjust the price and the range limits
                sqrt_price_current = sqrt_price_lower
                tick_upper = tick_lower
                tick_lower -= pool.tick_spacing
                sqrt_price_upper = sqrt_price_lower
                sqrt_price_lower = tick_index_price(tick_lower // 2)
                # query the blockchain for liquidityNet in new current tick range
                currentTickRange = Tick(*pool._pool_contract.caller.ticks(tick_lower))
            else:
                # in the current price range
                y = calculate_token1_amount(liquidity, sqrt_price_current, sqrt_target_price, sqrt_price_upper)
                deltaTokens += y
                sqrt_price_current = sqrt_target_price
        print("need to buy {:.10f} Y tokens".format(deltaTokens / 10 ** 18))
        
    
    return deltaTokens

def sqrt_x96_price_to_price(sqrtPriceX96):
    return (sqrtPriceX96 ** 2) / ((2 ** 96) ** 2)

def sqrt_x96_price_to_sqrt_price(sqrtPriceX96):
    return sqrtPriceX96/(1 << 96)

def get_nearest_ticks(tick: int, tick_spacing: int):
    tick_below = (tick//tick_spacing) * tick_spacing
    tick_above = tick_below + tick_spacing
    return tick_below, tick_above

def tick_index_price(tick_index: int):
    return 1.0001**tick_index

def calculate_token0_amount(liquidity, sqrt_price_curr, sqrt_price_low, sqrt_price_high):
    sqrt_price_curr = max(min(sqrt_price_curr, sqrt_price_high), sqrt_price_low)
    return liquidity * (sqrt_price_high - sqrt_price_curr) / (sqrt_price_curr * sqrt_price_high)

def calculate_token1_amount(liquidity, sqrt_price_curr, sqrt_price_low, sqrt_price_high):
    sqrt_price_curr = max(min(sqrt_price_curr, sqrt_price_high), sqrt_price_low)
    return liquidity * (sqrt_price_curr - sqrt_price_low)

def get_tick_position_in_bitmap(tick:int):
    word_index = tick >> 8
    tick_index_in_word = tick % 256
    return word_index, tick_index_in_word