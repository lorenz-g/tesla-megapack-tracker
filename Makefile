
develop:
	./watchexec -w templates -w projects.csv -w generate -w docs/js python generate/website.py

test:
	pytest --doctest-modules generate/website.py

build:
	python generate/website.py

run-local:
	python -m http.server 2222 --bind localhost

open-local:
	open http://localhost:2222/tesla-megapack-tracker/

open-remote:
	open https://lorenz-g.github.io/tesla-megapack-tracker/

gst:
# the normal git status shows all the project files. This allows to see the important things
# todo: also make the output of that colorful
	git -c color.ui=always status | grep  -v "docs/projects"

lint:
	black generate