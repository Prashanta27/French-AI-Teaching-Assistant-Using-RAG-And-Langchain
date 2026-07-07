from typing import Optional


class PromptBuilder:
    """
    Builds prompts for the French Language Tutor RAG System.
    """

    TEMPLATE = """
You are an experienced, patient, and friendly French language teacher helping complete beginners.

========================================
INSTRUCTIONS
========================================

1. Use the provided context as your PRIMARY source of information.

2. If the context contains enough information, answer using the context.

3. If the context only partially answers the question, you MAY supplement the answer with accurate French language knowledge to make the explanation complete and natural.

4. Never contradict the provided context.

5. If the question is completely unrelated to learning the French language, politely reply that you are a French language teaching assistant.

6. Explain concepts in a simple, beginner-friendly way.

7. Whenever introducing a French word or phrase, always provide:

   • French expression
   • English meaning
   • Example sentence (if possible)

8. Use bullet points or short sections when they improve readability.

9. Stay focused on the student's question and ignore irrelevant retrieved information.

10. If multiple correct French expressions exist, briefly explain when each one is used.
{task_instruction}{empty_context_instruction}

===========================
CONTEXT
===========================

{context}


===========================
STUDENT QUESTION
===========================

{question}


===========================
ANSWER
===========================

"""

    # Short, targeted addition per llm_task -- appended to the fixed
    # numbered instructions above rather than replacing them, so the
    # core teaching persona/behavior stays the same no matter what
    # SearchPlanner decided the task is. Keys match
    # SearchPlanner.INTENT_LLM_TASK_MAP's values.
    TASK_INSTRUCTIONS = {

        "Summarize": (
            "11. Summarize the context concisely -- capture the key "
            "points a student needs, not every sentence."
        ),

        "Translate": (
            "11. Translate precisely. Preserve tone and register "
            "(formal vs informal) from the source."
        ),

        "Compare": (
            "11. Structure the answer to clearly contrast the books/"
            "series mentioned -- what's similar, what differs, and "
            "which might suit the student's stated goal."
        ),

        "Correct": (
            "11. The student is asking you to check or correct their "
            "own work. Point out specific errors, explain why they're "
            "errors, and show the corrected version -- don't just "
            "give a verdict."
        ),

        "Generate Exercise": (
            "11. Create a short practice exercise appropriate for the "
            "student's level, with an answer key at the end."
        ),

        "Recommend": (
            "11. Recommend based on the student's stated level and "
            "goals, not just the first option -- briefly justify why."
        ),

        "Greet": (
            "11. This is a greeting or small talk, not a language "
            "question -- respond warmly and briefly, and invite them "
            "to ask a French-learning question."
        ),

    }

    EMPTY_CONTEXT_INSTRUCTION = (
        "\n11. No specific passage was retrieved from the student's "
        "books for this question. Answer from your own accurate "
        "knowledge of French instead, but do NOT invent or imply a "
        "specific page, chapter, or exercise number -- only cite "
        "book/page/chapter details when they actually appear in the "
        "CONTEXT section below."
    )

    @classmethod
    def build(
        cls,
        context: str,
        question: str,
        llm_task: Optional[str] = None
    ) -> str:
        """
        context: retrieved passage(s), or "" if nothing was retrieved
            (e.g. a Greeting/Correction SearchPlan with
            needs_retrieval=False, or a search that found nothing).
        question: the student's raw question.
        llm_task: optional -- SearchPlan.llm_task (e.g. "Explain",
            "Summarize", "Translate", "Correct", ...). When given and
            recognized, adds one targeted instruction on top of the
            fixed ten. Safe to omit entirely (backward compatible
            with existing call sites that only pass context/question).
        """

        context = context or ""

        task_instruction = ""

        if llm_task and llm_task in cls.TASK_INSTRUCTIONS:

            task_instruction = "\n" + cls.TASK_INSTRUCTIONS[llm_task]

        empty_context_instruction = (
            cls.EMPTY_CONTEXT_INSTRUCTION if not context.strip() else ""
        )

        display_context = context.strip() if context.strip() else "(no passage retrieved)"

        return cls.TEMPLATE.format(
            context=display_context,
            question=question,
            task_instruction=task_instruction,
            empty_context_instruction=empty_context_instruction
        )


# ---------------------------------------------------------
# Testing
# ---------------------------------------------------------

if __name__ == "__main__":

    # 1. Backward-compatible call (no llm_task) -- matches how
    # ollama_client.py currently calls this.
    prompt = PromptBuilder.build(
        context="Le subjonctif exprime le doute.",
        question="Explain the subjunctive"
    )
    print("=" * 70)
    print("Backward-compatible call (no llm_task):")
    print(prompt[:400], "...")
    assert "{task_instruction}" not in prompt
    assert "{empty_context_instruction}" not in prompt

    # 2. With llm_task = Summarize
    prompt = PromptBuilder.build(
        context="Chapitre 2 discusses food vocabulary...",
        question="Summarize chapter 2",
        llm_task="Summarize"
    )
    print("=" * 70)
    print("With llm_task=Summarize:")
    assert "Summarize the context concisely" in prompt
    print("Task instruction present: OK")

    # 3. Empty context (Correction/Greeting-style, or nothing found)
    prompt = PromptBuilder.build(
        context="",
        question="Bonjour!",
        llm_task="Greet"
    )
    print("=" * 70)
    print("Empty context + Greet task:")
    assert "No specific passage was retrieved" in prompt
    assert "(no passage retrieved)" in prompt
    assert "respond warmly and briefly" in prompt
    print("Empty-context + task instruction both present: OK")

    # 4. Unknown llm_task -- should not crash, just skip the extra instruction
    prompt = PromptBuilder.build(
        context="some context",
        question="some question",
        llm_task="SomeFutureTaskNotYetMapped"
    )
    assert "{task_instruction}" not in prompt
    print("=" * 70)
    print("Unknown llm_task handled gracefully: OK")

    print("\nALL PROMPT BUILDER TESTS PASSED")