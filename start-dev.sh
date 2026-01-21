#!/bin/bash

echo "Starting IDS Development Environment"
echo "====================================="
echo

echo "Starting Flask Backend..."
cd backend && python app.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

echo
echo "Starting Next.js Frontend..."
cd .. && npm run dev &
FRONTEND_PID=$!

echo
echo "Both services are starting up..."
echo
echo "Flask Backend: http://localhost:3002"
echo "Next.js Frontend: http://localhost:3000"
echo
echo "Press Ctrl+C to stop both services..."

# Function to cleanup processes
cleanup() {
    echo "Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit
}

# Trap Ctrl+C
trap cleanup SIGINT

# Wait for user to stop
wait
