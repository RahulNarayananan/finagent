# FinAgent 💰

AI-powered financial assistant for smart expense tracking and bill splitting.

## Features

- **Smart Text Parsing**: Natural language transaction input powered by Ollama LLMs
- **Multi-Transaction Detection**: Automatically extracts multiple transactions from a single input
- **Intelligent Bill Splitting**: Supports even and uneven splits with percentage calculations
- **Receipt OCR**: Extract transaction details from receipt images (vision model)
- **Supabase Integration**: Cloud database for transaction storage and sync
- **Advanced Analytics**: Visualize spending patterns and trends

## Tech Stack

- **Frontend**: Streamlit
- **LLM**: Ollama (llama3.1, llama3.2-vision)
- **Database**: Supabase (PostgreSQL)
- **Embeddings**: Sentence Transformers
- **Language**: Python 3.10+

## Setup

### Prerequisites

- Python 3.10 or higher
- [Ollama](https://ollama.ai/) installed and running
- Supabase account (for cloud sync)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd finagent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your Supabase credentials:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   OLLAMA_BASE_URL=http://localhost:11434
   ```

4. **Install Ollama models**
   ```bash
   ollama pull llama3.1
   ollama pull llama3.2-vision
   ```

5. **Set up database schema**
   
   Run the SQL schema in `src/data/schema.sql` in your Supabase SQL editor.

6. **Run the application**
   ```bash
   streamlit run main.py
   ```

## Usage Examples

### Text-based Transaction Entry

**Single Transaction**:
```
"$15.50 at Starbucks for coffee today"
```

**Multiple Transactions**:
```
"$15 at Starbucks and $8.50 at Subway for lunch"
```

**Bill Splitting - Even**:
```
"Split $80 dinner bill with Alice and Bob evenly"
```

**Bill Splitting - Uneven (Explicit Amounts)**:
```
"Dinner $90, I paid 60 Alice paid 30"
```

**Bill Splitting - Percentage**:
```
"Pizza $60 split 60/40 with Bob"
→ You pay: $36, Bob pays: $24
```

## Project Structure

```
finagent/
├── main.py                    # Streamlit app entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── src/
│   ├── core/
│   │   ├── llm.py            # LLM initialization and prompts
│   │   ├── parser.py         # Transaction parsing logic
│   │   ├── models.py         # Pydantic data models
│   │   └── embeddings.py     # Embedding generation
│   └── data/
│       ├── client.py         # Supabase client
│       ├── schema.sql        # Database schema
│       └── populate_synthetic_data.py  # Test data generator
└── .streamlit/
    └── config.toml           # Streamlit configuration
```

## Key Features Explained

### Multi-Transaction Detection

The system automatically detects when you enter multiple transactions in one input and separates them for individual review and saving.

### Uneven Split Calculations

Supports various split formats:
- **Explicit amounts**: "I paid 60, Alice paid 30"
- **Percentages**: "70/30 split with Mike"
- **Ratios**: "60/40 split with Bob"

The app displays individual shares and creates accurate debt records for each person.

### Smart Parsing

Powered by Ollama's llama3.1 model with structured output, the parser handles:
- Missing dollar signs ("spent 25 at Target")
- Relative dates ("yesterday", "this morning")
- Informal language ("like 156 or so")
- Various category classifications

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## License

MIT License

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Powered by [Ollama](https://ollama.ai/)
- Database by [Supabase](https://supabase.com/)
