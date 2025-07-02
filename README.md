# powo-agent
A command-line assistant takes genus and species names as inputs and runs a local script to fetch botanical information using the POWO (Plants of the World Online) database.

### Create and Activate Virtual environment
``` python3 -m venv .venv ```

``` source .venv/bin/activate ```

### Create a .env File and add API key
``` touch .env ```

``` OPENAI_API_KEY= ```

### Build the Docker image
``` docker build -t powo-agent .```

### Run the Docker Container
``` docker run --rm -p 9999:9999 --env-file .env powo-agent ```

agent card should be present at http://localhost:9999/.well-known/agent.json if everything goes well

#### Test

``` python3.12 -m pytest -s   ```
