from langchain_core.prompts import ChatPromptTemplate


RAG_PROMPT = ChatPromptTemplate.from_template("""
You are an evidence-based AI assistant.

Answer the user's question using ONLY the provided context.

If the context does not contain enough information to answer the question,
say that the information is not available in the provided documents.

Do not invent facts.

Context:
{context}

Question:
{question}

Answer:
""")