# include ../common.mk // This is from Professor Callahan's 09/10 Zoom meeting.
include common.mk

# Our directories
API_DIR = server
DB_DIR = data
SEC_DIR = security
COMMON_DIR = common
STATES_DIR = states
COUNTIES_DIR = counties
REQ_DIR = .

FORCE:

prod: all_tests github

github: FORCE
	- git commit -a
	git push origin master

all_tests: FORCE
	cd $(API_DIR); make tests
	cd $(DB_DIR); make tests
	cd $(COMMON_DIR); make tests
	cd $(STATES_DIR); make tests
	cd $(COUNTIES_DIR); make tests
	# cd $(DB_DIR); make tests

dev_env: FORCE
	pip install -r $(REQ_DIR)/requirements-dev.txt
	@echo "You should set PYTHONPATH to: "
	@echo $(shell pwd)

docs: FORCE
	cd $(API_DIR); make docs
