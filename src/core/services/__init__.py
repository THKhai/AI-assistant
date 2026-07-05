from .knowledge_service import KnowledgeService
from .plan_service import ConversationService, PlanService
from .token_service import TotpService, TokenService
from .user_service import UserService

# Singleton instances — all services are stateless (no instance state).
# Module-level caches live inside each service file.
users = UserService()
tokens = TokenService()
totp = TotpService()
plans = PlanService()
conversations = ConversationService()
knowledge = KnowledgeService()


# ── FastAPI Depends factories ──

def get_user_service() -> UserService:
    return users


def get_token_service() -> TokenService:
    return tokens


def get_plan_service() -> PlanService:
    return plans


def get_conversation_service() -> ConversationService:
    return conversations


def get_knowledge_service() -> KnowledgeService:
    return knowledge
