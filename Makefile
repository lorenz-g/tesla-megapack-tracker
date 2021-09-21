
develop:
	./watchexec -w templates -w projects.csv -w generate_website.py python generate_website.py

test:
	pytest --doctest-modules generate_website.py
