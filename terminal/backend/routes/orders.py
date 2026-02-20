from fastapi import APIRouter
from models import OrdersRequest
router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/")
async def create_order(order: Order):
    pass

@router.get("/")
async def get_orders(orders_request: OrdersRequest):
    

    okx_service = OkxService(base_url="https://www.okx.com")
    orders = await okx_service.get_orders()
    return orders

@router.delete("/")
async def cancel_order(order_id: str):
    pass
