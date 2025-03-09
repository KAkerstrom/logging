# Use an official Python image
FROM python:3.13.2

# Set the working directory in the container
WORKDIR /app

# Copy the project files into the container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn sqlalchemy

# Expose the port FastAPI runs on
EXPOSE 8100

# Command to run the API server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8100"]
