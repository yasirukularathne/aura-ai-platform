from app.rag.generation.rag_chain import ask_question


question = "What is the refund policy?"

result = ask_question(question)

print("\n================ ANSWER ================\n")

print(result["answer"])


print("\n================ SOURCES ================\n")

for source in result["sources"]:

    print(
        f"Source: {source['source']} | "
        f"Page: {source['page']}"
    )