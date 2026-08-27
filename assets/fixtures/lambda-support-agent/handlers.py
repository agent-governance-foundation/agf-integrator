# Synthetic fixture for agf-integrator's self-test (references/self-test.md), AWS Lambda profile.
# Not a real product -- three separate Lambda handlers, each built with a different, deliberate
# governance gap, matching the shape of every other fixture in this skill. Deliberately three
# separate functions, not three actions behind one entrypoint -- that's Lambda's real deployment
# unit (one function per handler), unlike the other profiles' single-process shape. Do not "fix"
# the gaps here; they are the fixture's whole point.

from agf import AGFClient
from agf.mcp import guard_tool

_CUSTOMERS = {"cust_1": {"name": "Jane Doe", "tickets": ["tkt_1"]}}
_TICKETS = {"tkt_1": {"status": "open", "customer_id": "cust_1"}}

client = AGFClient(api_key="ak_live_fixture_only")


def search_order(event, context):
    """No guard at all -- fully ungoverned. Anyone who can invoke this function can look up
    any customer's order history."""
    return {"statusCode": 200, "body": str(_CUSTOMERS.get(event.get("customer_id"), {}))}


def _caller_authenticated(event) -> bool:
    # Stand-in for however a real deployment might gate this -- e.g. an API Gateway authorizer
    # context field, not an AGF Decision.
    return bool(event.get("requestContext", {}).get("authorizer", {}).get("authenticated"))


def update_ticket(event, context):
    """Ad-hoc check only -- a Decision-shaped gate exists (checks a plain event field an API
    Gateway authorizer might set), but it isn't AGF-backed: no Actor identity beyond whatever
    populated that field, no Authority scoping, no Receipt."""
    if not _caller_authenticated(event):
        return {"statusCode": 403, "body": "not authenticated"}
    ticket_id = event["ticket_id"]
    _TICKETS[ticket_id]["status"] = event["status"]
    return {"statusCode": 200, "body": f"ticket {ticket_id} set to {event['status']}"}


@guard_tool(client, agent_id="did:agf:fixture-agent", action_type="lambda:issue_refund", chain=[])
def issue_refund(event, context):
    """Decision is present in shape (guard_tool IS applied) -- but with a static, empty
    chain=[] and no chain-building mechanism at all, this cannot succeed on a real call
    (agf-runtime requires a non-empty chain or a trust_summary). No real Authority, no Actor
    beyond a static constant, no Receipt, no execution-time validation."""
    return {"statusCode": 200, "body": f"refunded {event['amount']} for order {event['order_id']}"}
