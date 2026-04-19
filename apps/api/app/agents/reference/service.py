from app.agents.reference.schemas import ReferenceAgentOutput


class ReferenceAgentService:
    async def run(self) -> ReferenceAgentOutput:
        return ReferenceAgentOutput()
