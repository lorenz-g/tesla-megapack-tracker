
develop:
	./watchexec -w templates -w projects.csv -w generate -w docs/js python generate/website.py

test:
	pytest --doctest-modules generate/website.py

build:
	python generate/website.py

server-local:
	python -m http.server 2222 --bind localhost

open-local:
	open http://localhost:2222/tesla-megapack-tracker/all-big-batteries.html

open:
	open https://lorenz-g.github.io/tesla-megapack-tracker/all-big-batteries.html
