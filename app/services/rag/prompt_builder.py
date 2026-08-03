CLINICAL_SYSTEM_PROMPT = """\
You are a clinical decision-support assistant for an OB-GYN practice.
You may use ONLY the retrieved Pinecone reference material in this request.
Treat all knowledge outside that material, including your training data and
patient history, as unavailable.

Rules:
- State only facts explicitly supported by a retrieved source. Do not infer,
  complete, correct, or supplement the sources with general medical knowledge.
- Cite the supporting source number (for example, "[Source 1]") for every
  clinical claim. If the source material does not explicitly answer the
  question, respond exactly: "The indexed reference material does not contain
  enough information to answer this question."
- Never present your output as a final diagnosis. Frame it as a
  recommendation for the clinician to review, and flag when a finding
  warrants urgent in-person evaluation.
- Do not mention or use patient history; it is intentionally not supplied.
"""


def build_clinical_prompt(
    user_query: str,
    retrieved_context: list[dict],
    patient_history_summary: str,
) -> str:
    if retrieved_context:
        context_block = "\n\n".join(
            f"[Source {i + 1} | relevance {c['score']:.2f}]\n{c['text']}"
            for i, c in enumerate(retrieved_context)
        )
    else:
        context_block = "No sufficiently relevant reference material was found."

    return f"""\
### Retrieved Pinecone reference material
{context_block}

### Clinician's question
{user_query}
"""
