# CU-Quants-Trading-Terminal
The CU Quants Trading Terminal

Posedian But Better
Web Based UI

## Quick Start with Docker

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### Run the Terminal

```bash
# Clone the repo
git clone https://github.com/your-org/CU-Quants-Trading-Terminal.git
cd CU-Quants-Trading-Terminal

# Start the frontend (first run will take a minute to build)
docker compose up

# Or run in background
docker compose up -d
```

Open **http://localhost:3000** in your browser.

### Stop the Terminal

```bash
docker compose down
```

### Rebuild (after pulling new changes)

```bash
docker compose up --build
```

## Development Without Docker

See [terminal/frontend/README.md](terminal/frontend/README.md) for manual setup instructions.

## Project Structure

- `terminal/frontend/` - React/Vite web UI
- `terminal/backend/` - C++ backend (placeholder - not yet implemented)
- `docker-compose.yml` - Docker orchestration for all services

