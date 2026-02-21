import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Literal, Optional

import asyncio
import queue
import concurrent.futures
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from core.llm import OpenAIProvider
from core.llm.factory import BaseLLM
from core.memory import ConversationManager, KnowledgeManager, KnowledgeExtractor
from core.skills import SkillRegistry, SkillExecutor
from core.architect import SkillGenerator
from core.tools import build_tool_definitions, ToolExecutor
from core.tools.loop import run_tool_loop
from core.auth import TailscaleAuth
from core.auth.middleware import TailscaleAuthMiddleware
from skills.core_ops.git_tools import GitTools

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Zane",
    description="A calm, helpful AI assistant - your Exocortex",
    version="0.1.0"
)

# Build CORS origins list (localhost + Tailscale IP if available)
cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
try:
    ts_ip = subprocess.run(
        ["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=2
    ).stdout.strip()
    if ts_ip:
        cors_origins.append(f"http://{ts_ip}:5173")
        cors_origins.append(f"http://{ts_ip}:8000")
        logger.info("Tailscale IP detected: %s — added to CORS origins", ts_ip)
except Exception:
    logger.info("Tailscale IP not available — using localhost origins only")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tailscale auth middleware (conditional)
tailscale_enabled = os.getenv("TAILSCALE_AUTH_ENABLED", "true").lower() == "true"
if tailscale_enabled:
    tailscale_auth = TailscaleAuth()
    app.add_middleware(TailscaleAuthMiddleware, tailscale_auth=tailscale_auth, exempt_paths=["/"])
    logger.info("Tailscale auth middleware enabled")
else:
    logger.info("Tailscale auth middleware disabled")

# Load system prompt
PROMPTS_DIR = Path(__file__).parent / "config" / "prompts"
SYSTEM_PROMPT_PATH = PROMPTS_DIR / "system_core.md"

def load_system_prompt() -> str:
    """Load the system prompt from disk."""
    if SYSTEM_PROMPT_PATH.exists():
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    return ""

# Initialize LLM provider
llm: Optional[BaseLLM] = None

# Initialize conversation manager
CONVERSATIONS_DIR = Path(__file__).parent / "memory" / "conversations"
conversation_manager = ConversationManager(CONVERSATIONS_DIR)

# Initialize knowledge manager
KNOWLEDGE_DIR = Path(__file__).parent / "memory" / "knowledge"
knowledge_manager = KnowledgeManager(KNOWLEDGE_DIR)

# Knowledge extractor (initialized lazily after LLM)
knowledge_extractor: Optional[KnowledgeExtractor] = None

# Initialize skills
SKILLS_DIR = Path(__file__).parent / "skills"
skill_registry = SkillRegistry(SKILLS_DIR)
skill_executor = SkillExecutor(skill_registry)

# Tool executor for Claude tool-use
tool_executor_instance = ToolExecutor(skill_executor, knowledge_manager)

# Skill generator (initialized lazily after LLM)
skill_generator: Optional[SkillGenerator] = None

# Git tools for safe code modification
ARCHITECT_PROMPT_PATH = PROMPTS_DIR / "architect.md"
git_tools = GitTools(Path(__file__).parent)

# Pending skill plans awaiting user approval (keyed by thread_id)
PENDING_PLANS_PATH = Path(__file__).parent / "memory" / "pending_plans.json"


def _load_pending_plans() -> dict:
    """Load pending plans from disk."""
    if PENDING_PLANS_PATH.exists():
        return json.loads(PENDING_PLANS_PATH.read_text(encoding="utf-8"))
    return {}


def _save_pending_plans(plans: dict) -> None:
    """Save pending plans to disk."""
    PENDING_PLANS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PENDING_PLANS_PATH.write_text(json.dumps(plans, indent=2), encoding="utf-8")


def _check_approval(message: str) -> Optional[bool]:
    """Check if a message is approving or rejecting a pending plan.

    Returns:
        True if approving, False if rejecting, None if neither.
    """
    msg = message.strip().lower()
    approve_words = ["yes", "approve", "go ahead", "do it", "build it",
                     "looks good", "lgtm", "ship it", "proceed", "go for it", "approved"]
    reject_words = ["no", "reject", "cancel", "stop", "don't", "abort", "nevermind", "nah"]

    for word in approve_words:
        if msg == word or msg.startswith(word + " ") or msg.startswith(word + ",") or msg.startswith(word + "."):
            return True
    for word in reject_words:
        if msg == word or msg.startswith(word + " ") or msg.startswith(word + ",") or msg.startswith(word + "."):
            return False
    return None


def get_llm() -> BaseLLM:
    """Get or initialize the LLM provider."""
    global llm
    if llm is None:
        llm = OpenAIProvider()
    return llm


def get_generator() -> SkillGenerator:
    """Get or initialize the skill generator."""
    global skill_generator
    if skill_generator is None:
        skill_generator = SkillGenerator(
            llm=get_llm(),
            skills_path=SKILLS_DIR,
            architect_prompt_path=ARCHITECT_PROMPT_PATH
        )
    return skill_generator


def get_extractor() -> KnowledgeExtractor:
    """Get or initialize the knowledge extractor."""
    global knowledge_extractor
    if knowledge_extractor is None:
        knowledge_extractor = KnowledgeExtractor(get_llm())
    return knowledge_extractor


# Pydantic models
class LogEvent(BaseModel):
    """A single log event for transparency."""
    type: Literal["thought", "tool", "file_io", "error"]
    subtype: Optional[str] = None
    message: str
    metadata: Optional[dict] = None


class ZaneResponse(BaseModel):
    """The standard response format from Zane."""
    text: str
    thread_id: str
    reasoning: str = ""
    audio_base64: Optional[str] = None
    logs: list[LogEvent]


class RollbackResponse(BaseModel):
    """Response from the rollback endpoint."""
    success: bool
    message: str
    rolled_back_commit: Optional[str] = None
    reset_to: Optional[str] = None


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""
    message: str
    thread_id: Optional[str] = None


class ThreadResponse(BaseModel):
    """Response for loading a full thread."""
    id: str
    created_at: str
    messages: list[dict]


class ThreadSummary(BaseModel):
    """Lightweight thread metadata for the thread list."""
    id: str
    created_at: str
    message_count: int
    preview: str


class ThreadListResponse(BaseModel):
    """Response for listing all threads."""
    threads: list[ThreadSummary]


def _execute_skill_plan(plan: dict, logs: list[LogEvent]) -> str:
    """Execute an approved skill plan: snapshot -> generate -> validate -> commit.

    Args:
        plan: The pending plan dict with 'user_request' and 'skill_id'.
        logs: The transparency log list to append to.

    Returns:
        Response text describing the result.
    """
    is_modify = plan.get("action") == "modify"
    target_skill_id = plan.get("target_skill_id")

    # Step 1: Git snapshot
    action_label = "modifying" if is_modify else "generating"
    snapshot_sha = git_tools.snapshot(f"Before {action_label} skill: {plan['user_request'][:50]}")
    logs.append(LogEvent(type="tool", subtype="snapshot", message=f"Git snapshot created: {snapshot_sha[:8]}"))

    # Step 2: Generate or modify skill code
    generator = get_generator()

    if is_modify and target_skill_id:
        # Load existing skill files for modification
        skill_files = skill_registry.get_skill_files(target_skill_id)
        if not skill_files:
            logs.append(LogEvent(type="error", subtype="skill_gen", message=f"Could not load existing skill: {target_skill_id}"))
            return f"Failed to load existing skill '{target_skill_id}' for modification."

        generated = generator.generate_modification(
            plan["user_request"],
            skill_files["manifest"],
            skill_files["code"]
        )
    else:
        generated = generator.generate(plan["user_request"])

    if not generated["success"]:
        logs.append(LogEvent(type="error", subtype="skill_gen", message=f"Skill generation failed: {generated.get('error')}"))
        return f"I attempted to {'modify' if is_modify else 'create'} the skill but failed: {generated.get('error')}"

    logs.append(LogEvent(type="tool", subtype="skill_gen", message=f"Skill {'modified' if is_modify else 'generated'}: {generated['skill_id']}"))

    # Step 3: Save to disk
    if is_modify and target_skill_id:
        skill_files = skill_registry.get_skill_files(target_skill_id)
        saved = generator.save_skill_to_path(generated, skill_files["path"])
    else:
        saved = generator.save_skill(generated)

    if not saved["success"]:
        git_tools.rollback()
        logs.append(LogEvent(type="error", subtype="skill_save", message=f"Failed to save skill, rolled back: {saved.get('error')}"))
        return f"Failed to save the skill: {saved.get('error')}. Changes rolled back."

    logs.append(LogEvent(type="file_io", subtype="write", message=f"Skill saved to: {saved['path']}"))

    # Step 4: Validate
    validation = generator.validate_skill(Path(saved["path"]))
    if not validation["valid"]:
        git_tools.rollback()
        logs.append(LogEvent(type="error", subtype="skill_validate", message=f"Skill validation failed, rolled back: {validation['errors']}"))
        return f"The generated skill had errors: {validation['errors']}. Changes rolled back."

    # Step 5: Commit on success
    commit_label = "Modified" if is_modify else "Created"
    commit_sha = git_tools.commit(f"[ZANE] {commit_label} skill: {generated['skill_id']}")
    logs.append(LogEvent(type="tool", subtype="commit", message=f"Skill committed: {commit_sha[:8]}"))

    # Reload skill registry
    skill_registry.reload()

    return f"Successfully {'modified' if is_modify else 'created'} skill '{generated['skill_id']}' at {saved['path']}. The skill is now available for use. ✅"


def _build_reasoning(logs: list[LogEvent]) -> str:
    """Condense logs into a short reasoning trace."""
    parts = []
    for log in logs:
        if log.subtype == 'knowledge_read':
            if log.type == 'thought' and log.metadata:
                n = len(log.metadata.get('entries', []))
                parts.append(f"Found {n} knowledge entries")
            elif 'No matching' in log.message:
                parts.append("No knowledge matches")
        elif log.subtype == 'intent':
            meta = log.metadata or {}
            mode = meta.get('mode', '?')
            conf = meta.get('confidence', 0)
            parts.append(f"{mode} intent ({conf:.0%})")
        elif log.subtype == 'history':
            parts.append(log.message)
        elif log.subtype == 'skill_exec':
            if 'Executing' in log.message:
                parts.append(log.message)
        elif log.subtype == 'approval':
            parts.append(log.message)
        elif log.subtype in ('skill_gen', 'snapshot', 'commit'):
            parts.append(log.message)
        elif log.subtype == 'plan':
            parts.append(log.message)
        elif log.subtype == 'tool_call':
            parts.append(log.message)
        elif log.subtype == 'tool_result':
            meta = log.metadata or {}
            parts.append(f"{meta.get('tool_name', '?')} returned")
        elif log.subtype in ('tools', 'tool_loop'):
            parts.append(log.message)
        elif log.type == 'error' and log.subtype not in ('knowledge_read',):
            parts.append(f"Error: {log.message}")
    return ' → '.join(parts) if parts else 'Processed request'


@app.get("/")
def health_check():
    """Health check endpoint."""
    return {"status": "operational", "name": "Zane", "version": "0.1.0"}


@app.post("/rollback", response_model=RollbackResponse)
def rollback() -> RollbackResponse:
    """Roll back the last [ZANE] skill commit.

    Finds the most recent [ZANE] commit, resets to its snapshot parent,
    and reloads the skill registry so the change takes effect immediately.
    """
    result = git_tools.rollback_last_zane()

    if result["success"]:
        skill_registry.reload()

    return RollbackResponse(**result)


@app.post("/chat", response_model=ZaneResponse)
def chat(chat_request: ChatRequest, request: Request) -> ZaneResponse:
    """Process a chat message and return Zane's response.

    Uses the Glass Box Router to determine intent (CHAT/SKILL/DEV)
    and routes accordingly with full transparency logging.

    Args:
        chat_request: The chat request containing the user's message.
        request: The raw HTTP request (for auth info).

    Returns:
        ZaneResponse with the assistant's reply and transparency logs.
    """
    logs: list[LogEvent] = []

    # Log Tailscale user if present
    ts_user = getattr(request.state, "tailscale_user", None)
    if ts_user:
        logs.append(LogEvent(
            type="thought",
            subtype="auth",
            message=f"Tailscale user: {ts_user['display_name']} ({ts_user['login_name']}) from {ts_user['node_name']}",
            metadata=ts_user,
        ))

    # Log the incoming request
    logs.append(LogEvent(
        type="thought",
        subtype="receive",
        message=f"Received message: '{chat_request.message[:50]}...'" if len(chat_request.message) > 50 else f"Received message: '{chat_request.message}'"
    ))

    try:
        # Get or create thread
        thread_id = chat_request.thread_id
        if not thread_id or not conversation_manager.thread_exists(thread_id):
            thread_id = conversation_manager.create_thread()
            logs.append(LogEvent(
                type="file_io",
                subtype="write",
                message=f"Created new conversation thread: {thread_id}"
            ))

        # Save user message to thread
        conversation_manager.save_message(thread_id, "user", chat_request.message)

        # Retrieve relevant knowledge
        relevant_knowledge = knowledge_manager.retrieve_relevant(chat_request.message)
        knowledge_context = ""
        if relevant_knowledge:
            knowledge_context = knowledge_manager.format_for_context(relevant_knowledge)
            logs.append(LogEvent(
                type="thought",
                subtype="knowledge_read",
                message=f"Retrieved {len(relevant_knowledge)} relevant knowledge entries",
                metadata={"entries": [e.get("file_path") for e in relevant_knowledge]}
            ))
        else:
            logs.append(LogEvent(
                type="thought",
                subtype="knowledge_read",
                message="No matching knowledge entries"
            ))

        # Check for pending skill plan awaiting approval
        pending_plans = _load_pending_plans()
        if thread_id in pending_plans:
            approval = _check_approval(chat_request.message)

            if approval is True:
                # User approved - execute the plan
                plan = pending_plans.pop(thread_id)
                _save_pending_plans(pending_plans)

                logs.append(LogEvent(
                    type="thought",
                    subtype="approval",
                    message="User approved skill plan. Proceeding with generation."
                ))

                response_text = _execute_skill_plan(plan, logs)

                # Save + extract knowledge + return (skip normal routing)
                conversation_manager.save_message(thread_id, "assistant", response_text)
                logs.append(LogEvent(type="thought", subtype="done", message="Response generated successfully."))

                return ZaneResponse(text=response_text, thread_id=thread_id, reasoning=_build_reasoning(logs), audio_base64=None, logs=logs)

            elif approval is False:
                # User rejected
                pending_plans.pop(thread_id)
                _save_pending_plans(pending_plans)

                response_text = "No worries, I've cancelled the skill plan. Let me know if you'd like to try something different. 👍"

                conversation_manager.save_message(thread_id, "assistant", response_text)
                logs.append(LogEvent(type="thought", subtype="approval", message="User rejected skill plan."))
                logs.append(LogEvent(type="thought", subtype="done", message="Response generated successfully."))

                return ZaneResponse(text=response_text, thread_id=thread_id, reasoning=_build_reasoning(logs), audio_base64=None, logs=logs)

            # If neither approve nor reject, fall through to normal routing
            # (user might be asking a follow-up question about the plan)

        # Check for DEV mode (explicit "dev" keyword required)
        is_dev_mode = re.search(r'\bdev\b', chat_request.message, re.IGNORECASE)

        if is_dev_mode:
            # ---- DEV MODE: existing plan→approve→execute flow (unchanged) ----
            provider = get_llm()

            # Use IntentDetector just for DEV action/target classification
            from core.routing import IntentDetector
            dev_detector = IntentDetector(provider)
            available_skills = skill_registry.list_skills()
            intent = dev_detector.detect(chat_request.message, available_skills)

            dev_action = intent.dev_action or "create"
            target_skill_name = intent.target_skill

            # Try to resolve target skill for modifications
            target_skill_id = None
            existing_skill = None
            if dev_action == "modify" and target_skill_name:
                existing_skill = skill_registry.get_skill(target_skill_name)
                if not existing_skill:
                    for s in available_skills:
                        if target_skill_name.lower() in s.get("name", "").lower() or target_skill_name.lower() in s.get("id", "").lower():
                            existing_skill = s
                            break
                if existing_skill:
                    target_skill_id = existing_skill.get("id")

            is_modify = dev_action == "modify" and target_skill_id is not None
            action_label = "modification" if is_modify else "creation"

            logs.append(LogEvent(
                type="thought",
                subtype="mode",
                message=f"Entering DEV mode: Generating skill {action_label} plan for approval." + (f" Target: {target_skill_id}" if is_modify else "")
            ))

            generator = get_generator()

            if is_modify:
                skill_files = skill_registry.get_skill_files(target_skill_id)
                if skill_files:
                    plan_result = generator.plan_modification(chat_request.message, skill_files["manifest"], skill_files["code"])
                else:
                    plan_result = {"success": False, "error": f"Could not read files for skill '{target_skill_id}'"}
            else:
                plan_result = generator.plan(chat_request.message)

            if not plan_result["success"]:
                logs.append(LogEvent(
                    type="error",
                    subtype="plan",
                    message=f"Planning failed: {plan_result.get('error')}"
                ))
                response_text = f"I tried to plan a skill {action_label} but hit an issue: {plan_result.get('error')}"
            else:
                pending_plans = _load_pending_plans()
                plan_data = {
                    "user_request": plan_result["user_request"],
                    "skill_id": plan_result["skill_id"],
                    "plan_text": plan_result["plan_text"]
                }
                if is_modify:
                    plan_data["action"] = "modify"
                    plan_data["target_skill_id"] = target_skill_id
                pending_plans[thread_id] = plan_data
                _save_pending_plans(pending_plans)

                logs.append(LogEvent(
                    type="thought",
                    subtype="plan",
                    message=f"Skill {action_label} plan stored, awaiting approval for: {plan_result['skill_id']}"
                ))

                verb = "modify" if is_modify else "build"
                response_text = (
                    f"Here's my plan for this skill {action_label}:\n\n"
                    f"{plan_result['plan_text']}\n\n"
                    f"---\n"
                    f"**Shall I go ahead and {verb} this?** (yes/no)"
                )

        else:
            # ---- TOOL-USE FLOW: replaces intent detection + CHAT/SKILL routing ----
            provider = get_llm()

            # Build system prompt with knowledge context
            system_prompt = load_system_prompt()
            if knowledge_context:
                system_prompt += f"\n\n## Relevant Knowledge\n{knowledge_context}"

            # Load conversation history
            messages = conversation_manager.load_context(thread_id)
            logs.append(LogEvent(
                type="thought",
                subtype="history",
                message=f"Loaded {len(messages)} messages from conversation history."
            ))

            # Build tool definitions from current skill registry
            available_skills = skill_registry.list_skills()
            tools = build_tool_definitions(available_skills)

            logs.append(LogEvent(
                type="thought",
                subtype="tools",
                message=f"Prepared {len(tools)} tools ({len(available_skills)} skills registered)."
            ))

            # Run the tool-use conversation loop
            loop_result = run_tool_loop(
                provider=provider,
                tool_executor=tool_executor_instance,
                messages=messages,
                tools=tools,
                system_prompt=system_prompt,
                max_tokens=1024
            )

            response_text = loop_result.text

            # Merge loop logs into our transparency logs
            for log_dict in loop_result.logs:
                logs.append(LogEvent(**log_dict))

        # Save assistant response to thread (text only, no tool-use blocks)
        conversation_manager.save_message(thread_id, "assistant", response_text)

        # Knowledge extraction safety net
        # Skip if save_knowledge was already called during tool use
        save_knowledge_called = any(
            log.subtype == "tool_call" and
            log.metadata and
            log.metadata.get("tool_name") == "save_knowledge"
            for log in logs
        )

        if not save_knowledge_called:
            try:
                extractor = get_extractor()
                extraction = extractor.extract_updates(
                    user_message=chat_request.message,
                    assistant_response=response_text,
                    knowledge_context=knowledge_context
                )

                if extraction["updates"]:
                    logs.append(LogEvent(
                        type="thought",
                        subtype="knowledge_extract",
                        message=f"Extracting knowledge: {extraction['reasoning']}"
                    ))

                    for update in extraction["updates"]:
                        update_fields = update.get("fields") or {}
                        related_files = update_fields.pop("related_files", None)
                        result = knowledge_manager.find_or_create_entry(
                            template_type=update["template_type"],
                            identifier=update["identifier"],
                            content=update.get("content"),
                            tags=update.get("tags", []),
                            fields=update_fields if update_fields else None,
                            related_files=related_files
                        )
                        logs.append(LogEvent(
                            type="file_io",
                            subtype="write",
                            message=f"Knowledge {result.get('action', 'processed')}: {result.get('file_path', 'unknown')}",
                            metadata=result
                        ))
            except Exception as e:
                logs.append(LogEvent(
                    type="error",
                    subtype="knowledge",
                    message=f"Knowledge extraction failed: {str(e)}"
                ))
        else:
            logs.append(LogEvent(
                type="thought",
                subtype="knowledge_extract",
                message="Skipping post-hoc extraction: save_knowledge was called during tool use."
            ))

        logs.append(LogEvent(
            type="thought",
            subtype="done",
            message="Response generated successfully."
        ))

        return ZaneResponse(
            text=response_text,
            thread_id=thread_id,
            reasoning=_build_reasoning(logs),
            audio_base64=None,
            logs=logs
        )

    except ValueError as e:
        logs.append(LogEvent(
            type="error",
            subtype="validation",
            message=str(e)
        ))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logs.append(LogEvent(
            type="error",
            subtype="llm",
            message=f"LLM call failed: {str(e)}"
        ))
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")


@app.post("/chat/stream")
async def chat_stream(chat_request: ChatRequest, request: Request):
    """Process a chat message with SSE streaming of log events.

    Streams events in SSE format:
      data: {"type":"log","event":{...}}
      data: {"type":"response","text":"...","thread_id":"...","reasoning":"..."}

    Falls back gracefully if streaming fails.
    """

    async def event_generator():
        logs: list[LogEvent] = []
        # Use thread-safe queue (not asyncio.Queue) for cross-thread communication
        log_queue: queue.Queue = queue.Queue()

        def on_log(log_dict: dict):
            """Callback to queue logs from the sync tool loop."""
            log_event = LogEvent(**log_dict)
            logs.append(log_event)
            # Thread-safe put (no event loop needed)
            log_queue.put(("log", log_event))

        # Log Tailscale user if present
        ts_user = getattr(request.state, "tailscale_user", None)
        if ts_user:
            log = LogEvent(
                type="thought",
                subtype="auth",
                message=f"Tailscale user: {ts_user['display_name']}",
                metadata=ts_user,
            )
            logs.append(log)
            yield f"data: {json.dumps({'type': 'log', 'event': log.model_dump()})}\n\n"

        # Log incoming request
        log = LogEvent(
            type="thought",
            subtype="receive",
            message=f"Received message: '{chat_request.message[:50]}...'" if len(chat_request.message) > 50 else f"Received message: '{chat_request.message}'"
        )
        logs.append(log)
        yield f"data: {json.dumps({'type': 'log', 'event': log.model_dump()})}\n\n"

        try:
            # Get or create thread
            thread_id = chat_request.thread_id
            if not thread_id or not conversation_manager.thread_exists(thread_id):
                thread_id = conversation_manager.create_thread()
                log = LogEvent(type="file_io", subtype="write", message=f"Created new conversation thread: {thread_id}")
                logs.append(log)
                yield f"data: {json.dumps({'type': 'log', 'event': log.model_dump()})}\n\n"

            # Save user message
            conversation_manager.save_message(thread_id, "user", chat_request.message)

            # Retrieve relevant knowledge
            relevant_knowledge = knowledge_manager.retrieve_relevant(chat_request.message)
            knowledge_context = ""
            if relevant_knowledge:
                knowledge_context = knowledge_manager.format_for_context(relevant_knowledge)
                log = LogEvent(
                    type="thought",
                    subtype="knowledge_read",
                    message=f"Retrieved {len(relevant_knowledge)} relevant knowledge entries",
                    metadata={"entries": [e.get("file_path") for e in relevant_knowledge]}
                )
            else:
                log = LogEvent(type="thought", subtype="knowledge_read", message="No matching knowledge entries")
            logs.append(log)
            yield f"data: {json.dumps({'type': 'log', 'event': log.model_dump()})}\n\n"

            # Check for pending skill plan
            pending_plans = _load_pending_plans()
            if thread_id in pending_plans:
                approval = _check_approval(chat_request.message)

                if approval is True:
                    plan = pending_plans.pop(thread_id)
                    _save_pending_plans(pending_plans)

                    log = LogEvent(type="thought", subtype="approval", message="User approved skill plan. Proceeding with generation.")
                    logs.append(log)
                    yield f"data: {json.dumps({'type': 'log', 'event': log.model_dump()})}\n\n"

                    response_text = _execute_skill_plan(plan, logs)
                    conversation_manager.save_message(thread_id, "assistant", response_text)

                    yield f"data: {json.dumps({'type': 'response', 'text': response_text, 'thread_id': thread_id, 'reasoning': _build_reasoning(logs), 'logs': [l.model_dump() for l in logs]})}\n\n"
                    return

                elif approval is False:
                    pending_plans.pop(thread_id)
                    _save_pending_plans(pending_plans)

                    response_text = "No worries, I've cancelled the skill plan. Let me know if you'd like to try something different. 👍"
                    conversation_manager.save_message(thread_id, "assistant", response_text)

                    log = LogEvent(type="thought", subtype="approval", message="User rejected skill plan.")
                    logs.append(log)
                    yield f"data: {json.dumps({'type': 'log', 'event': log.model_dump()})}\n\n"
                    yield f"data: {json.dumps({'type': 'response', 'text': response_text, 'thread_id': thread_id, 'reasoning': _build_reasoning(logs), 'logs': [l.model_dump() for l in logs]})}\n\n"
                    return

            # Check for DEV mode
            is_dev_mode = re.search(r'\bdev\b', chat_request.message, re.IGNORECASE)

            if is_dev_mode:
                # DEV mode logic (simplified for streaming - we don't stream the planning)
                provider = get_llm()
                from core.routing import IntentDetector
                dev_detector = IntentDetector(provider)
                available_skills = skill_registry.list_skills()
                intent = dev_detector.detect(chat_request.message, available_skills)

                dev_action = intent.dev_action or "create"
                target_skill_name = intent.target_skill
                target_skill_id = None
                existing_skill = None

                if dev_action == "modify" and target_skill_name:
                    existing_skill = skill_registry.get_skill(target_skill_name)
                    if not existing_skill:
                        for s in available_skills:
                            if target_skill_name.lower() in s.get("name", "").lower() or target_skill_name.lower() in s.get("id", "").lower():
                                existing_skill = s
                                break
                    if existing_skill:
                        target_skill_id = existing_skill.get("id")

                is_modify = dev_action == "modify" and target_skill_id is not None
                action_label = "modification" if is_modify else "creation"

                log = LogEvent(
                    type="thought",
                    subtype="mode",
                    message=f"Entering DEV mode: Generating skill {action_label} plan."
                )
                logs.append(log)
                yield f"data: {json.dumps({'type': 'log', 'event': log.model_dump()})}\n\n"

                generator = get_generator()

                if is_modify:
                    skill_files = skill_registry.get_skill_files(target_skill_id)
                    if skill_files:
                        plan_result = generator.plan_modification(chat_request.message, skill_files["manifest"], skill_files["code"])
                    else:
                        plan_result = {"success": False, "error": f"Could not read files for skill '{target_skill_id}'"}
                else:
                    plan_result = generator.plan(chat_request.message)

                if not plan_result["success"]:
                    response_text = f"I tried to plan a skill {action_label} but hit an issue: {plan_result.get('error')}"
                else:
                    pending_plans = _load_pending_plans()
                    plan_data = {
                        "user_request": plan_result["user_request"],
                        "skill_id": plan_result["skill_id"],
                        "plan_text": plan_result["plan_text"]
                    }
                    if is_modify:
                        plan_data["action"] = "modify"
                        plan_data["target_skill_id"] = target_skill_id
                    pending_plans[thread_id] = plan_data
                    _save_pending_plans(pending_plans)

                    verb = "modify" if is_modify else "build"
                    response_text = (
                        f"Here's my plan for this skill {action_label}:\n\n"
                        f"{plan_result['plan_text']}\n\n"
                        f"---\n"
                        f"**Shall I go ahead and {verb} this?** (yes/no)"
                    )

            else:
                # TOOL-USE FLOW with streaming
                provider = get_llm()
                system_prompt = load_system_prompt()
                if knowledge_context:
                    system_prompt += f"\n\n## Relevant Knowledge\n{knowledge_context}"

                messages = conversation_manager.load_context(thread_id)
                log = LogEvent(type="thought", subtype="history", message=f"Loaded {len(messages)} messages from conversation history.")
                logs.append(log)
                yield f"data: {json.dumps({'type': 'log', 'event': log.model_dump()})}\n\n"

                available_skills = skill_registry.list_skills()
                tools = build_tool_definitions(available_skills)

                log = LogEvent(type="thought", subtype="tools", message=f"Prepared {len(tools)} tools ({len(available_skills)} skills registered).")
                logs.append(log)
                yield f"data: {json.dumps({'type': 'log', 'event': log.model_dump()})}\n\n"

                # Run tool loop in thread, streaming logs via queue
                streamed_logs = []

                # Use ThreadPoolExecutor to run sync code
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        run_tool_loop,
                        provider=provider,
                        tool_executor=tool_executor_instance,
                        messages=messages,
                        tools=tools,
                        system_prompt=system_prompt,
                        max_tokens=1024,
                        on_log=on_log
                    )

                    # Consume logs from queue until task completes
                    while not future.done():
                        try:
                            # Use timeout to periodically check if future is done
                            event_type, event_data = log_queue.get(timeout=0.1)
                            if event_type == "log":
                                streamed_logs.append(event_data)
                                yield f"data: {json.dumps({'type': 'log', 'event': event_data.model_dump()})}\n\n"
                        except queue.Empty:
                            # Allow async event loop to process
                            await asyncio.sleep(0)
                            continue

                    # Drain remaining logs
                    while not log_queue.empty():
                        try:
                            event_type, event_data = log_queue.get_nowait()
                            if event_type == "log":
                                streamed_logs.append(event_data)
                                yield f"data: {json.dumps({'type': 'log', 'event': event_data.model_dump()})}\n\n"
                        except queue.Empty:
                            break

                    # Get the result (raises if exception occurred)
                    loop_result = future.result()
                    response_text = loop_result.text

                # Add streamed logs to main logs list (they were already yielded)
                logs.extend(streamed_logs)

            # Save response
            conversation_manager.save_message(thread_id, "assistant", response_text)

            # Knowledge extraction (skip if save_knowledge was called)
            save_knowledge_called = any(
                log.subtype == "tool_call" and
                log.metadata and
                log.metadata.get("tool_name") == "save_knowledge"
                for log in logs
            )

            if not save_knowledge_called:
                try:
                    extractor = get_extractor()
                    extraction = extractor.extract_updates(
                        user_message=chat_request.message,
                        assistant_response=response_text,
                        knowledge_context=knowledge_context
                    )

                    if extraction["updates"]:
                        for update in extraction["updates"]:
                            update_fields = update.get("fields") or {}
                            related_files = update_fields.pop("related_files", None)
                            knowledge_manager.find_or_create_entry(
                                template_type=update["template_type"],
                                identifier=update["identifier"],
                                content=update.get("content"),
                                tags=update.get("tags", []),
                                fields=update_fields if update_fields else None,
                                related_files=related_files
                            )
                except Exception:
                    pass  # Non-critical for streaming

            log = LogEvent(type="thought", subtype="done", message="Response generated successfully.")
            logs.append(log)
            yield f"data: {json.dumps({'type': 'log', 'event': log.model_dump()})}\n\n"

            # Final response
            yield f"data: {json.dumps({'type': 'response', 'text': response_text, 'thread_id': thread_id, 'reasoning': _build_reasoning(logs), 'logs': [l.model_dump() for l in logs]})}\n\n"

        except Exception as e:
            log = LogEvent(type="error", subtype="stream", message=str(e))
            logs.append(log)
            yield f"data: {json.dumps({'type': 'log', 'event': log.model_dump()})}\n\n"
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/threads", response_model=ThreadListResponse)
def list_threads(limit: int = 50, offset: int = 0) -> ThreadListResponse:
    """List all conversation threads with lightweight metadata."""
    summaries = conversation_manager.list_threads(limit=limit, offset=offset)
    return ThreadListResponse(threads=summaries)


@app.get("/thread/{thread_id}", response_model=ThreadResponse)
def get_thread(thread_id: str) -> ThreadResponse:
    """Load a full conversation thread by ID."""
    if not conversation_manager.thread_exists(thread_id):
        raise HTTPException(status_code=404, detail="Thread not found")
    json_path, _ = conversation_manager._get_thread_paths(thread_id)
    thread_data = json.loads(json_path.read_text(encoding="utf-8"))
    return ThreadResponse(
        id=thread_data["id"],
        created_at=thread_data["created_at"],
        messages=thread_data.get("messages", [])
    )


def _extract_date_prefix(thread_id: str) -> Optional[str]:
    """Extract the date prefix from a thread ID.
    'thread_20260130_...' → 'thread_20260130'
    't_260130_...'        → 't_260130'
    """
    m = re.match(r'^(thread_\d{8})_', thread_id) or re.match(r'^(t_\d{6})_', thread_id)
    return m.group(1) if m else None


class RenameRequest(BaseModel):
    """Request body for renaming a thread."""
    old_thread_id: str
    new_name: str  # just the suffix after t_YYMMDD_


@app.post("/thread/rename")
def rename_thread(req: RenameRequest):
    """Rename a thread by replacing its suffix while keeping the date prefix."""
    old_prefix = _extract_date_prefix(req.old_thread_id)
    if not old_prefix:
        raise HTTPException(400, "Invalid thread ID format")
    new_id = f"{old_prefix}_{req.new_name}"
    try:
        conversation_manager.rename_thread(req.old_thread_id, new_id)
    except FileNotFoundError:
        raise HTTPException(404, "Thread not found")
    except FileExistsError:
        raise HTTPException(409, "Name already taken")
    # Migrate pending plans
    plans = _load_pending_plans()
    if req.old_thread_id in plans:
        plans[new_id] = plans.pop(req.old_thread_id)
        _save_pending_plans(plans)
    return {"success": True, "new_thread_id": new_id}


# Static file serving for production (built PWA)
UI_DIST_DIR = Path(__file__).parent / "ui" / "dist"

if UI_DIST_DIR.exists():
    # Mount static assets (JS, CSS, icons)
    app.mount("/assets", StaticFiles(directory=UI_DIST_DIR / "assets"), name="assets")
    app.mount("/icons", StaticFiles(directory=UI_DIST_DIR / "icons"), name="icons")


@app.exception_handler(404)
async def _spa_fallback(request: Request, exc):
    """Serve the SPA for non-API 404s; return JSON 404 for API routes."""
    if UI_DIST_DIR.exists():
        path = request.url.path.lstrip('/')
        first_seg = path.split('/')[0] if path else ''
        if first_seg not in ('chat', 'rollback', 'threads', 'thread', 'api'):
            file_path = UI_DIST_DIR / path
            if path and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(UI_DIST_DIR / "index.html")
    return JSONResponse({"detail": "Not Found"}, status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
