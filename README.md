# Container Service
A service for managing development containers with SSH access.

## Setup
1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the service:
   ```
   uvicorn src.main:app --reload
   ```

## API Endpoints
- POST /containers - Create new container
- DELETE /containers/{container_id} - Terminate container
