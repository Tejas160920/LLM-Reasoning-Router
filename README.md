---
title: LLM Reasoning Router
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
---

# LLM Reasoning Router

An intelligent AI gateway that automatically routes prompts to appropriate models based on complexity analysis.

## Features

- **Smart Routing**: Analyzes prompt complexity and routes to fast or reasoning models
- **Streaming Responses**: Real-time output like ChatGPT
- **Quality Checking**: Validates response quality and escalates if needed
- **Cost Optimization**: Uses cheaper models for simple tasks
- **Full Metrics**: Tracks latency, cost, and routing decisions

## How It Works

1. Analyze incoming prompt for complexity signals (keywords, code, math, etc.)
2. Route simple prompts to fast model (`gemini-2.0-flash`)
3. Route complex prompts to reasoning model (`gemini-2.5-pro`)
4. Stream response in real-time
5. Check quality and log metrics

## Tech Stack

- **Backend**: FastAPI (Python)
- **LLM**: Google Gemini API
- **Database**: PostgreSQL (Neon)
- **Deployment**: Hugging Face Spaces

## API Endpoints

- `POST /v1/chat/completions` - Standard chat completion
- `POST /v1/chat/completions/stream` - Streaming chat completion
- `POST /v1/analyze` - Instant complexity analysis
- `GET /v1/metrics` - Dashboard metrics
- `GET /v1/health` - Health check

## Environment Variables

Set these in your Space's settings:

- `GEMINI_API_KEY` - Your Google Gemini API key
- `DATABASE_URL` - PostgreSQL connection string (from Neon)
- `FAST_MODEL` - Fast model name (default: gemini-2.0-flash)
- `COMPLEX_MODEL` - Complex model name (default: gemini-2.5-pro)
