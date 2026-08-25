# Synthetic fixture for agf-integrator's self-test (references/self-test.md).
# Not a real product — a small support-agent MCP server with three tools, each built with a
# different, deliberate governance gap, matching the worked example used throughout this
# skill's reference docs. Do not "fix" the gaps here; they are the fixture's whole point.

from mcp.server.fastmcp import FastMCP
from agf import AGFClient
from agf.mcp import guard_tool

mcp = FastMCP("support-agent")
client = AGFClient(api_key="ak_live_fixture_only")

_CUSTOMERS = {"cust_1": {"name": "Jane Doe", "tickets": ["tkt_1"]}}
_TICKETS = {"tkt_1": {"status": "open", "customer_id": "cust_1"}}


@mcp.tool()
def search_customer(customer_id: str) -> dict:
    """No guard at all — fully ungoverned. Anyone calling this tool can look up any customer."""
    return _CUSTOMERS.get(customer_id, {})


def _current_user_role() -> str:
    # Stand-in for however the caller's role would really be resolved in a live deployment.
    return "support_agent"


@mcp.tool()
def update_ticket(ticket_id: str, status: str) -> str:
    """Ad-hoc role check only — a Decision exists, but it isn't AGF-backed, and there's no
    Actor identity beyond an assumed static role, no Authority scoping, no Receipt."""
    if _current_user_role() not in ("support_agent", "admin"):
        raise PermissionError("not authorized")
    _TICKETS[ticket_id]["status"] = status
    return f"ticket {ticket_id} set to {status}"


@mcp.tool()
@guard_tool(client, agent_id="did:agf:support-agent", action_type="tool:issue_refund", resource="issue_refund")
def issue_refund(order_id: str, amount: float) -> str:
    """Decision is present (guard_tool, real agf-sdk call) — but agent_id is a static
    constant (no real per-caller Actor), no chain= is passed (no Authority scoping), and there
    is no receipt or execution-time validation."""
    return f"refunded {amount} for order {order_id}"
