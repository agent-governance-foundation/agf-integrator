# Synthetic fixture for agf-integrator's self-test (references/self-test.md), LangGraph profile.
# Not a real product -- a small support-agent LangGraph with three graph nodes, each built with
# a different, deliberate governance gap, matching the shape of
# assets/fixtures/support-agent-fastapi-mcp/server.py and assets/fixtures/a2a-support-agent/
# server.py, adapted to LangGraph's StateGraph.add_node() model. Deliberately tests only the
# graph-node surface (guard_node) -- the tool-calling surface (ToolNode/create_react_agent)
# already reuses the FastAPI/MCP fixture's AGFGuardedTool pattern untouched, no new ground to
# cover there. Do not "fix" the gaps here; they are the fixture's whole point.

from typing import TypedDict

from agf import AGFClient
from agf.langgraph import guard_node
from langgraph.graph import END, START, StateGraph

_CUSTOMERS = {"cust_1": {"name": "Jane Doe", "tickets": ["tkt_1"]}}
_TICKETS = {"tkt_1": {"status": "open", "customer_id": "cust_1"}}

client = AGFClient(api_key="ak_live_fixture_only")


class State(TypedDict):
    customer_id: str
    ticket_id: str
    status: str
    order_id: str
    amount: str
    authenticated: bool
    result: str


def search_order(state: State) -> dict:
    """No guard at all -- fully ungoverned. Anyone reaching this node can look up any
    customer's order history."""
    result = _CUSTOMERS.get(state["customer_id"], {})
    return {"result": str(result)}


def update_ticket(state: State) -> dict:
    """Ad-hoc check only -- a Decision-shaped gate exists (checks a plain `authenticated` flag
    on state), but it isn't AGF-backed: no Actor identity beyond whatever populated that flag,
    no Authority scoping, no Receipt."""
    if not state.get("authenticated"):
        raise PermissionError("not authenticated")
    _TICKETS[state["ticket_id"]]["status"] = state["status"]
    return {"result": f"ticket {state['ticket_id']} set to {state['status']}"}


@guard_node(client, agent_id="did:agf:fixture-agent", chain=[])
def issue_refund(state: State) -> dict:
    """Decision is present in shape (guard_node IS applied) -- but with a static, empty
    chain=[] and no chain-building mechanism at all, this cannot succeed on a real call
    (agf-runtime requires a non-empty chain or a trust_summary). No real Authority, no Actor
    beyond a static constant, no Receipt, no execution-time validation."""
    return {"result": f"refunded {state['amount']} for order {state['order_id']}"}


graph = StateGraph(State)
graph.add_node("search_order", search_order)
graph.add_node("update_ticket", update_ticket)
graph.add_node("issue_refund", issue_refund)
graph.add_edge(START, "search_order")
graph.add_edge("search_order", "update_ticket")
graph.add_edge("update_ticket", "issue_refund")
graph.add_edge("issue_refund", END)
app = graph.compile()
