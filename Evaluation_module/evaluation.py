from Question_generation.Retrivel import retrieve_docs_from_all_collections
import re
import os

def get_evaluation_prompt(question, answer, difficulty, context=None):
    prompt = f"""You are an expert HR interviewer evaluating candidate responses.

            Question: {question}
            Candidate's Answer: {answer}
            Difficulty Level: {difficulty}

            """
    if context:
        prompt += f"Extract Sample Answer/Guidelines:\n{context}\n\n"
    
    prompt += """Please evaluate the response on the following criteria:
        1. Relevance to the question (How well the answer addresses the question)
        2. Clarity and articulation
        3. Depth of response
        4. Professional attitude
        5. Examples and specifics provided (if applicable)

        Provide:
        1. Score (0-10)
        2. Brief explanation of the score
        3. Areas of improvement (if any)
        4. Give the context of the question and answer in your evaluation.

        Format your response as:
        <score>number</score>
        <reason>explanation</reason>
        <improvement>suggestions</improvement>
        <context>contextual information</context>"""
    
    return prompt

def extract_evaluation(eval_text):
    score_match = re.search(r'<score>(.*?)</score>', eval_text, re.DOTALL)
    reason_match = re.search(r'<reason>(.*?)</reason>', eval_text, re.DOTALL)
    improvement_match = re.search(r'<improvement>(.*?)</improvement>', eval_text, re.DOTALL)

    score_str = score_match.group(1).strip() if score_match else "0.0"
    # Handle cases like '8.5', '8', or '8.5/10', '1/10'
    if '/' in score_str:
        try:
            num, denom = score_str.split('/')
            score = float(num) / float(denom) * 10 if float(denom) != 0 else 0.0
        except Exception:
            score = 0.0
    else:
        try:
            score = float(score_str)
        except Exception:
            score = 0.0

    reason = reason_match.group(1).strip() if reason_match else ""
    improvement = improvement_match.group(1).strip() if improvement_match else ""

    return score, reason, improvement

def evaluate_answer(question, answer, difficulty):
    # Try to get relevant context from ChromaDB
    context = retrieve_docs_from_all_collections(question, k=3)
    # context = context[0] if context else None  # Get first matching document if available
    
    # Generate evaluation prompt
    evaluation_prompt = get_evaluation_prompt(question, answer, difficulty, context)
    
    # Prepare messages for LLM
    messages = [
        {
            "role": "system",
            "content": "You are an expert HR interview evaluator. Provide detailed, constructive feedback."
        },
        {
            "role": "user",
            "content": evaluation_prompt
        }
    ]
    
    return messages

