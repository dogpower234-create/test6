# HKH - Flask REST API

## Overview

HKH is a Flask-based REST API project.

## Development Setup

To clone the repository:

`git clone https://github.com/NYUTandonStudent/HKH.git`

## Running Locally with MongoDB

The API server stores its data in MongoDB. By default it uses a local
one at `mongodb://localhost:27017` (set `MONGO_URI` to use another).

1. Start MongoDB, for example in Docker:

   ```
   docker run -d --name mongodb -p 27017:27017 mongo
   ```

   (Next time, just `docker start mongodb`.)

2. Load the states (optional; replaces the `USStates` collection):

   ```
   bin/load_states.sh
   ```

3. Start the API server on port 8000 (it exits with a hint if
   MongoDB is not reachable):

   ```
   ./local.sh
   ```

4. Check which database the server is using and that it is up:

   ```
   curl http://127.0.0.1:8000/dbinfo
   ```

   This returns 200 if the database is up, 503 if it is down.

Tests use a separate database, `test_geodata2026`, so they never touch
your data.

## Production Build

To build the project for production:

```
make prod
```

## Running Tests

To run the automated test suite locally:

```
make all_tests
```

## CI/CD

The workflow configuration is located at `.github/workflows/main.yml`.

The GitHub Actions workflow runs on the `master` branch.
