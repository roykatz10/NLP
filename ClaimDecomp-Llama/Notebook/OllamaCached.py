import array
import os
from tqdm import tqdm
import ollama

# Set environment variable to save models to the models folder in the repository.
os.environ["OLLAMA_MODELS"] = "./models"
os.environ["OLLAMA_KEEP_ALIVE"] = "1m"


def check_and_download_model(model_name: str) -> None:
    """
    Checks if the specified LLM exists locally and downloads it if necessary.

    Args:
        model_name (str): Tag of the LLM.
    """
    model_exists: bool = False

    existing_models = ollama.list()["models"]
    for model in existing_models:
        if model["name"] == model_name:
            model_exists = True

    if not model_exists:
        print("Model Uncached - Downloading...")
        current_digest, bars = '', {}
        for progress in ollama.pull(model_name, stream=True):
            digest = progress.get('digest', '')
            if digest != current_digest and current_digest in bars:
                bars[current_digest].close()

            if not digest:
                print(progress.get('status'))
                continue

            if digest not in bars and (total := progress.get('total')):
                bars[digest] = tqdm(total=total, desc=f'pulling {digest[7:19]}', unit='B', unit_scale=True)

            if completed := progress.get('completed'):
                bars[digest].update(completed - bars[digest].n)

            current_digest = digest
        print("Download Complete.")
    else:
        print("Model Cached - Using Cached Version...")


if __name__ == '__main__':
    model_name = 'llama2'
    check_and_download_model(model_name)

def zero_shot(model_name: str, message: str) -> str:
    """
    Chat with the llm without any prior training (i.e. zero-shot)

    Args:
        model_name (str): Tag of the LLM.
        message (str): The prompt to provide to the LLM.
    Returns:
        response (str): The response from the assistant.
    """
    check_and_download_model(model_name)

    print("Zero Shot (" + model_name + "):")
    response = ollama.chat(model=model_name, messages=[{"role": "user", "content": message}], stream=False)
    return response["message"]["content"]


def few_shot(model_name: str, training_data: array, message: str) -> str:
    """
    Chat with the llm and provide some training samples for few-shot learning.

    Args:
        model_name (str): Tag of the LLM.
        training_data (array): The training data provided as an array in the format of (input, output).
        message (str): The prompt to provide to the LLM.
    Returns:
        response (str): The response from the assistant.
    """
    check_and_download_model(model_name)

    print("Few Shot (" + model_name + "): " + str(len(training_data)) + " Samples")
    few_shot_message = "\n\n"
    for pair in training_data:
        few_shot_message = "Input: " + pair[0] + "\nOutput: " + pair[1] + "\n"
    few_shot_message = few_shot_message + "\n\n" + message
    response = ollama.chat(model=model_name, messages=[{"role": "user", "content": few_shot_message}], stream=False)
    return response["message"]["content"]


def chain_of_reasoning_zero_shot(model_name: str, message: str) -> str:
    """
    Chat with the llm without any prior training (i.e. zero-shot), but with chain of thought reasoning.

    Args:
        model_name (str): Tag of the LLM.
        message (str): The prompt to provide to the LLM.
    Returns:
        response (str): The response from the assistant.
    """
    check_and_download_model(model_name)

    print("Chain of Reasoning - Zero Shot (" + model_name + "):")

    initial_messages = [
        {"role": "user", "content": message},
        {"role": "assistant", "content": "Let's think step by step."}
    ]
    complex_response = ollama.chat(model=model_name,
                                   messages=initial_messages,
                                   stream=False)
    response = ollama.chat(model=model_name,
                           messages=[
                               complex_response,
                               {"role": "assistant", "content": "Therefore, the final answer is "}
                           ],
                           stream=False)

    return response["message"]["content"]


def chain_of_reasoning_few_shot(model_name: str, training_data: array, message: str) -> str:
    """
    Chat with the llm and provide some training samples for few-shot learning, but also with chain of thought reasoning.

    Args:
        model_name (str): Tag of the LLM.
        training_data (array): The training data as an array in the form: (input, output), where output contains an
                               explanation of how to get to the answer including the final answer.
        message (str): The prompt to provide to the LLM.
    Returns:
        response (str): The response from the assistant.
    """
    check_and_download_model(model_name)

    print("Few Shot - Chain of Reasoning (" + model_name + "): " + str(len(training_data)) + " Samples")

    few_shot_message: str = "\n\n".join(
        training_data.map(lambda pair: "Input: " + pair[0] + "\nOutput: Let's think step by step. \n" + pair[1])
    )
    few_shot_message = few_shot_message + "\n\n" + message

    initial_messages = [
        {"role": "user", "content": few_shot_message},
        {"role": "assistant", "content": "Let's think step by step."}
    ]
    complex_response = ollama.chat(model=model_name,
                                   messages=initial_messages,
                                   stream=False)
    response = ollama.chat(model=model_name,
                           messages=[
                               initial_messages,
                               complex_response["message"],
                               {"role": "assistant", "content": "Therefore, the final answer is "}
                           ],
                           stream=False)

    return response["message"]["content"]
