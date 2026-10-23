# Build every guide: <dir>/guide.md -> build/nas-<dir>.pdf
GUIDES := $(wildcard */guide.md)
PDFS := $(patsubst %/guide.md,build/nas-%.pdf,$(GUIDES))
PYTHON ?= python3

all: $(PDFS)

.SECONDEXPANSION:
build/nas-%.pdf: %/guide.md $$(wildcard %/img/*) common/build_guide.py
	@mkdir -p build
	$(PYTHON) common/build_guide.py $< $@

clean:
	rm -rf build

.PHONY: all clean
