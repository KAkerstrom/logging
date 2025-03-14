# Overview
This is a very basic API server, intended to be easy to set up and run.  
There currently isn't a user interface included, though there is a Swagger UI.

# Features
- Basic API server for a simple data logging application.
- Track Properties (with a Number and optional Notes)
- Track Events for each Property (with a Timestamp and a Description)
- A Swagger UI at http://localhost:8100/docs

# Install and run using Docker
- Download and install [Docker Dektop](https://docs.docker.com/desktop/setup/install/windows-install/) (Windows)
- Download this project by doing one of the following methods:
  - [Click here](https://github.com/KAkerstrom/logging/archive/refs/heads/master.zip) to download this project as a zip file, which can then be extracted.
  - Or: download and install [Git](https://git-scm.com/downloads), then run this command in the terminal:
    - ```git clone https://github.com/KAkerstrom/logging.git```
- Start the server by running "start_server.bat"
  - (You can also just run ```docker-compose up``` in the terminal yourself.)
- If successful, this command should:
  - Create a docker container
  - Download Python, and all necessary Python libraries into the container
  - Create property_logs.db (in "data" directory)
  - Start the API server on port 8100
