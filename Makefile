ifneq (,$(wildcard ./.env))
	include .env
	export
endif

compose-up:
	docker compose -f compose.dev.yml up --detach

compose-down:
	docker compose -f compose.dev.yml down

run:
	python run.py

# curl will parse --user to "Authorization: Basic <token>" header
mongo-admin-get-token:
	@curl --request POST \
	  --url https://cloud.mongodb.com/api/oauth/token \
	  --user "$${MONGO_ADMIN_API_ID}:$${MONGO_ADMIN_API_SK}" \
	  --header "Content-Type: application/x-www-form-urlencoded" \
	  --header 'cache-control: no-cache' \
	  --data "grant_type=client_credentials" \
	 | jq '.access_token' > token.txt

# sed -n '1p' token.txt | tr -d \"
# 	read first line from token.txt, then remove all double quote from it
# 
# date -Iseconds -u -v+6H
# 	-Iseconds: format to ISO 8601 in seconds
# 	-u: to UTC
# 	-v+6H: add 6 hours to now
mongo-admin-set-ip:
	@curl --include --header "Authorization: Bearer $$(sed -n '1p' token.txt | tr -d \")" \
		--header "Accept: application/vnd.atlas.2025-03-12+json" \
		--header "Content-Type: application/json" \
		-X POST "https://cloud.mongodb.com/api/atlas/v2/groups/68396791152d7a5a27e060b1/accessList" \
		-d '[ \
				{ \
					"comment": "for local dev", \
					"deleteAfterDate": "'"$$(date -Iseconds -u -v+6H)"'", \
					"ipAddress": "'"$$(curl -4s https://api.ipify.org | tr -d '\n')"'" \
				} \
			]'

# Add current public IP address to project's IP access list in MongoDB Atlas.
# For local dev.
mongo-ip:
	$(MAKE) mongo-admin-get-token mongo-admin-set-ip