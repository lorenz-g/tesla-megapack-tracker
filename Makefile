
develop:
	./watchexec -w templates -w projects.csv -w generate python generate/website.py

test:
	pytest --doctest-modules generate/website.py

build:
	python generate/website.py

server-local:
	python -m http.server 2222 --bind localhost --directory docs

open-local:
	open http://localhost:2222/all-big-batteries.html

open:
	open https://lorenz-g.github.io/tesla-megapack-tracker/all-big-batteries.html
