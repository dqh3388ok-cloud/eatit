from app.agents.report.schemas import ReportAgentOutput


class ReportAgentService:
    async def run(self) -> ReportAgentOutput:
        return ReportAgentOutput()
