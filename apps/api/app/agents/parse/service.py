from app.agents.parse.schemas import ParseAgentOutput


class ParseAgentService:
    async def run(self) -> ParseAgentOutput:
        return ParseAgentOutput()
