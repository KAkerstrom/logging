# Use Python image as the base
FROM python:3.13.2

# Set the working directory in the container
WORKDIR /app

# Copy the project files into the container
COPY ./server ./server

# Install dependencies
# fastapi uvicorn sqlalchemy
RUN pip install --no-cache-dir -r ./server/requirements.txt

# Expose the port FastAPI runs on
EXPOSE ${PORT:-8100}

# Command to run the API server
#RUN python ./server/server.py
CMD uvicorn server.server:app --host ${HOST:-0.0.0.0} --port ${PORT:-8100}
