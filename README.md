# Lumen Travel Assistant — Da Nang

**Student:** Trần Kiên Cường — 25127025 — 25C09 <br>
**City:** Da Nang, Vietnam <br>
**Demo video:** WIP

A Streamlit travel assistant for Da Nang. Users sign in with Firebase (email/password).
The chat answers only from `knowledge_base.json` using RAG (`embeddinggemma` for retrieval,
`qwen3:4b` for generation, both on an Ollama server exposed through Pinggy), cites guide IDs
such as [G03], shows the retrieved entries with their scores, and says "I don't know" when the
guide has no answer.d

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
| `knowledge_base.json` | 12 guide entries about Da Nang (`id`, `title`, `text`, `source`; places also have `category` and `tags`) |
| `test_rag.py` | Runs the test questions below and prints retrieved IDs, scores and answers |

Settings: top-k = 3, `MIN_SCORE` = 0.30, temperature = 0.

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

Final run (`MIN_SCORE = 0.30`):

| # | Type | Question | Expected ID | Retrieved IDs (score) | Answer | Correct? | Failed at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Answerable | When does the Dragon Bridge breathe fire? | G01 | G01 (0.64), G11 (0.43), G04 (0.31) | Saturday and Sunday nights at about 9 pm [G01] | Yes | - |
| 2 | Answerable | Where can I buy tailored clothes? | G03 | G03 (0.34), G11 (0.23), G01 (0.22) | Han Market upper floor [G03] | Yes | - |
| 3 | Answerable | Which months are best for the beach? | G04 | G04 (0.66), G02 (0.37), G11 (0.24) | February to August [G04] | Yes | - |
| 4 | Answerable | How much is a ticket to Ba Na Hills? | G08 | G08 (0.53), G05 (0.50), G12 (0.43) | 1,000,000 VND [G08] | Yes | - |
| 5 | Paraphrase | Is there a free show with fire on the river at the weekend? | G01 | G01 (0.56), G11 (0.34), G07 (0.27) | Yes [G01] | Yes | - |
| 6 | Not in guide | What time does Han Market open? | - | G03 (0.57), G11 (0.47), G01 (0.40) | I don't know | Yes | - |
| 7 | Not in guide | What is the best hospital in the city? | - | G02 (0.24), G04 (0.23), G09 (0.21) | I don't know | Yes | - |

Failure found in an earlier run (`MIN_SCORE = 0.35`):

| # | Type | Question | Expected ID | Retrieved IDs (score) | Answer | Correct? | Failed at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2a | Answerable | Where can I buy tailored clothes? | G03 | G03 (0.34), G11 (0.23), G01 (0.22) | I don't know | No | Retrieval: the right entry ranked first, but its score 0.34 was below the 0.35 threshold, so the answer was refused |

**Design decision: `MIN_SCORE`.** The weakest answerable question scored 0.34 (row 2) and the
strongest off-guide question scored 0.24 (row 7). Lowering the threshold from 0.35 to 0.30
separates the two groups and fixed row 2a.

**Two layers of "I don't know".** Row 7 is stopped by the score threshold (0.24 < 0.30), so the
chat model is never called. Row 6 passes the threshold (G03 scores 0.57 because it is about Han
Market) but G03 contains no opening hours, so the model itself replies "I don't know".

## Known limitations

- The guide has only 12 entries; anything outside them is answered with "I don't know".
- `MIN_SCORE` was tuned on 7 questions only. Row 2 passes by just 0.04, so similar questions
  phrased differently may be refused.
- Prices and opening hours in the guide are snapshots from 2026 and can become outdated.
- `qwen3:4b` on the course server always reasons before answering, so replies take several
  seconds; the app sends `think: true` so the reasoning is kept out of the answer.
- Chat history is lost on sign-out or page refresh (by design: no database).
- The Pinggy URL changes on every restart and must be updated in `.env`.

## AI tools used

<Review and edit this note so it is accurate.> Claude (Claude Code) was used to explain the
RAG and Firebase concepts, to produce a study guide with reference code based on Labs 3 and 5,
to diagnose why `qwen3:4b` answers were cut off (reasoning tokens filling `num_predict`), and to
help choose `MIN_SCORE` from the test results.
