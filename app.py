import inspect
import importlib.util
import os
from colorama import init, Fore, Style
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

instructions = {"role": "system", "content": "You are a helpful assistant who execute bash command lines."}
chat_history = []

# Map Python types to JSON Schema-compatible types
TYPE_MAPPING = {
    int: "integer",
    float: "number",
    str: "string",
    bool: "boolean",
    list: "array",
    dict: "object"
}

# Helper to generate function metadata from annotations
def generate_function_metadata(func):
    """Generate metadata for OpenAI's functions parameter from a Python function."""
    sig = inspect.signature(func)
    parameters = {}
    required = []
    
    for name, param in sig.parameters.items():
        if param.annotation != inspect.Parameter.empty:
            param_type = TYPE_MAPPING.get(param.annotation, "string")  # Default to string if type is not mapped
            parameters[name] = {
                "type": param_type,
                "description": f"The {name} parameter."
            }
            if param.default == inspect.Parameter.empty:  # Required if no default value
                required.append(name)
        else:
            parameters[name] = {
                "type": "string",
                "description": f"The {name} parameter."
            }

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": func.__doc__,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required
            }
        }
    }
RED = '\033[31m'   # Red color
GREEN = '\033[32m' # Green color
RESET = '\033[0m'  # Reset to default color


def load_python_functions():    
    files = [f for f in os.listdir("./gen") if os.path.isfile("gen/" + f)]
    print(files)
    for file in files:
        load_python_function("gen/" + file)

def load_python_function(filename):
    spec = importlib.util.spec_from_file_location('my_module', filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Show the functions in the module
    functions = inspect.getmembers(module, inspect.isfunction)
    for name, func in functions:
        available_functions.append(func)
        function_metadata.append(generate_function_metadata(func))
        print(f"Function name: {name}, function object: {func}")
    global function_map
    function_map = {func.__name__: func for func in available_functions}

def make_python_function(filename: str, sourcecode: str):
    """Makes a python file with specified source code. Make sure the function have a descriptive docstring."""
    filename = "gen/" + filename
    # Load the module
    with open(filename, 'w') as f:
        f.write(sourcecode)

    spec = importlib.util.spec_from_file_location('my_module', filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Show the functions in the module
    functions = inspect.getmembers(module, inspect.isfunction)
    for name, func in functions:
        available_functions.append(func)
        function_metadata.append(generate_function_metadata(func))
        print(f"Function name: {name}, function object: {func}")
    global function_map
    function_map = {func.__name__: func for func in available_functions}

# Build function metadata dynamically
available_functions = [make_python_function]
function_metadata = [generate_function_metadata(func) for func in available_functions]

# Map for calling the functions
function_map = {func.__name__: func for func in available_functions}
load_python_functions()
# Interact with the AI
def chat_with_ai():
    print("Type 'exit' to end the chat.")
    
    while True:
        global chat_history
        # Get user input
        user_input = input(f"{GREEN}You: {RESET}")
        if user_input.lower() == "exit":
            print("Ending chat. Goodbye!")
            break
    
        chat_history.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Use a model that supports function calling
                messages=[instructions] + chat_history,
                tools=function_metadata,
            )            

            print_message(response)
            handle_function(response)

        except Exception as e:
            print(f"{RED}Error: {RESET}", e)

def print_message(response):
    message = response.choices[0].message
    global chat_history

    if (message.content):
        print(f"{GREEN}AI: {RESET}", message.content)
        chat_history.append({"role": "assistant", "content": message.content})

    if len(chat_history) > 10:
        chat_history = chat_history[-10:]

def handle_function(response):
    message = response.choices[0].message
    global chat_history
    if message.tool_calls == None:
        return
    
    for tc in message.tool_calls:
        function_name = tc.function.name
        arguments = eval(tc.function.arguments)

        if function_name in function_map:
            result = function_map[function_name](**arguments)
            print(f"{GREEN}Function{RESET} '{function_name}' called with {GREEN}arguments{RESET} {arguments}. {GREEN}Result:{RESET}\n{result}")
            chat_history.append({"role": "user", "content": f"Function '{function_name}' called with arguments {arguments}. Result: {result}"})
        else:
            print(f"Function '{function_name}' is not recognized.")

if __name__ == "__main__":
    chat_with_ai()