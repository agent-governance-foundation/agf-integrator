# Synthetic fixture for agf-integrator's self-test (references/self-test.md), A2A profile.
# Not a real product -- a small support-agent A2A server with three task executors, each built
# with a different, deliberate governance gap, matching the shape of
# assets/fixtures/support-agent-fastapi-mcp/server.py's MCP fixture, adapted to A2A's real
# one-executor-per-entrypoint model (execute() is the task-execution entrypoint, not a
# per-function decorator like MCP's @mcp.tool()). Do not "fix" the gaps here; they are the
# fixture's whole point.

from agf import AGFClient
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue

_CUSTOMERS = {"cust_1": {"name": "Jane Doe", "tickets": ["tkt_1"]}}
_TICKETS = {"tkt_1": {"status": "open", "customer_id": "cust_1"}}

client = AGFClient(api_key="ak_live_fixture_only")


class SearchOrderExecutor(AgentExecutor):
    """No guard at all -- fully ungoverned. Anyone reaching this executor can look up any
    customer's order history."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        customer_id = context.get_user_input()
        result = _CUSTOMERS.get(customer_id, {})
        await event_queue.enqueue_event(result)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


def _caller_authenticated(context: RequestContext) -> bool:
    # Stand-in for however a real deployment might gate this -- A2A's own transport-level
    # auth, not an AGF Decision.
    return context.call_context.user.is_authenticated


class UpdateTicketExecutor(AgentExecutor):
    """Ad-hoc check only -- a Decision-shaped gate exists (checks A2A's own
    call_context.user.is_authenticated), but it isn't AGF-backed: no Actor identity beyond
    whatever A2A's transport layer populated, no Authority scoping, no Receipt."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        if not _caller_authenticated(context):
            raise PermissionError("not authenticated")
        ticket_id, status = context.get_user_input().split(":", 1)
        _TICKETS[ticket_id]["status"] = status
        await event_queue.enqueue_event(f"ticket {ticket_id} set to {status}")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


class IssueRefundExecutor(AgentExecutor):
    """Decision is present in shape (calls AGFClient.decide()) -- but with an empty chain=[]
    and no chain-building mechanism at all, this cannot succeed on a real call (agf-runtime
    requires a non-empty chain or a trust_summary). No real Authority, no Actor beyond a static
    constant, no Receipt, no execution-time validation."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        result = await client.decide(
            action_type="task:issue_refund",
            resource="IssueRefundExecutor.execute",
            chain=[],
        )
        order_id, amount = context.get_user_input().split(":", 1)
        await event_queue.enqueue_event(f"refunded {amount} for order {order_id}")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass
