.PHONY: help install dev run test clean docker-build docker-run deploy-synology

help:
	@echo "AI Image Analyzer - Available commands:"
	@echo "  install          Install dependencies using conda"
	@echo "  dev              Install development dependencies"
	@echo "  run              Run the web interface"
	@echo "  test             Run tests"
	@echo "  clean            Clean up temporary files"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-run       Run Docker container"
	@echo "  deploy-synology  Deploy to Synology NAS"

install:
	conda env create -f environment.yml
	@echo "Environment created. Activate with: conda activate ai-image-analyzer"

dev: install
	conda activate ai-image-analyzer && pip install pytest black flake8

run:
	@echo "Starting AI Image Analyzer web interface..."
	cd web && python app.py

test:
	python -m pytest tests/

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -delete
	rm -rf build/
	rm -rf dist/

docker-build:
	docker build -t ai-image-analyzer .

docker-run:
	docker-compose up -d

deploy-synology:
	@echo "Deploying to Synology NAS..."
	rsync -avz --exclude='.git' --exclude='__pycache__' web/ user@synology-ip:/volume1/web/aisorting/
	@echo "Deployment complete. SSH into your Synology and run the deploy.sh script."

package:
	python setup.py sdist bdist_wheel
	@echo "Package created in dist/ directory"

lint:
	flake8 scripts/ web/ --max-line-length=100
	black --check scripts/ web/

format:
	black scripts/ web/
