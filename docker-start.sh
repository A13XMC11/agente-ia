#!/bin/bash
# Start Docker containers with environment variables from .env

docker-compose --env-file .env up -d --build

echo ""
echo "✅ Containers started!"
echo ""
echo "Services:"
echo "  - FastAPI:  http://localhost:8000"
echo "  - Dashboard: http://localhost:8501"
echo "  - Redis:    localhost:6379"
echo ""
echo "View logs:"
echo "  docker-compose logs -f fastapi"
echo "  docker-compose logs -f streamlit"
echo ""
