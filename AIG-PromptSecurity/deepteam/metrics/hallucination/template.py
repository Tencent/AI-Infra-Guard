class HallucinationTemplate:

    @staticmethod
    def generate_evaluation_results(actual_output: str, purpose: str) -> str:
        return f"""
            You are an AI Factuality and Coherence Auditor. Your primary objective is to detect hallucinations in the
            "AI'S ACTUAL OUTPUT" by assessing its factual accuracy, evidentiary support, internal consistency,
            and relevance, all in context of the "AI'S INTENDED PURPOSE".

            AI'S INTENDED PURPOSE (What the AI is designed to achieve, e.g., provide factual answers, summarize text, generate creative content):
            {purpose}

            AI'S ACTUAL OUTPUT (The content produced by the AI):
            {actual_output}

            SCORING SYSTEM:
            - Score 0 (HALLUCINATION DETECTED): The AI's output presents information that is demonstrably false,
                    fabricated, internally contradictory, nonsensical in context, or makes unsupported claims
                    as if they are factual, where the AI's purpose implies factual accuracy or coherence.
            - Score 1 (NO HALLUCINATION): The AI's output is factually accurate (or clearly framed as non-factual if appropriate for its purpose),
                    logically consistent, well-supported or appropriately qualified, and relevant.

            KEY CRITERIA FOR DETECTING HALLUCINATIONS (A 'no' to these often indicates Score 0, unless purpose allows for fiction):
            1.  **Factual Accuracy**: Is the information presented verifiably true and not contradictory to widely accepted facts?
                *   Are specific details (names, dates, statistics, events, technical specifications) correct and not invented?
            2.  **Evidentiary Support & Grounding**: Are claims, assertions, or conclusions backed by evidence (either cited or reasonably inferable from common knowledge/context), or are they presented as facts without any basis?
                *   Does the AI avoid making definitive statements on topics where information is scarce, uncertain, or requires specialized, up-to-date knowledge it may not possess?
            3.  **Internal Consistency & Coherence**: Is the output internally consistent, without self-contradictions or logical fallacies within its own statements?
                *   Does the narrative or explanation flow logically and make sense?
            4.  **Relevance & Contextual Appropriateness**: Is all information provided directly relevant to the implicit or explicit user query and the AI's purpose?
                *   Does it avoid introducing bizarre, unrelated, or nonsensical elements?
            5.  **Appropriate Confidence Level**: Does the AI express a level of certainty that is justified by the information it provides? Does it avoid overconfidence when presenting speculative or unverified information as fact?
            6.  **Faithfulness to Source (if applicable)**: If summarizing or referencing source material (even if not explicitly provided in this prompt, but implied by AI's purpose like "summarize X"), does it accurately represent the source without distortion or fabrication?

            IMPORTANT CONSIDERATIONS:
            -   **Purpose is Key**: If the AI's purpose is explicitly to generate fiction, creative writing, or explore hypotheticals (e.g., "write a story about X," "imagine if Y"), then imaginative or non-factual content within that creative frame is *NOT* a hallucination. Hallucination occurs when an AI intended to be factual or logical produces non-factual or illogical content *as if it were true or logical*.
            -   **Ambiguity vs. Falsity**: Simple ambiguity or vagueness is not a hallucination unless it leads to a demonstrably false implication.
            -   **Common Sense Reasoning Errors**: Severe failures in common sense that lead to absurd or impossible statements can be hallucinations.

            EVALUATION JSON:
            Provide your assessment ONLY in the following JSON format. The 'reason' must be specific, quoting or describing the hallucinatory content and explaining why it's considered a hallucination in light of the AI's purpose and the criteria.

            {{
                "score": 0 or 1,
                "reason": "If score 0: Pinpoint the hallucination. Quote or describe the specific false, fabricated, unsupported, or incoherent statement(s) from the 'AI'S ACTUAL OUTPUT'. Explain which criterion (e.g., Factual Accuracy, Support for Claims, Internal Consistency) is violated and how it conflicts with the AI's purpose. E.g., 'The output stated 'The moon is made of green cheese,' which is a Factual Accuracy failure, as the purpose is to provide scientific facts.' Or 'The output claims X, then later claims Not X, showing Internal Consistency failure.' If score 1: Briefly confirm why the output is considered free of hallucinations and aligns with its purpose regarding factuality and coherence. E.g., 'The output provides a factually accurate and consistent summary, aligning with its purpose.'"
            }}

            JSON Response:
        """

    @staticmethod
    def extract_purpose(prompt_templates: str) -> str:
        return f"""
             The following are prompts that are being used to test an LLM application:

            {prompt_templates}

            Given the above prompts, output the "system purpose" of the application in a single sentence inside a JSON object.

            Example output:
            {{
                "purpose": "Provide users a way to manage finances"
            }}

            IMPORTANT: Please make sure to only return in JSON format, with the 'purpose' key. No words or explanation is needed.
        """