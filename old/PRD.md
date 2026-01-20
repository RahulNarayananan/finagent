# Product Requirements Document: FinAgent

| Metadata | Details |
| :--- | :--- |
| **Project Name** | FinAgent (Autonomous Financial Assistant) |
| **Version** | 1.0 (Draft) |
| **Status** | Planning |
| **Product Owner** | Smridh Varma, Rahul Narayanan |
| **Last Updated** | December 4, 2025 |

## 1. Problem Statement
Personal finance management is currently high-friction and low-insight.
* **The Friction:** Users must manually input data into spreadsheets or apps, leading to abandonment. Optical Character Recognition (OCR) tools are often brittle and require manual correction.
* **The Insight Gap:** Traditional apps use rigid rules (e.g., "Starbucks = Coffee"), missing context. They cannot answer natural language questions like *"Can I afford a trip next month?"* or handle complex social workflows like splitting a bill based on who ate what.

## 2. Product Vision
To build an **AI-native financial assistant** that proactively manages money by understanding unstructured data (emails, texts, images) and engaging in natural language conversations. It shifts the user paradigm from "Data Entry" to "Financial Review."

## 3. Target Audience
* **Primary Persona ("The Busy Optimizer"):** Young professional, tech-savvy, has multiple income streams or frequent social expenses. Values time over penny-pinching but wants accurate data.
* **Secondary Persona ("The Group Spender"):** Frequently dines out or travels with friends; hates the awkward math of splitting bills.

## 4. User Stories

| ID | Capability | User Story |
| :--- | :--- | :--- |
| **US-1** | **Smart Ingest** | As a user, I want to paste a messy email or SMS about a transaction so that it is logged with the correct Amount, Date, Merchant, and Category without manual editing. |
| **US-2** | **Visual Log** | As a user, I want to snap a photo of a physical receipt so that line items are extracted automatically. |
| **US-3** | **Bill Split** | As a user, I want to assign specific receipt items to friends (e.g., "Alice had the beer") so that the agent calculates who owes what automatically. |
| **US-4** | **Sub Scout** | As a user, I want the system to auto-identify recurring charges (like Netflix) so I can see my fixed monthly burn rate. |
| **US-5** | **RAG Chat** | As a user, I want to ask natural questions (e.g., "How much did I spend on dining last month?") and get answers based on my actual database. |

## 5. Functional Requirements (The "What")

### 5.1 Core Agent Loop (The Brain)
* **FR-01:** System must utilize a Large Language Model (GPT-4o) to parse unstructured text inputs.
* **FR-02:** System must enforce strict schema validation (via Pydantic) to ensure no "hallucinated" fields enter the database.
* **FR-03:** System must utilize **Vector Embeddings** to categorize new merchants based on semantic similarity to past transactions (e.g., "Spotify" vector is close to "Apple Music" → Category: Subscriptions).

### 5.2 Multi-Modal Ingest (The Eyes)
* **FR-04:** System must accept image inputs (JPG/PNG).
* **FR-05:** System must extract individual line items, quantities, and prices, not just the total sum.
* **FR-06:** System must provide a **Human-in-the-Loop** confirmation step if the AI's confidence in reading the receipt is low or if the total does not match the sum of items.

### 5.3 Social Splitting (The Logic)
* **FR-07:** System must maintain a "Friends" list.
* **FR-08:** System must allow users to select which friend pays for which line item (or split shared items evenly).
* **FR-09:** System must generate a summary of "Debts" (e.g., "Alice owes you $15.50").

### 5.4 Analytics & Storage
* **FR-10:** Data must be stored in a relational database (Supabase/Postgres) for financial accuracy.
* **FR-11:** Unstructured fields (Merchant Name, Notes) must have corresponding Vector Embeddings stored for RAG retrieval.

## 6. Non-Functional Requirements

* **NFR-01 Privacy:** No raw receipt images are permanently stored. Only extracted JSON data is kept.
* **NFR-02 Latency:** Text parsing must complete in <5 seconds. Image analysis must complete in <15 seconds.
* **NFR-03 Accuracy:** The Agent must achieve >90% success rate in correctly identifying the "Merchant" and "Total Amount" from clear images.

## 7. AI System Architecture & Constraints

* **Orchestration:** LangChain / LangGraph (Python)
* **Frontend:** Streamlit
* **Database:** Supabase (PostgreSQL + `pgvector`)
* **LLM Provider:** OpenAI (GPT-4o for Vision/Complex Logic, GPT-4o-mini for simple categorization).
* **Deployment:** Docker container on Google Cloud Platform (Cloud Run).

## 8. Success Metrics (KPIs)

* **Categorization Accuracy:** % of transactions where the user did *not* manually edit the Category field.
* **Parse Success Rate:** % of receipt images that result in a valid JSON object without crashing.
* **Query Resolution:** % of "Chat" questions that receive a SQL-backed answer (vs. "I don't know").
