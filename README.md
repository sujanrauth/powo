# powo-agent
A command-line assistant takes genus and species names as inputs and runs a local script to fetch botanical information using the POWO (Plants of the World Online) database.

#### Create and Activate Virtual environment
``` python3 -m venv .venv ```

``` source .venv/bin/activate ```

#### Install Dependencies
``` pip install -r requirements.txt ``` 

#### Create a .env File and add API key
``` touch .env ```

``` OPENAI_API_KEY= ```

#### Run the Agent
``` python3 chat.py ```

# iChatBio-SDK
``` python3 __main__.py ```

agent card should be present at http://localhost:9999/.well-known/agent.json if everything goes well
