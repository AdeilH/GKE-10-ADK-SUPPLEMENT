import grpc
import os
from dotenv import load_dotenv

from google.adk.agents import Agent

# Import the gRPC modules compiled from your .proto file
import demo_pb2
import demo_pb2_grpc

# --- Configuration ---
load_dotenv()
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY not found. Please add it to your .env file.")

# Read service addresses from environment variables
# Fallback to localhost for local testing
PRODUCT_CATALOG_ADDRESS = os.getenv('PRODUCT_CATALOG_SERVICE_ADDR', 'localhost:3550')
CHECKOUT_SERVICE_ADDRESS = os.getenv('CHECKOUT_SERVICE_ADDR', 'localhost:5050')

print(f"Connecting to Product Catalog at: {PRODUCT_CATALOG_ADDRESS}")
print(f"Connecting to Checkout Service at: {CHECKOUT_SERVICE_ADDRESS}")
# --- Tool Definitions ---

def list_all_products() -> dict:
    """Retrieves a summary of every product available in the Online Boutique's live catalog."""
    print("--- Tool Triggered: list_all_products ---")
    try:
        channel = grpc.insecure_channel(PRODUCT_CATALOG_ADDRESS)
        stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)
        response = stub.ListProducts(demo_pb2.Empty())
        product_summary = [p.name for p in response.products]
        print(f"--- Tool Success: Found {len(product_summary)} products ---")
        return {"status": "success", "products": product_summary}
    except grpc.RpcError as e:
        return {"status": "error", "error_message": f"Network error: {e.details()}"}


def get_product_details(product_name: str) -> dict:
    """Gets all available details for a single, specific product by its name."""
    print(f"--- Tool Triggered: get_product_details (Query: '{product_name}') ---")
    try:
        channel = grpc.insecure_channel(PRODUCT_CATALOG_ADDRESS)
        stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)
        response = stub.ListProducts(demo_pb2.Empty())
        search_key = product_name.lower().strip()
        for product in response.products:
            if product.name.lower() == search_key:
                price = product.price_usd.units + (product.price_usd.nanos / 1_000_000_000)
                product_data = {
                    "name": product.name,
                    "description": product.description,
                    "price": f"${price:.2f}",
                    "categories": list(product.categories)
                }
                print(f"--- Tool Success: Found details for '{product_name}' ---")
                return {"status": "success", "product": product_data}
        return {"status": "error", "error_message": f"Product '{product_name}' not found."}
    except grpc.RpcError as e:
        return {"status": "error", "error_message": f"Network error: {e.details()}"}


def place_order(email: str, street_address: str, city: str, state: str, zip_code: int, credit_card_number: str, credit_card_expiration_month: int, credit_card_expiration_year: int, credit_card_cvv: int) -> dict:
    """
    Places an order for the items in the user's cart. Requires all user details.
    This tool simulates a real purchase by calling the live checkout service.
    """
    print(f"--- Tool Triggered: place_order for user '{email}' ---")
    try:
        channel = grpc.insecure_channel(CHECKOUT_SERVICE_ADDRESS)
        stub = demo_pb2_grpc.CheckoutServiceStub(channel)
        
        # For this demo, we assume the user has already added items to their cart.
        # The checkout service automatically finds the cart for 'test-user'.
        request = demo_pb2.PlaceOrderRequest(
            email=email,
            address=demo_pb2.Address(
                street_address=street_address,
                city=city,
                state=state,
                zip_code=zip_code,
                country="USA"
            ),
            credit_card=demo_pb2.CreditCardInfo(
                credit_card_number=credit_card_number,
                credit_card_expiration_month=credit_card_expiration_month,
                credit_card_expiration_year=credit_card_expiration_year,
                credit_card_cvv=credit_card_cvv
            ),
            # In a real app, this would be the logged-in user's ID.
            user_id="test-user",
            user_currency="USD"
        )
        
        response = stub.PlaceOrder(request)
        
        print(f"--- Tool Success: Order placed, tracking ID {response.order.shipping_tracking_id} ---")
        return {
            "status": "success",
            "order_confirmation_id": response.order.order_id,
            "shipping_tracking_id": response.order.shipping_tracking_id,
        }
    except grpc.RpcError as e:
        return {"status": "error", "error_message": f"Failed to place order: {e.details()}"}


# --- Agent Definition ---

root_agent = Agent(
    name="boutique_complete_agent",
    model="gemini-2.0-flash",
    description=(
        "You are a full-service shopping agent for the 'Online Boutique'. You can help users discover, "
        "learn about, and purchase products."
    ),
    instruction=(
        "1. Start by helping the user find products using `list_all_products` and `get_product_details`.\n"
        "2. Elaborate creatively on product details to help the user visualize owning the item.\n"
        "3. If the user expresses clear intent to buy a product (e.g., 'I want to buy the watch', 'let's purchase it'), you must shift into the checkout workflow.\n"
        "4. **Checkout Workflow:** First, you MUST inform the user that you need their details to proceed. Ask them to provide their email, full shipping address, and credit card information.\n"
        "5. **Wait** for the user to provide all the necessary details.\n"
        "6. Once you have all the information, you MUST use the `place_order` tool to complete the purchase.\n"
        "7. After the tool call is successful, confirm the purchase with the user by providing the `order_confirmation_id` and the `shipping_tracking_id` from the tool's response. Be celebratory and thank them for their order."
    ),
    # Add the new place_order tool to the agent's skillset
    tools=[list_all_products, get_product_details, place_order],
)