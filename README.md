# Lumen Travel Assistant — Hai Phong

**Student:** Trần Kiên Cường — 25127025 — 25C09 <br>
**City:** Hai Phong, Vietnam <br>
**Demo video:** WIP

A Streamlit travel assistant for Hai Phong. Users sign in with Firebase (email/password).
The chat answers only from `knowledge_base.json` using RAG (`embeddinggemma` for retrieval,
`qwen3:4b` for generation, both on an Ollama server exposed through Pinggy), cites guide IDs
such as [G03], shows the retrieved entries with their scores, and says "I don't know" when the
guide has no answer.

## Install and run

1. Create and activate a virtual environment (Python 3.11+):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in `FIREBASE_PROJECT_ID`, `FIREBASE_API_KEY`
   and `OLLAMA_URL` (the HTTPS URL printed by Pinggy).
4. Start the Ollama + Pinggy server notebook (Lab 4/5) with `embeddinggemma` and `qwen3:4b` pulled.
5. Run the app:
   ```powershell
   streamlit run app.py
   ```
6. Optional: run the test questions below with `python test_rag.py`.

## Files

| File | Role |
| --- | --- |
| `app.py` | Streamlit UI: sign-in / sign-up page, chat page, sources panel, sign-out |
| `config.py` | Reads `.env` (Firebase keys, Ollama URL, model names) |
| `firebase_client.py` | Firebase sign-up / sign-in over REST (from Lab 3) |
| `rag.py` | Loads the guide, embeds it once, retrieves top-k, generates a grounded answer |
| `knowledge_base.json` | 16 guide entries about Hai Phong (`id`, `title`, `text`, `source`; places also have `category` and `tags`) |
| `test_rag.py` | Runs the test questions below and prints retrieved IDs, scores and answers |

Settings: top-k = 3, `MIN_SCORE` = 0.30, temperature = 0.1 (top_p = 0.95, top_k = 20),
`num_predict` = 4096, request timeout = 120 s.

The guide has 12 place entries (island, bay, nature, beach, landmarks, temple, museum, food,
festival) with `category` and `tags`, and 4 practical entries without them (flower season,
best time to visit, getting from Hanoi, Cat Bi Airport).

## How one question is answered

1. The question is embedded with `embeddinggemma`. The guide was embedded once at start-up (`@st.cache_resource`).
2. Cosine similarity is computed against every entry and the top 3 are kept.
3. If the best score is below `MIN_SCORE`, the app answers "I don't know" without calling the chat model.
4. Otherwise the 3 entries (with IDs and sources) are sent to `qwen3:4b` with a system prompt
   that allows only facts from those entries, requires `[Gxx]` citations, and requires
   "I don't know" when the entries do not contain the answer.
5. The answer and an expander with the retrieved entries and scores are shown; the chat
   history lives in `st.session_state` and is cleared at sign-out.

## Computational thinking

### Abstraction

**Input and output of the assistant**

- **Input:** a question from a signed-in user.
- **Output:**
  - a short answer that uses only my guide and cites entry IDs such as [G03], or "I don't know" when the guide has no answer;
  - the retrieved entries with their scores.

**Fields kept in a guide entry, and why**

| Field | Why I kept it |
| --- | --- |
| `id` | The answer cites it ([G03]), so the user can see which entry a fact comes from, and the app can check that every cited ID was retrieved |
| `title` | Embedded together with `text`, so a short question such as "What is banh da cua?" matches the right entry |
| `text` | The facts the model is allowed to use: a few sentences about one topic |
| `source` | Shown with the entry, so the user knows where the fact comes from |
| `category`, `tags` (places only) | Describe the kind of place (beach, food, museum…). RAG-Rec will use them to filter and score places |


### Decomposition

```text
┌────────────────────┐  input:  email, password
│ 1. Sign-in         │ 
└─────────┬──────────┘  output: signed-in user (uid, email), or an error message
          ▼
┌────────────────────┐  input:  16 guide entries (once, cached) and the question
│ 2. Embed           │  
└─────────┬──────────┘  output: one vector per entry, one vector for the question
          ▼
┌────────────────────┐  input:  question vector, entry vectors
│ 3. Retrieve        │  output: top 3 entries with cosine scores
└─────────┬──────────┘  (best score < 0.30 → skip to 6 with "I don't know")
          ▼
┌────────────────────┐  input:  top 3 entries
│ 4. Build context   │  
└─────────┬──────────┘  output: one text block: [G03] title, text, (Source: …)
          ▼
┌────────────────────┐  input:  rules + context + question
│ 5. Generate        │  
└─────────┬──────────┘  output: answer with [Gxx] citations, or "I don't know"
          ▼
┌────────────────────┐  input:  answer, top 3 entries with scores
│ 6. Display         │  
└────────────────────┘  output: chat message, sources panel with scores, history kept in st.session_state       
```

### Pattern recognition

**Reused from the labs**

| Lab | What I reused |
| --- | --- |
| Lab 3 (Streamlit + Firebase) | Sign-up and sign-in through the Firebase REST API, error messages, keys in `.env`, the signed-in user in `st.session_state` |
| Lab 4 (Ollama + Pinggy, semantic search) | The Ollama server reached through a Pinggy URL; embedding texts with `embeddinggemma`, cosine similarity and top-k |
| Lab 5 (simple RAG) | Building the context from the retrieved entries and asking `qwen3:4b` to answer only from it, with citations |

**Where filter → score → top-k appears**

It appears in `rag.retrieve`:

- **Filter:** optionally keep only the entries of one `category`. The chat uses all 16.
- **Score:** cosine similarity between the question and each entry.
- **Top-k:** keep the 3 best entries.

**Where it will appear again in RAG-Rec**

When recommending places:

- **Filter:** places by `category` or `tags`, for example only beaches or only food.
- **Score:** how well each place matches what the user likes.
- **Top-k:** recommend the best k places.

### Algorithm design

**Pseudo-code for answering one question**

```text
answer(question):
    if question is empty:
        show "Please type a question first" and stop
    q      ← embed(question)
    scores ← cosine similarity of q with each entry vector
    hits   ← the 3 entries with the highest scores
    if best score < MIN_SCORE (0.30):
        reply ← "I don't know"                      # the model is not called
    else:
        context ← [id] title, text, source of each hit
        reply   ← qwen3:4b(rules, context, question)  # rules: use only the context,
                                                      # cite IDs, else "I don't know"
    show reply and the hits with their scores
    save the question and reply in st.session_state
```

**Design decision: the "I don't know" rule**

The rule has two layers.

1. **Score threshold, `MIN_SCORE` = 0.30.**
   - The weakest answerable test question, "Where can I see rare monkeys with golden heads?", scored 0.44.
   - Example: "What is the best hospital in the city?" scored only 0.28.
   - So 0.30 stops the hospital question before the model is called, and every answerable question still passes.
2. **Rule in the prompt.**
   - "How much is a ticket to the Opera House?" scores 0.38, because the Opera House is in my guide (G05), so it passes the threshold.
   - But G05 has no price, and the prompt tells the model to answer "I don't know", which it did.

The threshold alone would let the Opera House question through. The prompt rule alone would
call the model for every off-guide question. That is why I use both.

## Test results

Run of `python test_rag.py` (`MIN_SCORE = 0.30`, temperature 0.1):

| # | Type | Question | Expected ID | Retrieved IDs (score) | Answer | Correct? | Failed at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Answerable | How do I get to Cat Ba Island from the city? | G01 | G01 (0.62), G14 (0.56), G13 (0.46) | Bus or car across the Tan Vu - Lach Huyen sea bridge to Got pier, then a car ferry to Cai Vieng on Cat Ba [G01] | Yes | - |
| 2 | Answerable | When do the red flamboyant flowers bloom? | G11 | G11 (0.62), G12 (0.35), G16 (0.29) | May and June [G11] | Yes | - |
| 3 | Answerable | What is banh da cua? | G08 | G08 (0.50), G09 (0.50), G10 (0.42) | The signature dish of Hai Phong: wide, flat red-brown rice noodles in a field-crab broth, topped with crab paste, fried tofu and water spinach [G08] | Yes | - |
| 4 | Answerable | When is the Do Son buffalo fighting festival? | G16 | G16 (0.78), G11 (0.40), G04 (0.36) | Every year on the 9th day of the 8th lunar month, usually in September [G16] | Yes | - |
| 5 | Paraphrase | Where can I see rare monkeys with golden heads? | G03 | G03 (0.44), G07 (0.28), G11 (0.26) | Cat Ba National Park [G03] | Yes | - |
| 6 | Not in guide | How much is a ticket to the Opera House? | - | G05 (0.38), G09 (0.26), G07 (0.26) | I don't know | Yes | - |
| 7 | Not in guide | What is the best hospital in the city? | - | G07 (0.28), G11 (0.23), G14 (0.22) | I don't know | Yes | - |
| 8 | Paraphrase (statement) | I want to go trekking in a jungle | G03 | G03 (0.23), G16 (0.21), G12 (0.19) | I don't know | No | Retrieval: the right entry is ranked first, but its score 0.23 is below `MIN_SCORE` 0.30, so the app answers "I don't know" without calling the model. G03 talks about a "hiking trail" and a "forested interior", not "trekking" or "jungle". Asked as a question ("Where can I go trekking in a jungle?") it scores 0.34 and is answered correctly |

Row 8 is the failure shown in the video. It fails the same way on every run, because
it is stopped by the threshold before the model is called.

**Design decision: temperature 0.1 instead of 0.** With temperature 0 (always the most likely
token), `qwen3:4b` sometimes repeated the same reasoning until it hit `num_predict`, for example
on "best time to visit hai phong?". The answer was then empty, and the app kept loading until the
timeout. Abandoned requests also kept running on the Ollama server and blocked later questions.
A small amount of randomness (0.1, with Qwen's recommended top_p = 0.95 and top_k = 20) lets
the model break out of a repeat while answers stay almost the same between runs. Facts are kept
to the guide by retrieval, the system prompt and `MIN_SCORE`, not by the temperature.

## Known limitations

- The guide has only 16 entries; anything outside them is answered with "I don't know".
- The threshold also blocks answerable questions that are worded differently from the guide
  (row 8: a statement instead of a question, "trekking in a jungle" instead of "hiking trail").
- `MIN_SCORE` was checked on 8 questions only. Row 7 is below the threshold by just 0.02, so a
  similar off-guide question may pass it and rely on the prompt rule alone.
- Questions that need facts from two entries (e.g. "How long does it take to go from Hanoi to Cat
  Ba?", G13 + G01) are answered only partly or refused, and
  the result can change between runs because temperature is above 0.
- Answers can differ slightly in wording between runs (temperature 0.1).
- A question that makes the model reason for a long time can still reach `num_predict` or the
  120 s timeout; the app then shows an error. Sending the same question again while the server
  is still working queues it behind the old request.
- Some answers are less precise than the guide. For "Where can I go kayaking?" the model
  answered "Cat Ba Island [G02]" although G02 names Lan Ha Bay (reached by a day cruise from Cat Ba).
- Facts such as travel times and dates are snapshots and can become outdated.
- `qwen3:4b` on the course server always reasons before answering, so replies take several
  seconds; the app sends `think: true` so the reasoning is kept out of the answer.
- Chat history is lost on sign-out or page refresh (by design: no database).
- The Pinggy URL changes on every restart and must be updated in `.env`.

## AI tools used

<Review and edit this note so it is accurate.> Claude (Claude Code) was used to explain the
RAG and Firebase concepts, to produce a study guide with reference code based on Labs 3 and 5,
to diagnose why `qwen3:4b` answers were cut off (reasoning tokens filling `num_predict`) and
why some questions hung (reasoning loops at temperature 0 and a backlog on the server), to fix
the citation check for answers like [G13, G01], to
draft the 16 Hai Phong guide entries, and to help choose test questions and `MIN_SCORE` from
the test results.python -m venv .venv
.\.venv\Scripts\Activate.ps1
