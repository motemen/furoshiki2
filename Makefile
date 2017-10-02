test: test-local test-docker

test-local:
	./t/01-furo2

test-docker:
	docker build t
	docker run --rm -v "$$PWD:/src" -w /src "$$(docker build -q t)" sh -c 'pip3 install . && FURO2=$$(which furo2) ./t/01-furo2'

sdist:
	python3 setup.py sdist
