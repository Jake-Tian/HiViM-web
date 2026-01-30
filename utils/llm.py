from openai import OpenAI

_TOKEN_TOTAL = 0


def add_tokens(token_count):
    """Add tokens to a simple global counter."""
    global _TOKEN_TOTAL
    if token_count:
        _TOKEN_TOTAL += token_count


def reset_token_counter():
    """Reset the global token counter to zero."""
    global _TOKEN_TOTAL
    _TOKEN_TOTAL = 0


def get_token_counter():
    """Get the current global token counter."""
    return _TOKEN_TOTAL

def generate_text_response(prompt):
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    total_tokens = getattr(response.usage, "total_tokens", 0) if response.usage else 0
    add_tokens(total_tokens)
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("OpenAI API returned None content. The response may have been filtered or empty.")
    return content, total_tokens

def get_embedding(text):
    client = OpenAI()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text, 
    )
    return response.data[0].embedding

def get_multiple_embeddings(texts):
    client = OpenAI()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts, 
    )
    return [response.data[i].embedding for i in range(len(response.data))]