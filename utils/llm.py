from openai import OpenAI

def generate_text_response(prompt):
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("OpenAI API returned None content. The response may have been filtered or empty.")
    return content

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