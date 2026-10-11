# Hypermedia Chat

Realtime chat application using Server-Sent Events (Datastar) and TailwindCSS

## Requirements

- npm
- uv

## Running

### Build styles (watching)

```bash
npx @tailwindcss/cli -i ./src/input.css -o ./src/static/output.css --watch
```

### Run server (watching)

```bash
uv run fastapi dev src/hypermedia_chat
```
