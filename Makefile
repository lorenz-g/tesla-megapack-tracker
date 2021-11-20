
develop:
	./watchexec -w templates -w projects.csv -w generate python generate/website.py

test:
	pytest --doctest-modules generate/website.py
