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

Settings: top-k = 3, `MIN_SCORE` = 0.30, temperature = 0.

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

## Test results

Run of `python test_rag.py` (`MIN_SCORE = 0.30`):

| # | Type | Question | Expected ID | Retrieved IDs (score) | Answer | Correct? | Failed at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Answerable | How do I get to Cat Ba Island from the city? | G01 | G01 (0.62), G14 (0.56), G13 (0.46) | Bus or car across the Tan Vu - Lach Huyen bridge to Got pier, then the car ferry to Cai Vieng (15-20 minutes) [G01] | Yes | - |
| 2 | Answerable | When do the red flamboyant flowers bloom? | G11 | G11 (0.62), G12 (0.35), G16 (0.29) | May and June [G11] | Yes | - |
| 3 | Answerable | What is banh da cua? | G08 | G08 (0.50), G09 (0.50), G10 (0.42) | Crab noodle soup [G08] | Yes | - |
| 4 | Answerable | When is the Do Son buffalo fighting festival? | G16 | G16 (0.78), G11 (0.40), G04 (0.36) | On the 9th day of the 8th lunar month, usually in September [G16] | Yes | - |
| 5 | Paraphrase | Where can I see rare monkeys with golden heads? | G03 | G03 (0.44), G07 (0.28), G11 (0.26) | Cat Ba National Park [G03] | Yes | - |
| 6 | Not in guide | How much is a ticket to the Opera House? | - | G05 (0.38), G09 (0.26), G07 (0.26) | I don't know | Yes | - |
| 7 | Not in guide | What is the best hospital in the city? | - | G07 (0.28), G11 (0.23), G14 (0.22) | I don't know | Yes | - |
| 8 | Answerable (two entries) | How long does it take to go from Hanoi to Cat Ba? | G13 + G01 | G13 (0.57), G01 (0.49), G14 (0.48) | I don't know | No | Generation: both needed entries were retrieved (1.5-2 h Hanoi to Hai Phong in G13, ferry 15-20 min in G01), but the model refused instead of combining them |

Row 8 is a harder question that needs two entries; it is the failure shown in the video.

**Design decision: `MIN_SCORE`.** The weakest answerable question scored 0.44 (row 5) and the
strongest off-guide question scored 0.28 (row 7). A threshold of 0.30 sends row 7 straight to
"I don't know" without calling the chat model, while every answerable question passes.

**Two layers of "I don't know".** Row 7 is stopped by the score threshold (0.28 < 0.30), so the
chat model is never called. Row 6 passes the threshold (G05 scores 0.38 because it is about the
Opera House) but G05 contains no ticket price, so the model itself replies "I don't know".

## Known limitations

- The guide has only 16 entries; anything outside them is answered with "I don't know".
- `MIN_SCORE` was checked on 8 questions only. Row 7 is below the threshold by just 0.02, so a
  similar off-guide question may pass it and rely on the prompt rule alone.
- Questions that need facts from two entries (row 8) are often refused: the model does not
  combine partial facts into one answer.
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
to diagnose why `qwen3:4b` answers were cut off (reasoning tokens filling `num_predict`), to
draft the 16 Hai Phong guide entries, and to help choose test questions and `MIN_SCORE` from
the test results.