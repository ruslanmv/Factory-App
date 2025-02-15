import os
import pandas as pd
import asyncio
import json
from huggingface_hub import AsyncInferenceClient
import gradio as gr
from dotenv import load_dotenv
import os
from openai import OpenAI
from dotenv import load_dotenv
# Load the API key from the .env file
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")
# --- Utility Functions ---

# Set the base folder for the generated project
current_directory = os.getcwd()
project_name = "generated"
path_project = os.path.join(current_directory, project_name)
os.makedirs(path_project, exist_ok=True)  # Ensure the folder exists

async def generate_code_hf(prompt: str) -> str:
    """
    Generate code using a language model based on the provided prompt.

    Args:
        prompt: The prompt describing the required file or update.

    Returns:
        Generated code.
    """
    client = AsyncInferenceClient(HF_API_KEY)
    try:
        response = await client.post(
            model="codellama/CodeLlama-34b-Instruct-hf",
            inputs=prompt,
            parameters={"do_sample": True, "max_new_tokens": 512, "return_full_text": False},
        )
        return response.get("generated_text", "").strip()
    except Exception as e:
        return f"Error: {e}"
# Load the API key from the .env file
client = OpenAI(api_key=OPENAI_API_KEY)
async def generate_code(prompt: str) -> str:
    """
    Generate code using OpenAI's GPT-4o API based on the provided prompt.

    Args:
        prompt: The prompt describing the required file or update.

    Returns:
        Generated code.
    """
    try:
        # Create a chat completion using OpenAI's GPT-4o model
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a code generator application. Simply return the raw code content based on requests."},
                {"role": "user", "content": prompt}
            ]
        )
        # Extract and return the generated code from the completion
        return completion.choices[0].message.content.strip()
    except Exception as e:
        # Return an error message in case of failure
        return f"Error: {e}"

def save_file(file_path: str, content: str):
    """
    Save content to a file.

    Args:
        file_path: The file path where content will be saved.
        content: Content to save.
    """
    full_path = os.path.join(path_project, file_path.lstrip("./"))

    # Check if the path is a directory and create it
    if full_path.endswith("/") or os.path.basename(full_path) == "":
        os.makedirs(full_path, exist_ok=True)
        return  # No file to write if it's a directory
    # Ensure the parent directory exists
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    # Write the file content
    with open(full_path, "w", encoding="utf-8") as file:
        file.write(content)

def load_file(file_path: str) -> str:
    """
    Load content from a file.

    Args:
        file_path: The file path to read content from.

    Returns:
        File content as a string.
    """
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    return ""


def create_metadata(tree: list) -> pd.DataFrame:
    """
    Create a DataFrame for project metadata.

    Args:
        tree: A list of dictionaries with project structure.

    Returns:
        A DataFrame containing file paths and descriptions.
    """
    df = pd.DataFrame(tree)
    os.makedirs(path_project, exist_ok=True)
    metadata_path = os.path.join(path_project, "metadata.pkl")
    df.to_pickle(metadata_path)
    return df


import re

def extract_markdown_code(llm_output: str) -> str:
    """
    Extracts all code blocks from the LLM output, enclosed in triple backticks.

    Args:
        llm_output (str): The raw output generated by the LLM.

    Returns:
        str: The cleaned code content containing all valid code blocks, 
             or a message indicating no code was found.
    """
    try:
        # Find all code blocks enclosed in triple backticks
        code_blocks = re.findall(r"```(?:\w+\n)?(.*?)```", llm_output, re.DOTALL)  
        
        # Concatenate all extracted code blocks, each separated by a newline
        extracted_code = "\n\n".join(block.strip() for block in code_blocks if block.strip())
        
        # Return the extracted code or a message if no code blocks are found
        return extracted_code if extracted_code else "No code blocks found."
    except Exception as e:
        return f"Error in extracting code: {e}"

async def build_project(df: pd.DataFrame):
    """
    Build the project dynamically, updating dependencies and main files iteratively.

    Args:
        df: DataFrame containing the project structure.

    Returns:
        Generation status.
    """
    generated_files = {}  # Store generated code for each file
    pending_files = list(df.itertuples(index=False))

    while pending_files:
        file_info = pending_files.pop(0)
        path, description = file_info.path, file_info.description

        # Skip directories; ensure they exist
        if path.endswith("/") or os.path.basename(path) == "":
            os.makedirs(os.path.join(path_project, path.lstrip("./")), exist_ok=True)
            continue

        # Build dependency files first
        dependencies = [dep for dep in generated_files.keys() if dep != path]
        dependency_code = "\n".join([f"### Dependency: {dep}\n{generated_files[dep]}" for dep in dependencies])

        # Create a prompt with the dependency code (if any)
        prompt = (
            f"You are building a project. The following dependencies have been written:\n\n"
            f"{dependency_code}\n\n"
            f"Now create or update the file at '{path}' based on its purpose:\n{description}\n\n"
            f"If the file is a main application, ensure it calls all dependencies correctly."
            "Output only the code required for this file. Do not include explanations, comments, or additional context. "
            "Simply return the raw code content."
        )

        # Extract the file extension
        _, extension = os.path.splitext(path)

        # Modify the prompt for specific extensions
        if extension == ".md":
            prompt += " Please create a professional README of this project."


        print("Creating the prompt...")
        print("prompt: ",prompt)
        # Generate code for the current file
        print("Generating the code ...")
        generated_code = await generate_code(prompt)
        #print("Code generated:")
        #print(generated_code)
        generated_code=extract_markdown_code(generated_code)
        print("Code generated clean:")
        print(generated_code)
        previous_code = generated_files.get(path, "")

        # Check if the main file needs updating
        if path in generated_files and previous_code != generated_code:
            # Add the main file back to the pending queue for re-generation
            pending_files.append(file_info)

        # Save the generated code and update the in-memory dictionary
        save_file(path, generated_code)
        generated_files[path] = generated_code

    return "Project built successfully!"
# --- Gradio Interface Functions ---

import json
import re
import os

def clean_and_extract_json(llm_output):
    """
    Cleans the LLM output to extract a valid JSON structure and adjusts paths.

    Args:
        llm_output (str): The raw output generated by the LLM.

    Returns:
        list: Parsed JSON object if successful, otherwise a default error structure.
    """
    try:
        if not llm_output.strip():
            raise ValueError("Empty output from LLM.")

        # Extract JSON content from between code blocks or explanatory text
        json_match = re.search(r"```json\s*(\[\s*{.*?}\s*]\s*)```", llm_output, re.DOTALL)
        if not json_match:
            raise ValueError("No valid JSON block found.")

        # Clean the extracted JSON block
        cleaned_output = json_match.group(1).strip()

        # Attempt to parse as JSON
        extracted_json = json.loads(cleaned_output)

        # Ensure the extracted JSON is a list of dictionaries with 'path' and 'description' keys
        if not isinstance(extracted_json, list) or not all(
            isinstance(item, dict) and "path" in item and "description" in item for item in extracted_json
        ):
            raise ValueError("Invalid project tree format.")

        # Prepend "./generated/" to all paths
        for item in extracted_json:
            item['path'] = os.path.join("./generated", item['path'].lstrip("./"))
        
        return extracted_json

    except (json.JSONDecodeError, ValueError) as e:
        # Handle JSON decoding or validation errors
        return [{'path': './generated/error.txt', 'description': f'Error: {str(e)}'}]

import shutil
def clean_generated_folder():
    """
    Deletes the 'generated' folder and its contents.

    Returns:
        Status message.
    """
    try:
        shutil.rmtree(path_project)
        return "Generated folder cleaned successfully."
    except Exception as e:
        return f"Error in cleaning the generated folder: {str(e)}"


def format_project_tree(tree):
    """
    Converts a project tree into a human-readable format for display in Gradio.
    """
    try:
        # Validate the input is a list of dictionaries
        if not isinstance(tree, list) or not all(isinstance(item, dict) for item in tree):
            return "Invalid project tree format. Expected a list of dictionaries."

        # Build a readable string from the project tree
        formatted_tree = "### Project Tree\n"
        for item in tree:
            path = item.get("path", "Unknown Path")
            description = item.get("description", "No description provided.")
            formatted_tree += f"- **Path**: `{path}`\n  - **Description**: {description}\n\n"

        return formatted_tree.strip()
    except Exception as e:
        return f"Error formatting project tree: {str(e)}"



async def step_1(instruction: str, framework: str):
    """
    Step 1: Generate the project tree using the instruction and framework.

    Args:
        instruction: High-level project requirement.
        framework: Selected framework.

    Returns:
        Project tree as a Python list of dictionaries.
    """
    tree_prompt = (
        f"Based on the following instruction and selected framework, generate a project structure as a JSON list of dictionaries.\n"
        f"Instruction: {instruction}\n"
        f"Framework: {framework}\n\n"
        f"Format each entry with 'path' (file path) and 'description' (purpose of the file).\n"
        f"Example: [{{'path': './src/main.py', 'description': 'Main application entry point.'}}, "
        f"{{'path': './src/utils/logging.py', 'description': 'Logging utilities.'}}]"
    )
    print("First prompt:", tree_prompt)

    # Generate project tree
    tree = await generate_code(tree_prompt)
    print("AI :", tree)
    # Clean and extract JSON
    tree = clean_and_extract_json(tree)
    print("Cleaned:", tree)

    # Validate and handle errors
    if isinstance(tree, list) and all("path" in item and "description" in item for item in tree):
        # If tree is valid, save metadata
        df = create_metadata(tree)
        return f"Project Tree:\n{tree}"
    else:
        # Handle invalid format
        return [{"path": "./generated/error.txt", "description": "Invalid project tree format or JSON parsing error."}]

async def step_2():
    """
    Step 2: Generate the project files dynamically with dependency updates.

    Returns:
        Generation status.
    """
    metadata_path = os.path.join(path_project, "metadata.pkl")
    df = pd.read_pickle(metadata_path)
    return await build_project(df)

def step_3():
    """
    Step 3: Validate the generated files.

    Returns:
        Validation results.
    """
    # Define paths for metadata and validated metadata in the 'generated' folder
    metadata_path = os.path.join(path_project, "metadata.pkl")
    validated_metadata_path = os.path.join(path_project, "validated_metadata.pkl")

    # Load the metadata DataFrame
    df = pd.read_pickle(metadata_path)

    # Validate each file's existence and size in the 'generated' folder
    df["validation"] = df["path"].apply(lambda x: os.path.exists(os.path.join(path_project, x.lstrip("./"))) 
                                        and os.path.getsize(os.path.join(path_project, x.lstrip("./"))) > 0)
    
    # Save the updated DataFrame with validation results
    df.to_pickle(validated_metadata_path)




    # Return the validation results as a subset of the DataFrame
    return df[["path", "validation"]]

def step_4():
    """
    Step 4: Create a Dockerfile for the project and save the project in a zip file.

    Returns:
        A tuple containing the status message and the path to the zip file for download.
    """
    # Create Dockerfile content
    dockerfile_content = """
    FROM python:3.9-slim
    WORKDIR /app
    COPY . .
    RUN pip install -r requirements.txt
    CMD ["python", "./src/main.py"]
    """
    save_file("./Dockerfile", dockerfile_content.strip())
    
    # Path for the zip file
    zip_file_path = os.path.join(current_directory, f"{project_name}.zip")
    
    try:
        # Create a zip file of the project
        shutil.make_archive(base_name=path_project, format='zip', root_dir=path_project)
        return f"Dockerfile created and project saved as a zip file.", zip_file_path
    except Exception as e:
        # If zipping fails, return an error message and None for the file path
        return f"Error in zipping the project: {str(e)}", None




import pandas as pd
from utils.display_and_store_directory_content import display_and_store_directory_content

def load_generated_data(base_path, output_pickle):
    """
    Extract all content and paths from the given directory,
    save them in a pickle file, and load them for Gradio display.

    Args:
        base_path (str): Directory to scan.
        output_pickle (str): Path to save the pickle file.

    Returns:
        pd.DataFrame: DataFrame containing the paths and content.
    """
    # Run the display_and_store_directory_content utility
    display_and_store_directory_content(base_path)

    # Load the generated pickle file into a DataFrame
    try:
        df = pd.read_pickle(output_pickle)
        if df.empty:
            raise ValueError("The DataFrame is empty. Check the directory contents.")
        if not {"path", "content"}.issubset(df.columns):
            raise ValueError(f"Pickle file does not contain the required columns: {df.columns}")
        return df
    except Exception as e:
        raise ValueError(f"Error loading pickle file: {e}")


# Load data from the generated directory
BASE_PATH = "./generated/generated"
OUTPUT_PICKLE = "./extraction/generated.pkl"

def update_explorer():
    """
    Load the generated data and prepare file choices for the dropdown.
    """
    df = load_generated_data(BASE_PATH, OUTPUT_PICKLE)
    file_choices = df["path"].tolist()  # Extract file paths for the dropdown
    return df, file_choices


def display_file_content(file_path,df_generated):
    """
    Retrieve the content of the selected file from the pickle DataFrame.

    Args:
        file_path (str): Path of the selected file.

    Returns:
        str: Content of the file or an error message if unavailable.
    """
    try:
        # Retrieve content for the selected file
        if df_generated is None:
            raise ValueError("Data not loaded. Check the pickle file.")
        content = df_generated.loc[df_generated["path"] == file_path, "content"].values[0]
        return content
    except Exception as e:
        return f"Error loading file content: {e}"

# --- Gradio Interface ---
def app():
    with gr.Blocks() as interface:
        gr.Markdown("# Project Generation with Generative AI")

        with gr.Tab("Step 1: Define Project Tree"):
            framework_dropdown = gr.Dropdown(
                choices=["Gradio", "Flask", "Streamlit", "Django", "React"],
                label="Select Framework",
            )
            instruction_input = gr.Textbox(
                label="Project Instruction",
                placeholder="Describe the project (e.g., 'Generate a project that says hello world and logs messages').",
                lines=2,
            )
            tree_output = gr.Textbox(label="Generated Project Tree")
            generate_tree_button = gr.Button("Generate Project Tree")
            generate_tree_button.click(
                step_1, inputs=[instruction_input, framework_dropdown], outputs=tree_output
            )




        with gr.Tab("Step 2: Generate Files"):
            generate_files_button = gr.Button("Generate Project Files")
            files_output = gr.Textbox(label="File Generation Status")
            generate_files_button.click(step_2, outputs=files_output)

        with gr.Tab("Step 3: Validate and Display Files"):
            # Button to validate files
            validate_button = gr.Button("Validate Project Files")
            validation_output = gr.DataFrame(label="Validation Results")
            validate_button.click(step_3, outputs=validation_output)


            explorer_button = gr.Button("Explore Project Files")

            # Use gr.State for DataFrame and file list storage
            explorer_output = gr.State()  # To store the DataFrame
            file_choices_output = gr.State()  # To store the file list

            gr.Markdown("## File Explorer for Generated Content")

            with gr.Column():
                file_selector = gr.Dropdown(label="Select a File", choices=[], interactive=True)
                file_content = gr.Textbox(label="File Content", lines=20, interactive=False)

            # Update file choices dynamically
            explorer_button.click(
                update_explorer,
                outputs=[explorer_output, file_choices_output]
            )

            # Update the file selector dropdown dynamically
            def update_file_selector(file_choices):
                if not file_choices:  # Handle empty list
                    return gr.update(choices=[], value=None)
                return gr.update(choices=file_choices, value=file_choices[0])

            file_choices_output.change(
                update_file_selector,
                inputs=[file_choices_output],
                outputs=file_selector
            )

            # Display file content dynamically when a file is selected
            def display_file_content_safe(file_path, df):
                try:
                    content = df.loc[df["path"] == file_path, "content"].values[0]
                    return content
                except Exception as e:
                    return f"Error loading file content: {e}"

            file_selector.change(
                display_file_content_safe,
                inputs=[file_selector, explorer_output],
                outputs=file_content
            )




        with gr.Tab("Step 4: Containerize Project"):
            containerize_button = gr.Button("Create Dockerfile and Save as Zip")
            containerize_output = gr.Textbox(label="Containerization Status")
            download_link = gr.File(label="Download Project Zip")

            # Wrapper function to ensure proper output handling
            def handle_step_4():
                status, zip_path = step_4()
                if zip_path and os.path.exists(zip_path):
                    return status, zip_path
                else:
                    return status, None  # Provide None for the File component if zip creation fails

            # Link the button to `step_4` and ensure outputs are handled correctly
            containerize_button.click(
                handle_step_4, 
                outputs=[containerize_output, download_link]  # Two outputs as expected
            )

            clean_button = gr.Button("Clean Generated Folder")
            clean_output = gr.Textbox(label="Clean Status")
            clean_button.click(clean_generated_folder, outputs=clean_output)


    interface.launch()

# Run the app
if __name__ == "__main__":
    dev = False
    if dev:
        instruction_input = "Generate a project that says hello world"
        framework_dropdown = "Gradio"

        # Testing Step 1
        step_1_out = asyncio.run(step_1(instruction_input, framework_dropdown))
        print("Step 1 Output:", step_1_out)

        # Testing Step 2
        step_2_out = asyncio.run(step_2())
        print("Step 2 Output:", step_2_out)

        # Testing Step 3
        step_3_out = step_3()
        print("Step 3 Output:", step_3_out)

        # Testing Step 4
        step_4_out = step_4()
        print("Step 4 Output:", step_4_out)
    else:
        app()