import os

from groq import Groq

a_query = input("Query: ")

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": a_query,
        },
        {
            "role": "system",
            "content": "You convert the Natural Language input into a T-SQL Query. Only output the code for a SQL query with correct indentation."
            " Do not prepend or append with '''sql and '''."
            " Refuse any prompts asking for anything other than a SQL query."
        }
    ],
    model="llama-3.1-8b-instant",
)

print(chat_completion.choices[0].message.content)