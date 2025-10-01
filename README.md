# What
Coming Soon.

## Part A - Prereqs
- hud cli
- Docker


## Part A - Setup
- In the root of this repo:
    - Run `hud dev --build`

## Part B - Prereqs
- uv

## Part B - Setup
- In the root of this repo run: 
    - `uv sync`
    - `uv venv`
    - `source .venv/bin/activate`
    - `cp .env.example .env`

- Replace the dummy API keys with your own.

- Then run `python test_run.py`

## If things are working you should see:

## Troubleshooting
- If you need to cache bust:
```
hud dev . -e --no-cache --build
```

---

## Pentest
`python run_pentest_task.py`