# Use the official Python 3.13 image as a base
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app/



# Install uv (fast Python package installer and runner)
RUN pip install --upgrade pip && pip install uv

# Sync dependencies from pyproject.toml using uv (allow pre-releases)
RUN uv pip install --system --upgrade --prerelease=allow .


# Expose the correct port for the app
EXPOSE 3978

# Start the application using python
CMD ["python", "-m", "src.main"]
