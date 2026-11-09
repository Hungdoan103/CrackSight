.PHONY: install-api install-web install dev-api dev-web health

API_DIR=apps/api
WEB_DIR=apps/web

install-api:
	pip install -r $(API_DIR)/requirements.txt

install-web:
	cd $(WEB_DIR) && npm install

install: install-api install-web

dev-api:
	cd $(API_DIR) && python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

dev-web:
	cd $(WEB_DIR) && npm run dev

health:
	curl -s http://127.0.0.1:8000/health
