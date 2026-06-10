"""
Standalone CLI runner for the research pipeline.

Usage:
    python main.py "AI trends in 2025"
    python main.py "quantum computing breakthroughs" --focus "hardware,error correction"
    python main.py "climate change solutions" --results 8 --format plain
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Validate environment early
if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GOOGLE_CLOUD_PROJECT"):
    print(
        "ERROR: Set GOOGLE_API_KEY (or GOOGLE_CLOUD_PROJECT for Vertex AI) in .env",
        file=sys.stderr,
    )
    sys.exit(1)

from google.adk.runners import InMemoryRunner
from google.genai import types

from orchestrator.agent import root_agent


async def run_pipeline(topic: str, max_results: int, focus: str, fmt: str) -> str:
    runner = InMemoryRunner(agent=root_agent)
    session = await runner.session_service.create_session(
        app_name=root_agent.name,
        user_id="cli-user",
    )

    prompt = (
        f"Please research the following topic and produce a full report:\n\n"
        f"**Topic:** {topic}\n"
        f"**Max search results:** {max_results}\n"
    )
    if focus:
        prompt += f"**Focus areas:** {focus}\n"
    prompt += f"**Output format:** {fmt}\n"

    final_response = ""
    async for event in runner.run_async(
        user_id="cli-user",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=prompt)],
        ),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    return final_response


def main() -> None:
    parser = argparse.ArgumentParser(description="Google ADK Research Pipeline")
    parser.add_argument("topic", help="Research topic or question")
    parser.add_argument("--results", type=int, default=5, help="Max search results (default: 5)")
    parser.add_argument("--focus", default="", help="Comma-separated focus areas")
    parser.add_argument("--format", default="markdown", choices=["markdown", "plain"])
    args = parser.parse_args()

    print(f"\n🔍 Researching: {args.topic}\n{'─' * 60}\n")
    report = asyncio.run(
        run_pipeline(args.topic, args.results, args.focus, args.format)
    )
    print(report)


if __name__ == "__main__":
    main()
