"""Run the README test questions and print retrieved IDs + answers."""
import rag

TESTS = [  # (type, question, expected entry ID or "-")
    ("answerable", "When does the Dragon Bridge breathe fire?", "G01"),
    ("answerable", "Where can I buy tailored clothes?", "G03"),
    ("answerable", "Which months are best for the beach?", "G04"),
    ("answerable", "How much is a ticket to Ba Na Hills?", "G08"),
    ("paraphrase", "Is there a free show with fire on the river at the weekend?", "G01"),
    ("not in guide", "What time does Han Market open?", "-"),        # topic exists, fact missing
    ("not in guide", "What is the best hospital in the city?", "-"),  # topic missing entirely
]

rag.check_server()
guide = rag.load_guide()
vectors = rag.build_index(guide)

for kind, question, expected in TESTS:   # sequential, like Lab 5, to spare the server
    reply, hits = rag.answer(question, guide, vectors)
    retrieved = ", ".join(f"{h['id']}({h['score']:.2f})" for h in hits)
    print(f"[{kind}] {question}")
    print(f"  expected: {expected} | retrieved: {retrieved}")
    print(f"  answer: {reply}")
    print(f"  citations: {rag.citation_check(reply, hits)}\n")