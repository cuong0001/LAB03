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

### 1. Abstraction

**Input → output of the assistant**

- **Input:** a signed-in user's question (text) and the 16 entries in `knowledge_base.json`.
- **Output:**
  - a short answer that uses only guide facts and cites IDs such as [G03], or "I don't know";
  - the retrieved entries with their similarity scores.

**Fields kept in a guide entry, and why**

| Field | Why it is kept |
| --- | --- |
| `id` | The model cites it ([G03]), and `citation_check` compares cited IDs with retrieved ones |
| `title` | Embedded together with `text`, so a short question like "What is banh da cua?" matches the right entry |
| `text` | The facts the model may use: 2–4 sentences, one topic per entry, so one entry answers one kind of question |
| `source` | Shown in the sources panel and sent with the context, so a user can see where a fact comes from |
| `category`, `tags` (places only) | Added to the embedded text now; RAG-Rec will use them to filter and score places |

**Left out:**
- opening hours, prices and addresses that change often (the bot says "I don't know" instead of guessing);
- photos and long descriptions;
- the user's password, which goes only to Firebase;
- earlier chat turns, because each question is answered from the guide alone.

### 2. Decomposition

```text
[Sign-in] → [Embed] → [Retrieve] → [Build context] → [Generate] → [Display]
```

| Box | Input | Output | Code |
| --- | --- | --- | --- |
| 1. Sign-in | email, password | `user = {uid, email, id_token, expires_at}` or an error message | `firebase_client.sign_in`, `app.auth_form` |
| 2. Embed | 16 entries (once, cached); then each question | 16 × d matrix of vectors; one question vector | `rag.build_index`, `rag.embed` |
| 3. Retrieve | question vector, entry vectors | top 3 entries with cosine scores | `rag.retrieve` |
| 4. Build context | top 3 entries | one text block `[G03] title / text / (Source: …)` | `rag.build_context` |
| 5. Generate | system rule + context + question | answer with [Gxx] citations, or "I don't know" | `rag.generate` |
| 6. Display | answer, top 3 entries | chat message, sources expander with scores, warning for unknown IDs, history in `st.session_state` | `app.show_message`, `app.show_sources` |

Between boxes 3 and 4 there is a check: if the best score is below `MIN_SCORE`, the app skips boxes 4–5 and displays "I don't know".

**Example: "Where can I see rare monkeys with golden heads?" (test row 5)**

1. Sign-in: the chat page opens for the signed-in email.
2. Embed: the question becomes one vector. The guide was embedded at start-up.
3. Retrieve: G03 (0.44), G07 (0.28), G11 (0.26). G03 is found although the question says "monkeys with golden heads", not "langur".
4. Build context: the three entries are joined into one text block with their IDs and sources.
5. Generate: "Cat Ba National Park [G03]".
6. Display: the answer appears with the three entries and scores. G03 was retrieved, so there is no warning.

### 3. Pattern recognition

**Reused from the labs**

| From | What was reused | Where |
| --- | --- | --- |
| Lab 3 | Firebase REST sign-up and sign-in, error code → message, `.env` loading, `st.session_state` for the user | `firebase_client.py`, `config.py`, `app.py` |
| Lab 4 | The Ollama server notebook exposed through Pinggy; its URL is kept in `.env` | `.env`, `config.py` |
| Lab 5 | Server check (`/api/tags`), `embed`, `retrieve`, `build_context`, `generate`, `citation_check`, and the "use only the context" prompt | `rag.py` |

**Where filter → score → top-k appears**

| Step | In this assignment (`rag.retrieve`) | In RAG-Rec |
| --- | --- | --- |
| Filter | Keep the entries of one `category`. The parameter exists; the chat uses all 16 | Keep only places that match what the user wants (e.g. category = beach, or a tag) |
| Score | Cosine similarity between the question and each entry | Similarity between the user's preferences and each place, as in the Lab 6 `ContentBasedRecommender` |
| Top-k | The 3 highest scores go to the model | The k best places are recommended, then explained by the RAG chat |

**Other patterns:**
- A threshold decides "I don't know".
- `@st.cache_resource` caches the guide index, so the guide is embedded only once.
- A regex plus a set difference checks the citations.

### 4. Algorithm design

```text
answer(question, guide, V):            # V = entry vectors, embedded once
    if question is empty: warn "Please type a question first", stop
    q      ← embed(question)
    scores ← cosine(q, V[i]) for every entry i
    hits   ← the 3 entries with the highest scores
    if scores of hits[0] < MIN_SCORE (0.30):
        return "I don't know", hits    # layer 1: nothing in the guide is close
    context ← "[id] title / text / (Source: …)" for each hit
    reply   ← qwen3:4b(SYSTEM rule, context, question)
                                       # layer 2: the rule says "I don't know" if the fact is missing
    unknown ← cited IDs in reply − IDs of hits
    show reply, hits with scores, and a warning if unknown is not empty
```

**Design decision: the "I don't know" rule (`MIN_SCORE` = 0.30), with real examples**

- "Where can I see rare monkeys with golden heads?" has the weakest score among the answerable questions: 0.44, which passes.
- "What is the best hospital in the city?" scores 0.28, which is below 0.30. The app answers "I don't know" without calling the model.
- "How much is a ticket to the Opera House?" retrieves G05 with 0.38 and passes the threshold. G05 has no price, so the system rule makes the model answer "I don't know".

So two layers are needed. The threshold alone would let the Opera House question through, and the prompt rule alone would call the model for every off-guide question.

Other choices:
- **k = 3:** enough for the two-entry question in row 8 (G13 and G01 are both in the top 3), while keeping the prompt short.
- **Temperature 0.1:** explained under Test results.

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
| 8 | Answerable (two entries) | How long does it take to go from Hanoi to Cat Ba? | G13 + G01 | G13 (0.57), G01 (0.49), G14 (0.48) | 1.5 to 2 hours and 15 to 20 minutes [G13, G01] | Partly | Generation: both entries were retrieved, but the answer only lists the two times and leaves out the drive from the city across the bridge to Got pier. In an earlier run with the same retrieval the model answered "I don't know", so the result is not stable |

Row 8 is a harder question that needs two entries; it is the failure shown in the video.

**Design decision: `MIN_SCORE`.** The weakest answerable question scored 0.44 (row 5) and the
strongest off-guide question scored 0.28 (row 7). A threshold of 0.30 sends row 7 straight to
"I don't know" without calling the chat model, while every answerable question passes.

**Two layers of "I don't know".** Row 7 is stopped by the score threshold (0.28 < 0.30), so the
chat model is never called. Row 6 passes the threshold (G05 scores 0.38 because it is about the
Opera House) but G05 contains no ticket price, so the model itself replies "I don't know".

**Design decision: temperature 0.1 instead of 0.** With temperature 0 (always the most likely
token), `qwen3:4b` sometimes repeated the same reasoning until it hit `num_predict`, for example
on "best time to visit hai phong?". The answer was then empty, and the app kept loading until the
timeout. Abandoned requests also kept running on the Ollama server and blocked later questions.
A small amount of randomness (0.1, with Qwen's recommended top_p = 0.95 and top_k = 20) lets
the model break out of a repeat while answers stay almost the same between runs. Facts are kept
to the guide by retrieval, the system prompt and `MIN_SCORE`, not by the temperature.

## Known limitations

- The guide has only 16 entries; anything outside them is answered with "I don't know".
- `MIN_SCORE` was checked on 8 questions only. Row 7 is below the threshold by just 0.02, so a
  similar off-guide question may pass it and rely on the prompt rule alone.
- Questions that need facts from two entries (row 8) are answered only partly or refused, and
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