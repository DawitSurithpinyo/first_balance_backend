compose-up:
	docker compose -f compose.dev.yml up --detach

compose-down:
	docker compose -f compose.dev.yml down

run:
	python run.py