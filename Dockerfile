# start from a lightweight python image
FROM python:3.11-slim

# create and move into the work directory inside the container
WORKDIR /app

# copy dependency list and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy the rest of your backend source code
COPY src /app

# expose the port FastAPI will listen on (same as your code)
EXPOSE 8000

# command to start your FastAPI app
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
