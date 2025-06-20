# Search Wizard Backend

AI-powered document generation backend with LlamaParse integration.

## Features

- **Multi-Agent System**: StructureAgent + WriterAgent for intelligent document generation
- **LlamaParse Integration**: Advanced document parsing with OCR and table extraction
- **Multi-LLM Support**: OpenAI, Anthropic, and Google Gemini
- **Intelligent Caching**: Redis-based with memory fallback
- **Document Processing**: PDF, Word, PowerPoint, and more

## Tech Stack

- **Framework**: FastAPI (Python 3.11)
- **Document Parsing**: LlamaParse API
- **Caching**: Redis
- **LLM Providers**: OpenAI, Anthropic, Gemini
- **Database**: Supabase

## Deployment

Deployed on Railway with automatic restarts and health monitoring.

## Environment Variables

See `.env.example` for required configuration.