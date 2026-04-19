from app.agents.framework.schemas import FrameworkAgentOutput


class FrameworkAgentService:
    async def run(self) -> FrameworkAgentOutput:
        return FrameworkAgentOutput()
