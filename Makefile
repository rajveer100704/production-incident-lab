.PHONY: up-buggy up-fixed load smoke test logs down reset config

up-buggy:
	TX_MODE=buggy docker compose up --build -d --wait --wait-timeout 60

up-fixed:
	TX_MODE=fixed docker compose up --build -d --wait --wait-timeout 60

load:
	python scripts/load_test.py --requests 200 --concurrency 20

smoke:
	python scripts/smoke_test.py

test:
	python -m pytest -q

logs:
	docker compose logs -f api downstream

down:
	docker compose down

reset:
	docker compose down -v --remove-orphans

config:
	docker compose config
