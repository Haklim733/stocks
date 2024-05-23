SHELL := /bin/bash
BRANCH != git rev-parse --abbrev-ref HEAD# same as $(shell ...)
ECR_URI = $$AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com# set AWS_ACCOUNT in .env or export to env var
REPO_NAME = thetadata
PWD != echo $$PWD
.PHONY = config-dev config-prod build build-slim dev dev-slim rm-cache run run-slim rm rm-slim restart restart-slim rm containers push-ecr push-ecr-slim

config-dev:
	source .env

config-prod:
	set -a && source .env.prod && set +a

create-ecr:
	aws ecr create-repository \
    --repository-${REPO_NAME} \
    --region us-east-1 \
    --tags '[{"Key":"env","Value":"prod"},{"Key":"repo","Value": ${REPO_NAME}}]'

build-fat:
	docker build -t ${REPO_NAME}.fat:${BRANCH} --build-arg NODE_VERSION=20 --progress=plain -f docker/Dockerfile  --secret id=env,src=.env --build-arg BRANCH=${BRANCH} .

slimify-fat:
	slim build --exec-file ./docker/slim-exec.sh --preserve-path-file ./docker/preserve-paths.txt --include-bin-file=./docker/preserve-bins.txt --include-path-file=./docker/preserve-paths.txt  --http-probe=false --target garmgmt.fat:${BRANCH} --tag garmgmt.slim:${BRANCH}

build-lambda:
	docker build -t ${REPO_NAME}.lambda:${BRANCH} --platform linux/amd64 -f docker/lambda --secret id=env,src=.env --build-arg BRANCH=${BRANCH} --progress plain --build-arg CACHEBUST=$(date +%s) .

slimify-lambda:
	slim build --exec-file ./docker/slim-exec.sh --preserve-path-file ./docker/preserve-paths.txt --include-bin-file=./docker/preserve-bins.txt --include-path-file=./docker/preserve-paths.txt  --http-probe=false --target garmgmt.lambda:${BRANCH} --tag garmgmt.lambda.slim:${BRANCH}

restart:
	export garmgmt=$$(docker ps -a -q --filter name=garmgmt) && \
	docker start $${garmgmt} && \
	docker exec -it $${garmgmt} bash


restart-slim:
	export garmgmt_slim=$$(docker ps -a -q --filter name=garmgmt.slim:latest)
	docker start $$garmgmt_slim  && docker exec -it $$garmgmt_slim bash

rm-cache:
	docker builder prune

rm-containers:
	docker rm -v $(docker ps --filter status=exited -q)

rm-fat:
	export containers=$$(docker ps -a -q --filter name=garmgmt.fat) && docker rm $${containers}

rm-slim:
	export containers=$$(docker ps -a -q --filter name=garmgmt.slim) && docker rm $${containers}

rm-lambda:
	export containers=$$(docker ps -a -q --filter name=garmgmt.lambda) && docker rm $${containers}

run-fat:
	docker run -it --name garmgmt.fat-${BRANCH} -v $(PWD):/project/opt/local  -v ~/.aws:/root/.aws -e DBT_PROFILE='dev' garmgmt:${BRANCH}

run-slim:
	docker run -it --name garmgmt.slim-${BRANCH} -v $(PWD):/project/opt/local -v ~/.aws:/root/.aws -e DBT_PROFILE='dev' garmgmt.slim:${BRANCH}

run-lambda:
	docker run --platform linux/amd64 -d -v ~/.aws-lambda-rie:/aws-lambda -p 9000:8080 \
	-e BOX_FOLDER_IDS='{"contact_list": "248026883020", "internal": "248026883020" }' \
	-e BOX_CONFIG='${BOX_CONFIG}' \
	-e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
	-e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
	--name test.garmgmt.lambda \
	--entrypoint /aws-lambda/aws-lambda-rie garmgmt.lambda:${BRANCH} \
	 /usr/local/bin/python -m awslambdaric write_box/lambda_function.handler

test-lambda:
	curl "http://localhost:9000/2015-03-31/functions/function/invocations" -d @infrastructure/tests/data/s3_notification.json

activate:
	source /project/.venv/bin/activate && pipenv shell

push-ecr:
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${ECR_URI}
	docker tag garmgmt:${BRANCH} ${ECR_URI}/garmgmt:fat && \
	docker push ${ECR_URI}/garmgmt:fat

push-ecr-slim:
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${ECR_URI}
	docker tag garmgmt.slim:${BRANCH} ${ECR_URI}/garmgmt:slim && \
	docker push ${ECR_URI}/garmgmt:slim

push-ecr-slim-prod:
	docker tag 062843637934.dkr.ecr.us-east-1.amazonaws.com/garmgmt:slim ${ECR_URI}/garmgmt:slim
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${ECR_URI} && \
	docker push ${ECR_URI}/garmgmt:slim

push-ecr-lambda:
	aws ecr batch-delete-image \
		--repository-name garmgmt \
		--image-ids imageTag=lambda
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${ECR_URI}
	docker buildx prune -f && \
	docker tag garmgmt.lambda:${BRANCH} ${ECR_URI}/garmgmt:lambda && \
	docker push ${ECR_URI}/garmgmt:lambda

get-ecr-lambda-digest:
	export lambdaDigest=$$(aws ecr describe-images --repository-name garmgmt  --image-ids imageTag=lambda --query='imageDetails[0].imageDigest')

push-ecr-lambda-digest:
	aws ssm put-parameter --name /garmgmt/lambda/digest --value


docker-check:
	make run && ./docker/slim-exec.sh

pull-ecr-slim:
	docker pull ${ECR_URI}/garmgmt:lambda
