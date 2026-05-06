# Distillery

Distillery is a tool designed to extract, process, and "distill" knowledge from YouTube playlists. It automatically downloads transcripts and uses a multi-stage LLM pipeline to condense large amounts of video content into high-signal summaries, wisdom, and insights.

## Summary

The tool follows a hierarchical distillation process:

1. **Transcript Acquisition**: Downloads markdown transcripts for all videos in a specified YouTube playlist.
2. **Individual Distillation**: For each transcript, it generates three levels of condensation:
    - **Summary**: A concise overview of the video.
    - **Wisdom**: Key timeless principles extracted from the summary.
    - **Insights**: Actionable or novel observations derived from the summary.
3. **Playlist Distillation**: Aggregates all individual summaries, wisdoms, and insights into a final, comprehensive distilled document for the entire playlist.

> [!warning]
> Due to the high amounts of videos some playlists container, distilliation will not happen concurrently as to avoid overloading AIF's inferencing platform. As such, a distillation may take long period of time to finish depending on the size of the playlist.

## Features

- **Automated Pipeline**: Full workflow from YouTube playlist ID to a final distilled markdown report.
- **Multi-Stage Refinement**: Uses a progressive "distillation" approach (Transcript -> Summary -> Wisdom/Insights) to ensure high information density.
- **LLM Agnostic**: Configurable to work with various models via AI Factory / OpenAI-compatible APIs.
- **Local Persistence**: Saves all intermediate results (summaries, wisdoms, insights) as markdown files for review.
- **Flexible Configuration**: Supports CLI arguments, environment variables, and YAML configuration files.

## Installation

### Prerequisites

- Python 3.10+
- `uv` (recommended for dependency management)

### Setup

```bash
# Sync dependencies
uv sync --all-groups
```

## Usage

### Basic Command

Run the distillation process by providing a YouTube playlist ID:

```bash
uv run distil --playlist-id <PLAYLIST_ID> --youtube-api-key <YOUR_API_KEY> --output <playlist_name>
```

### Configuration

You can configure the tool via CLI flags, a `.env` file, or a `distillery.yaml` file.

**Key Configuration Options:**

- `--playlist-id`: The ID of the YouTube playlist to process.
- `--youtube-api-key`: Your Google/YouTube API key.
- `--output`: Directory where transcripts and distilled files will be stored (default: `transcripts`).
- `--model`: The LLM model to use for distillation.
- `--api-base-url`: The URL of the LLM API provider.

### Example `.env` file

```env
YOUTUBE_API_KEY=your_api_key_here
DISTILLERY_MODEL=gemma-4-26b-a4b-it
DISTILLERY_API_BASE_URL=https://api.ai.us.lmco.com/v1
```

## Project Structure

- `src/distillery/main.py`: CLI entrypoint and orchestration logic.
- `src/distillery/agent.py`: LLM agent logic and distillation pipeline.
- `src/distillery/transcripts.py`: YouTube API interaction and transcript downloading.
- `src/distillery/configs.py`: Pydantic-based configuration management.
- `src/distillery/patterns/`: Prompt templates used for distillation stages.

## Resources

- **YouTube API Documentation**: [Google Developers](https://developers.google.com/youtube/v3)
- **Pydantic AI**: [Documentation](https://pydantic-ai.readthedocs.io/)
- **Cyclopts**: [Documentation](https://cyclopts.github.io/)
