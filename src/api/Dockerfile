# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application source code
COPY ./src /app/src

# Ensure Python can find the src package by setting PYTHONPATH
ENV PYTHONPATH=/app

# Command to run the application from the project root
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]