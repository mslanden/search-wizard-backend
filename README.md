# Search Wizard: AI Job Posting Creator

An AI-powered system that automates the creation of job postings through a multi-step agent process using LangChain and LangGraph.

## System Overview

This system consists of three specialized agents:

1. **Extractor Agent**: Parses input documents to extract relevant job information
2. **Composer Agent**: Generates a structured job posting in Markdown format
3. **Review Agent**: Validates the job posting and provides feedback

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up OpenAI API Key

Create a `.env` file in the project root with your OpenAI API key:

```
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

### Basic Usage

```bash
python run_agents.py --input documents/sample_job_description.txt
```

### Advanced Options

```bash
python run_agents.py --input documents/sample_job_description.txt --output custom_output --model gpt-4
```

Parameters:
- `--input`: Path to the input document (required)
- `--output`: Directory to save the output files (default: 'output')
- `--model`: LLM model to use (default: 'gpt-3.5-turbo')

## Project Structure

```
search-wizard/
├── agents/
│   ├── __init__.py
│   ├── extractor_agent.py
│   ├── composer_agent.py
│   ├── review_agent.py
├── documents/
│   └── sample_job_description.txt
├── output/
├── .env
├── guide.md
├── README.md
├── requirements.txt
└── run_agents.py
```

## Workflow

1. The Extractor Agent parses the input document and extracts structured job information
2. The Composer Agent generates a Markdown job posting based on the extracted information
3. The Review Agent evaluates the job posting for quality and completeness
4. If approved, the job posting is saved; otherwise, it's sent back to the Composer Agent for revision

## Next Steps

- Fine-tune the agents for better extraction and composition
- Add support for more document formats (currently supports text and PDF)
- Implement a web interface for easier interaction
- Add more comprehensive validation rules for the Review Agent
