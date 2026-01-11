#!/bin/bash
# Development environment launcher using tmux
# Usage: ./scripts/dev.sh

SESSION="glean"

# Kill existing session if it exists
tmux kill-session -t $SESSION 2>/dev/null

# Create new session with backend pane
tmux new-session -d -s $SESSION -n "dev"

# Split into 3 panes: backend (top), frontend (bottom-left), shell (bottom-right)
tmux split-window -v -t $SESSION:dev
tmux split-window -h -t $SESSION:dev.1

# Backend API (top pane)
tmux send-keys -t $SESSION:dev.0 "cd $(pwd) && source .venv/bin/activate 2>/dev/null; cd web/api && uvicorn main:app --reload --host 0.0.0.0 --port 8000" C-m

# Frontend dev server (bottom-left pane)
tmux send-keys -t $SESSION:dev.1 "cd $(pwd)/web/frontend && npm run dev" C-m

# Shell for commands (bottom-right pane)
tmux send-keys -t $SESSION:dev.2 "cd $(pwd) && source .venv/bin/activate 2>/dev/null; echo 'Ready for commands. Try: make help'" C-m

# Select the shell pane
tmux select-pane -t $SESSION:dev.2

# Attach to session
tmux attach-session -t $SESSION
