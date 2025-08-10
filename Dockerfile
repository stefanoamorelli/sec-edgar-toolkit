# SEC EDGAR Toolkit - Multi-stage Dockerfile
# Build images for TypeScript and Python packages

# =============================================================================
# Base Images
# =============================================================================

# TypeScript/Node.js base stage
FROM node:20-alpine AS typescript-base
WORKDIR /app
# Install pnpm globally
RUN npm install -g pnpm
# Copy package files
COPY typescript/package.json typescript/pnpm-lock.yaml* ./
# Install dependencies
RUN pnpm install --frozen-lockfile
# Copy source code
COPY typescript/ .
# Build the TypeScript package
RUN pnpm run build

# Python base stage  
FROM python:3.11-slim AS python-base
WORKDIR /app
# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*
# Copy Python package files
COPY python/pyproject.toml python/README.md ./
# Install the package in production mode
RUN pip install --no-cache-dir .
# Copy source code
COPY python/src/ ./src/

# =============================================================================
# Development Images
# =============================================================================

# TypeScript development stage
FROM typescript-base AS typescript-dev
# Install development dependencies (already included in base)
COPY typescript/ .
# Expose default port for development server
EXPOSE 3000
# Default command for development
CMD ["pnpm", "run", "test"]

# Python development stage
FROM python-base AS python-dev
# Install development dependencies
RUN pip install --no-cache-dir ".[dev]"
# Copy test files and other development files
COPY python/ .
# Default command for development
CMD ["pytest"]

# =============================================================================
# Production Images
# =============================================================================

# TypeScript production stage
FROM node:20-alpine AS typescript
WORKDIR /app
RUN npm install -g pnpm
# Copy only production dependencies and built artifacts
COPY --from=typescript-base /app/dist ./dist
COPY --from=typescript-base /app/package.json ./package.json
COPY --from=typescript-base /app/node_modules ./node_modules
# Set production environment
ENV NODE_ENV=production
EXPOSE 3000
CMD ["node", "dist/index.js"]

# Python production stage  
FROM python:3.11-slim AS python
WORKDIR /app
# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*
# Copy and install the package
COPY --from=python-base /app .
# Set production environment
ENV PYTHONPATH=/app/src
CMD ["python", "-c", "import sec_edgar_toolkit; print('SEC EDGAR Toolkit ready')"]

# =============================================================================
# Combined Development Image
# =============================================================================

# Combined development stage with both TypeScript and Python
FROM ubuntu:22.04 AS dev
WORKDIR /app

# Install Node.js, Python, and system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    python3 \
    python3-pip \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g pnpm \
    && rm -rf /var/lib/apt/lists/*

# Copy and setup TypeScript package
COPY typescript/ ./typescript/
WORKDIR /app/typescript
RUN pnpm install && pnpm run build

# Copy and setup Python package
WORKDIR /app
COPY python/ ./python/
WORKDIR /app/python
RUN pip3 install -e ".[dev]"

# Set working directory back to root
WORKDIR /app
EXPOSE 3000

# Default command shows both packages are ready
CMD ["bash", "-c", "echo 'TypeScript:' && cd typescript && pnpm run test --passWithNoTests && echo 'Python:' && cd ../python && python3 -c 'import sec_edgar_toolkit; print(\"SEC EDGAR Toolkit (Python) ready\")' && echo 'Both packages ready for development!'"]