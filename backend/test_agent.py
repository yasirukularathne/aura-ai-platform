from app.agents.rag_agent import rag_graph


question = "What is the refund policy?"


result = rag_graph.invoke({
    "question": question
})


print("\n================ ANSWER ================\n")

print(result["answer"])


print("\n================ CITATIONS ================\n")

for citation in result["citations"]:
    print(citation)