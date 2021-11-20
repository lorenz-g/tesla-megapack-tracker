
develop:
	./watchexec -w templates -w projects.csv -w generate python generate/website.py

test:
	pytest --doctest-modules generate/website.py

build:
	python generate/website.py

open:
	open https://lorenz-g.github.io/tesla-megapack-tracker/all-big-batteries.html
