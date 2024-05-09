from typing import Optional


def design_order(
    symbol,
    order_type,
    instruction,
    quantity,
    leg_id,
    order_leg_type,
    asset_type,
    price: Optional[str] = None,
    session="NORMAL",
    duration="DAY",
    complex_order_strategy_type="NONE",
    tax_lot_method="FIFO",
    position_effect="OPENING",
    # special_instruction="ALL_OR_NONE",
    order_strategy_type="SINGLE",
):

    post_order_payload = {
        "price": price,
        "session": session,
        "duration": duration,
        "orderType": order_type,
        "complexOrderStrategyType": complex_order_strategy_type,
        "quantity": quantity,
        "taxLotMethod": tax_lot_method,
        "orderLegCollection": [
            {
                "orderLegType": order_leg_type,
                "legId": leg_id,
                "instrument": {
                    "symbol": symbol,
                    "assetType": asset_type,
                },
                "instruction": instruction,
                "positionEffect": position_effect,
                "quantity": quantity,
            }
        ],
        "orderStrategyType": order_strategy_type,
    }

    return post_order_payload
