from app.agents.compression.schemas import CompressionAgentOutput


class CompressionAgentService:
    async def run(self) -> CompressionAgentOutput:
        return CompressionAgentOutput()
