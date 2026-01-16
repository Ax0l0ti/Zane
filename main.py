import os
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from core.llm import OpenAIProvider
from core.llm.factory import BaseLLM
from core.memory import ConversationManager
from core.routing import IntentDetector
from core.skills import SkillRegistry, SkillExecutor
from core.architect import SkillGenerator
from skills.core_ops.git_tools import GitTools

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Zane",
    description="A stoic, factual AI assistant - your Exocortex",
    version="0.1.0"
)

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

# Initialize skills
SKILLS_DIR = Path(__file__).parent / "skills"
skill_registry = SkillRegistry(SKILLS_DIR)
skill_executor = SkillExecutor(skill_registry)

# Intent detector (initialized lazily after LLM)
intent_detector: Optional[IntentDetector] = None

# Skill generator (initialized lazily after LLM)
skill_generator: Optional[SkillGenerator] = None

# Git tools for safe code modification
ARCHITECT_PROMPT_PATH = PROMPTS_DIR / "architect.md"
git_tools = GitTools(Path(__file__).parent)


def get_llm() -> BaseLLM:
    """Get or initialize the LLM provider."""
    global llm
    if llm is None:
        llm = OpenAIProvider()
    return llm


def get_detector() -> IntentDetector:
    """Get or initialize the intent detector."""
    global intent_detector
    if intent_detector is None:
        intent_detector = IntentDetector(get_llm())
    return intent_detector


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


# Pydantic models
class LogEvent(BaseModel):
    """A single log event for transparency."""
    type: Literal["thought", "tool", "file_io", "error"]
    message: str
    metadata: Optional[dict] = None


class ZaneResponse(BaseModel):
    """The standard response format from Zane."""
    text: str
    thread_id: str
    audio_base64: Optional[str] = None
    logs: list[LogEvent]


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""
    message: str
    thread_id: Optional[str] = None


@app.get("/")
def health_check():
    """Health check endpoint."""
    return {"status": "operational", "name": "Zane", "version": "0.1.0"}


@app.post("/chat", response_model=ZaneResponse)
def chat(request: ChatRequest) -> ZaneResponse:
    """Process a chat message and return Zane's response.

    Uses the Glass Box Router to determine intent (CHAT/SKILL/DEV)
    and routes accordingly with full transparency logging.

    Args:
        request: The chat request containing the user's message.

    Returns:
        ZaneResponse with the assistant's reply and transparency logs.
    """
    logs: list[LogEvent] = []

    # Log the incoming request
    logs.append(LogEvent(
        type="thought",
        message=f"Received message: '{request.message[:50]}...'" if len(request.message) > 50 else f"Received message: '{request.message}'"
    ))

    try:
        # Get or create thread
        thread_id = request.thread_id
        if not thread_id or not conversation_manager.thread_exists(thread_id):
            thread_id = conversation_manager.create_thread()
            logs.append(LogEvent(
                type="file_io",
                message=f"Created new conversation thread: {thread_id}"
            ))
        else:
            logs.append(LogEvent(
                type="file_io",
                message=f"Continuing thread: {thread_id}"
            ))

        # Save user message to thread
        conversation_manager.save_message(thread_id, "user", request.message)
        logs.append(LogEvent(
            type="file_io",
            message="Saved user message to thread (JSON + MD)"
        ))

        # Get providers
        provider = get_llm()
        detector = get_detector()

        # Detect intent (Glass Box Router)
        available_skills = skill_registry.list_skills()
        intent = detector.detect(request.message, available_skills)

        logs.append(LogEvent(
            type="thought",
            message=f"Intent detected: {intent.mode} (confidence: {intent.confidence:.2f})",
            metadata={
                "mode": intent.mode,
                "confidence": intent.confidence,
                "skill_name": intent.skill_name,
                "reasoning": intent.reasoning
            }
        ))

        # Route based on intent
        if intent.mode == "SKILL" and intent.skill_name:
            # Execute skill
            logs.append(LogEvent(
                type="tool",
                message=f"Executing skill: {intent.skill_name}"
            ))

            result = skill_executor.execute(intent.skill_name)

            if result["success"]:
                logs.append(LogEvent(
                    type="tool",
                    message=f"Skill executed successfully",
                    metadata=result["result"]
                ))

                # Format skill result with LLM
                skill_context = f"The user asked: {request.message}\n\nSkill '{intent.skill_name}' returned:\n{result['result']}\n\nProvide a natural response incorporating this information."
                response_text = provider.generate(
                    messages=[{"role": "user", "content": skill_context}],
                    system_prompt=load_system_prompt(),
                    max_tokens=512
                )
            else:
                logs.append(LogEvent(
                    type="error",
                    message=f"Skill failed: {result.get('error', 'Unknown error')}"
                ))
                # Fall back to chat mode
                response_text = f"I attempted to use the {intent.skill_name} skill, but it failed: {result.get('error', 'Unknown error')}. Let me try to help directly."

        elif intent.mode == "DEV":
            # DEV mode - generate a new skill with safety
            logs.append(LogEvent(
                type="thought",
                message="Entering DEV mode: Skill generation with Git safety."
            ))

            # Step 1: Git snapshot
            snapshot_sha = git_tools.snapshot(f"Before generating skill: {request.message[:50]}")
            logs.append(LogEvent(
                type="tool",
                message=f"Git snapshot created: {snapshot_sha[:8]}"
            ))

            # Step 2: Generate skill
            generator = get_generator()
            generated = generator.generate(request.message)

            if not generated["success"]:
                logs.append(LogEvent(
                    type="error",
                    message=f"Skill generation failed: {generated.get('error')}"
                ))
                response_text = f"I attempted to create a skill but failed: {generated.get('error')}"
            else:
                logs.append(LogEvent(
                    type="tool",
                    message=f"Skill generated: {generated['skill_id']}"
                ))

                # Step 3: Save to disk
                saved = generator.save_skill(generated)
                if not saved["success"]:
                    git_tools.rollback()
                    logs.append(LogEvent(
                        type="error",
                        message=f"Failed to save skill, rolled back: {saved.get('error')}"
                    ))
                    response_text = f"Failed to save the skill: {saved.get('error')}. Changes rolled back."
                else:
                    logs.append(LogEvent(
                        type="file_io",
                        message=f"Skill saved to: {saved['path']}"
                    ))

                    # Step 4: Validate
                    validation = generator.validate_skill(Path(saved["path"]))
                    if not validation["valid"]:
                        git_tools.rollback()
                        logs.append(LogEvent(
                            type="error",
                            message=f"Skill validation failed, rolled back: {validation['errors']}"
                        ))
                        response_text = f"The generated skill had errors: {validation['errors']}. Changes rolled back."
                    else:
                        # Step 5: Commit on success
                        commit_sha = git_tools.commit(f"Created skill: {generated['skill_id']}")
                        logs.append(LogEvent(
                            type="tool",
                            message=f"Skill committed: {commit_sha[:8]}"
                        ))

                        # Reload skill registry
                        skill_registry.reload()

                        response_text = f"Successfully created skill '{generated['skill_id']}' at {saved['path']}. The skill is now available for use."

        else:
            # CHAT mode - use LLM directly
            logs.append(LogEvent(
                type="thought",
                message="Processing as CHAT mode."
            ))

            # Load system prompt
            system_prompt = load_system_prompt()

            # Load conversation context from JSON
            messages = conversation_manager.load_context(thread_id)
            logs.append(LogEvent(
                type="thought",
                message=f"Loaded {len(messages)} messages from conversation history."
            ))

            # Generate response
            response_text = provider.generate(
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=1024
            )

        # Save assistant response to thread
        conversation_manager.save_message(thread_id, "assistant", response_text)
        logs.append(LogEvent(
            type="file_io",
            message="Saved assistant response to thread (JSON + MD)"
        ))

        logs.append(LogEvent(
            type="thought",
            message="Response generated successfully."
        ))

        return ZaneResponse(
            text=response_text,
            thread_id=thread_id,
            audio_base64=None,
            logs=logs
        )

    except ValueError as e:
        logs.append(LogEvent(
            type="error",
            message=str(e)
        ))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logs.append(LogEvent(
            type="error",
            message=f"LLM call failed: {str(e)}"
        ))
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
