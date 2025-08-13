# Makefile for generating Python code from JSON schema

# Default schema directory
SCHEMA_DIR ?= schema
# Default output prefix directory
OUTPUT_PREFIX ?= src

# Check if dependencies are installed by checking pip's output
CHECK_DEPS := $(shell pip list | grep datamodel-code-generator)

# Target to generate python code
generate-code:
ifndef CHECK_DEPS
	@echo "Dependencies are not installed. Please run 'make install-dep' first."
	@exit 1
else
	@echo "Generating Python models from schemas in $(SCHEMA_DIR)..."
	python script/generate_model.py $(SCHEMA_DIR) --output-prefix $(OUTPUT_PREFIX)
endif

# Target to install dependencies
install-dep:
	@echo "Installing dependencies from requirements.txt..."
	pip install -r requirements.txt

# Target to run all tests
test:
	@echo "Running all tests..."
	python -m pytest tests/ -v

# Target to run tests with coverage
test-cov:
	@echo "Running tests with coverage..."
	python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# Target to clean test artifacts
clean-test:
	@echo "Cleaning test artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +

.PHONY: generate-code install-dep test test-cov clean-test
