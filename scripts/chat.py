from dotenv import load_dotenv
load_dotenv()
from agents import Agent, Runner, function_tool
import subprocess

@function_tool
def run_script(input: str) -> str:
    try:
        parts = input.strip().split()
        if len(parts) != 2:
            return "Error: Please provide exactly two parameters."

        param1, param2 = parts

        result = subprocess.run(
            ["python3", "script.py", param1, param2],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        return f"Script error: {e.stderr.strip()}"
    except Exception as ex:
        return f"Unhandled error: {str(ex)}"

agent = Agent(
    name="Assistant", 
    instructions="You take two strings which are genus and species of a plant scientific name and run a powo  with the names to return data about the plant and You MUST only return the output of the tool exactly as-is. Do NOT add extra explanation.",
    tools=[run_script]
)

while True:
    user_input = input("\nEnter plant name (or type 'exit' to quit): ")
    if user_input.lower() in ["exit", "quit"]:
        print("Thank you!")
        break

    result = Runner.run_sync(agent, user_input)
    print("\nResult:", result.final_output)
