# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the working directory
COPY . .

# Default command to run the application (can be overridden in docker-compose.yaml)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
