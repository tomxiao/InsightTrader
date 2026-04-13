from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ta_service.config.settings import Settings, get_settings
from ta_service.models.auth import MobileUser
from ta_service.repos.analysis_tasks import AnalysisTaskRepository
from ta_service.repos.conversations import ConversationRepository
from ta_service.repos.messages import MessageRepository
from ta_service.repos.reports import ReportRepository
from ta_service.repos.user_sessions import UserSessionRepository
from ta_service.repos.users import UserRepository
from ta_service.services.analysis_service import AnalysisService
from ta_service.services.auth_service import AuthService
from ta_service.services.conversation_service import ConversationService
from ta_service.services.conversation_state_machine import ConversationStateMachine
from ta_service.services.resolution_agent import ResolutionAgent
from ta_service.services.resolution_service import ResolutionService
from ta_service.services.report_service import ReportService
from ta_service.services.stock_lookup_gateway import StockLookupGateway
from ta_service.workers.queue import AnalysisJobQueue

security = HTTPBearer(auto_error=False)


def get_app_state(request: Request):
    return request.app.state


def get_mongo_db(request: Request):
    return get_app_state(request).mongo_db


def get_redis(request: Request):
    return get_app_state(request).redis


def get_user_repository(request: Request) -> UserRepository:
    return UserRepository(get_mongo_db(request))


def get_user_session_repository(request: Request) -> UserSessionRepository:
    return UserSessionRepository(get_mongo_db(request))


def get_conversation_repository(request: Request) -> ConversationRepository:
    return ConversationRepository(get_mongo_db(request))


def get_message_repository(request: Request) -> MessageRepository:
    return MessageRepository(get_mongo_db(request))


def get_analysis_task_repository(request: Request) -> AnalysisTaskRepository:
    return AnalysisTaskRepository(get_mongo_db(request))


def get_report_repository(request: Request) -> ReportRepository:
    return ReportRepository(get_mongo_db(request))


def get_settings_dependency() -> Settings:
    return get_settings()


def get_job_queue(
    request: Request,
    settings: Settings = Depends(get_settings_dependency),
) -> AnalysisJobQueue:
    return AnalysisJobQueue(get_redis(request), settings)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    session_repo: UserSessionRepository = Depends(get_user_session_repository),
    settings: Settings = Depends(get_settings_dependency),
) -> AuthService:
    return AuthService(
        user_repo=user_repo,
        session_repo=session_repo,
        settings=settings,
    )


def get_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    return credentials.credentials


def get_current_user(
    token: str = Depends(get_access_token),
    auth_service: AuthService = Depends(get_auth_service),
):
    user = auth_service.get_current_user(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user


def require_admin(current_user: MobileUser = Depends(get_current_user)) -> MobileUser:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return current_user


def get_state_machine(
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
) -> ConversationStateMachine:
    return ConversationStateMachine(conversation_repo=conversation_repo)


def get_conversation_service(
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    message_repo: MessageRepository = Depends(get_message_repository),
    report_repo: ReportRepository = Depends(get_report_repository),
    task_repo: AnalysisTaskRepository = Depends(get_analysis_task_repository),
    state_machine: ConversationStateMachine = Depends(get_state_machine),
) -> ConversationService:
    return ConversationService(
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        report_repo=report_repo,
        task_repo=task_repo,
        state_machine=state_machine,
    )


def get_stock_lookup_gateway() -> StockLookupGateway:
    return StockLookupGateway()


def get_resolution_agent(
    stock_lookup_gateway: StockLookupGateway = Depends(get_stock_lookup_gateway),
) -> ResolutionAgent:
    return ResolutionAgent(stock_lookup_gateway=stock_lookup_gateway)


def get_analysis_service(
    task_repo: AnalysisTaskRepository = Depends(get_analysis_task_repository),
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    message_repo: MessageRepository = Depends(get_message_repository),
    report_repo: ReportRepository = Depends(get_report_repository),
    queue: AnalysisJobQueue = Depends(get_job_queue),
    settings: Settings = Depends(get_settings_dependency),
    state_machine: ConversationStateMachine = Depends(get_state_machine),
) -> AnalysisService:
    return AnalysisService(
        task_repo=task_repo,
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        report_repo=report_repo,
        queue=queue,
        settings=settings,
        state_machine=state_machine,
    )


def get_resolution_service(
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    message_repo: MessageRepository = Depends(get_message_repository),
    resolution_agent: ResolutionAgent = Depends(get_resolution_agent),
    stock_lookup_gateway: StockLookupGateway = Depends(get_stock_lookup_gateway),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    task_repo: AnalysisTaskRepository = Depends(get_analysis_task_repository),
    queue: AnalysisJobQueue = Depends(get_job_queue),
    state_machine: ConversationStateMachine = Depends(get_state_machine),
) -> ResolutionService:
    return ResolutionService(
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        resolution_agent=resolution_agent,
        stock_lookup_gateway=stock_lookup_gateway,
        analysis_service=analysis_service,
        task_repo=task_repo,
        queue=queue,
        state_machine=state_machine,
    )


def get_report_service(
    report_repo: ReportRepository = Depends(get_report_repository),
) -> ReportService:
    return ReportService(report_repo=report_repo)
