# Synthetic fixture for agf-integrator's self-test (references/self-test.md), OpenAI Agents SDK
# profile. Not a real product -- a small support-agent with three tools, each built with a
# different, deliberate governance gap, matching the shape of
# assets/fixtures/support-agent-fastapi-mcp/server.py and assets/fixtures/langgraph-support-agent/
# server.py, adapted to this SDK's single FunctionTool-everywhere model (no separate "graph
# node"/"executor" surface to split, unlike LangGraph/A2A). Do not "fix" the gaps here; they are
# the fixture's whole point.

from agents import Agent, function_tool

from agf import AGFClient
from agf.openai_agents import guard_function_tool

_CUSTOMERS = {"cust_1": {"name": "Jane Doe", "tickets": ["tkt_1"]}}
_TICKETS = {"tkt_1": {"status": "open", "customer_id": "cust_1"}}

client = AGFClient(api_key="ak_live_fixture_only")


@function_tool
def search_order(customer_id: str) -> str:
    """No guard at all -- fully ungoverned. Anyone reaching this tool can look up any
    customer's order history."""
    return str(_CUSTOMERS.get(customer_id, {}))


@function_tool
def update_ticket(ticket_id: str, status: str, authenticated: bool) -> str:
    """Ad-hoc check only -- a Decision-shaped gate exists (checks a plain `authenticated`
    argument), but it isn't AGF-backed: no real Actor identity, no Authority scoping, no
    Receipt."""
    if not authenticated:
        raise PermissionError("not authenticated")
    _TICKETS[ticket_id]["status"] = status
    return f"ticket {ticket_id} set to {status}"


@function_tool
def issue_refund(order_id: str, amount: str) -> str:
    return f"refunded {amount} for order {order_id}"


guarded_issue_refund = guard_function_tool(
    issue_refund,
    client,
    agent_id="did:agf:fixture-agent",
    chain=[],
)
"""Decision is present in shape (guard_function_tool IS applied) -- but with a static, empty
chain=[] and no chain-building mechanism at all, this cannot succeed on a real call (agf-runtime
requires a non-empty chain or a trust_summary). No real Authority, no Actor beyond a static
constant, no Receipt, no execution-time validation."""


agent = Agent(name="support-agent", tools=[search_order, update_ticket, guarded_issue_refund])
