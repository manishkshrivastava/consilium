# Use official Python lightweight image
FROM python:3.10-slim

# Set working directory to /workspace so it doesn't conflict with your 'app' folder
WORKDIR /workspace

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the repository code
COPY . .

# Expose the API port
EXPOSE 8000

# Run the FastAPI server using Uvicorn
CMD ["uvicorn", "app.api_server:app", "--host", "0.0.0.0", "--port", "8000"]