from app.agents.interviewer.schemas import InterviewerAgentOutput


class InterviewerAgentService:
    async def run(self) -> InterviewerAgentOutput:
        return InterviewerAgentOutput()
