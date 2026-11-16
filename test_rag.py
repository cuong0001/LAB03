"""Run the README test questions and print retrieved IDs + answers."""
import rag

TESTS = [  # (type, question, expected entry ID or "-")
    ("answerable", "How do I get to Cat Ba Island from the city?", "G01"),
    ("answerable", "When do the red flamboyant flowers bloom?", "G11"),
    ("answerable", "What is banh da cua?", "G08"),
    ("answerable", "When is the Do Son buffalo fighting festival?", "G16"),
    ("paraphrase", "Where can I see rare monkeys with golden heads?", "G03"),
    ("not in guide", "How much is a ticket to the Opera House?", "-"),  # topic exists, fact missing
    ("not in guide", "What is the best hospital in the city?", "-"),    # topic missing entirely
    ("paraphrase (statement)", "I want to go trekking in a jungle", "G03"),  # fails: 0.23 < MIN_SCORE
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