"""Evaluator-optimizer pattern: a second LLM call checks each reply before the visitor sees it.
If the reply fails, the twin regenerates with the evaluator's feedback."""

from pydantic import BaseModel

EVALUATOR_MODEL = "gpt-5.4-mini"


class Evaluation(BaseModel):
    is_acceptable: bool
    feedback: str


def _evaluator_system_prompt(name: str, context: str) -> str:
    return f"""You are a strict quality evaluator for an AI digital twin of {name}.
The twin chats with visitors (recruiters, clients, employers) on {name}'s website.

Judge the twin's latest reply. It is NOT acceptable if it:
- states facts about {name} that are not supported by the context below (hallucination),
- is rude, unprofessional, or off-brand for a senior engineer,
- answers unrelated topics instead of steering back to career,
- claims to be a human, or denies being an AI when asked,
- is unnecessarily long or ignores the visitor's actual question.

Context the twin had access to:
{context}
"""


def evaluate(client, name: str, context: str, reply: str, message: str, history: list[dict]) -> Evaluation:
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in history[-8:])
    user_prompt = (
        f"Conversation so far:\n{convo}\n\n"
        f"Latest visitor message:\n{message}\n\n"
        f"Twin's reply:\n{reply}\n\n"
        "Is this reply acceptable? Give short, actionable feedback."
    )
    try:
        resp = client.chat.completions.parse(
            model=EVALUATOR_MODEL,
            messages=[
                {"role": "system", "content": _evaluator_system_prompt(name, context)},
                {"role": "user", "content": user_prompt},
            ],
            response_format=Evaluation,
        )
        return resp.choices[0].message.parsed
    except Exception as e:  # if the evaluator fails, don't block the visitor
        print(f"Evaluator error: {e}")
        return Evaluation(is_acceptable=True, feedback=f"evaluator unavailable: {e}")
