.PHONY: setup build build-tf-a build-u-boot build-linux build-initramfs \
        boot test test-smoke test-faults test-smp test-regression report clean baseline

VENV ?= .venv
PY ?= python3

setup:
	$(PY) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -e ".[dev]"

baseline:
	./qemu/launch.sh

build: build-u-boot build-tf-a build-linux build-initramfs
	./qemu/scripts/dump_dtb.sh

build-u-boot:
	./qemu/scripts/build_uboot.sh

build-tf-a:
	./qemu/scripts/build_tfa.sh

build-linux:
	./qemu/scripts/build_linux.sh

build-initramfs:
	./qemu/scripts/build_initramfs.sh

boot:
	$(PY) -m bootx.cli.main boot

test:
	$(PY) -m pytest --junitxml=reports/junit.xml

test-smoke:
	$(PY) -m pytest -m smoke --junitxml=reports/junit.xml

test-faults:
	$(PY) -m pytest -m fault --junitxml=reports/junit.xml

test-smp:
	$(PY) -m pytest -m smp --junitxml=reports/junit.xml

test-regression:
	$(PY) -m pytest -m regression --junitxml=reports/junit.xml

report:
	$(PY) -m bootx.cli.main report

clean:
	$(PY) -m bootx.cli.main clean
