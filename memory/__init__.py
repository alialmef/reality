# Memory module - stores what Alfred learns about the user

from memory.user_profile import (
    UserProfile,
    get_user_profile,
    get_profile_context,
    get_knowledge_gap_context,
)
from memory.conversation_store import (
    ConversationStore,
    get_conversation_store,
    get_conversation_context,
)
from memory.consolidation import (
    MemoryConsolidator,
    get_consolidator,
    get_understanding_context,
)
from memory.relationships import (
    RelationshipGraph,
    get_relationship_graph,
    get_relationships_context,
)

__all__ = [
    "UserProfile",
    "get_user_profile",
    "get_profile_context",
    "get_knowledge_gap_context",
    "ConversationStore",
    "get_conversation_store",
    "get_conversation_context",
    "MemoryConsolidator",
    "get_consolidator",
    "get_understanding_context",
    "RelationshipGraph",
    "get_relationship_graph",
    "get_relationships_context",
]
