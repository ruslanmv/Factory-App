import gradio as gr
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

try:
    df_generated = load_generated_data(BASE_PATH, OUTPUT_PICKLE)
    file_choices = df_generated["path"].tolist()
except Exception as e:
    df_generated = None
    file_choices = []
    print(f"Error loading generated data: {e}")

def display_file_content(file_path):
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


# Gradio app
with gr.Blocks() as app:
    gr.Markdown("## File Explorer for Generated Content")

    with gr.Column():  # Use Column to stack elements vertically
        file_selector = gr.Dropdown(label="Select a File", choices=file_choices, interactive=True)
        file_content = gr.Textbox(label="File Content", lines=20, interactive=False)

    # Update file content display on file selection
    file_selector.change(display_file_content, inputs=file_selector, outputs=file_content)








# Run the app
if __name__ == "__main__":
    app.launch(debug=True)
