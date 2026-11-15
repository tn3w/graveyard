FROM python:3.11-slim

# Install Rust and Cargo
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && export PATH="$PATH:/root/.cargo/bin"

# Install maturin and cibuildwheel
RUN pip install maturin cibuildwheel

# Set the working directory
WORKDIR /app

# Copy the project files into the container
COPY . .

# Run cibuildwheel to build wheels
CMD ["cibuildwheel", "--output-dir", "/wheelhouse"]
