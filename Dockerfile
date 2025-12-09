# Use slim python base image
FROM python:3.11-slim

# Set container working directory
WORKDIR /app

# Copy dependency list and install packages
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code EXACTLY preserving folder structure
COPY src /app/src

# Copy frontend files to serve at /
COPY index.html /app/index.html
COPY styles.css /app/styles.css

# Expose the correct port the autograder expects
EXPOSE 8080

# Start FastAPI with the correct module path and port
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8080"]
