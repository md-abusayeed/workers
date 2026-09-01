# Cloudflare Worker Client

A small Python client I use to send requests from my local machine to a Cloudflare Worker.

Basically:

```text
Local Python
     ↓
Cloudflare Worker
     ↓
Whatever the Worker needs to talk to
```

Nothing fancy. I just wanted a clean way to call my Worker from Python without writing the same HTTP code everywhere.

## Setup

Install `httpx`:

```bash
pip install httpx
```

Set your Worker URL:

```bash
WORKER_URL=https://your-worker.workers.dev
```

If the Worker needs authentication:

```bash
WORKER_TOKEN=your-token
```

## Example

```python
import asyncio
import os

from worker_client import Config, WorkerClient


async def main():
    async with WorkerClient(
        Config(
            endpoint=os.environ["WORKER_URL"],
            token=os.getenv("WORKER_TOKEN"),
        )
    ) as worker:
        response = await worker.get("/api/status")
        print(response)


asyncio.run(main())
```

POST requests work the same way:

```python
response = await worker.post(
    "/api/jobs",
    payload={
        "name": "test",
        "priority": "high",
    },
)
```

## Why I made it

I wanted something small that handles the boring stuff for me:

* connection pooling
* async requests
* retries
* timeouts
* authentication
* JSON responses
* clean connection shutdown

So the rest of my code can just do:

```python
response = await worker.get("/api/status")
```

instead of dealing with HTTP details every time.

## Project

```text
.
├── worker_client.py
├── main.py
├── requirements.txt
└── README.md
```

That's pretty much it.

It's just a personal tool for talking to my Cloudflare Worker from my machine.
