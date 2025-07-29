import subprocess

# Base command
base_command = (
    "genai-perf profile -m nvidia/nv-rerankqa-mistral-4b-v3 "
    "--service-kind openai --endpoint-type rankings "
    "-u http://10.96.3.49:8000 "
    "--extra-inputs truncate:END "
    "--input-file synthetic:queries,passages -v"
)

# Parameter combinations
parameters = [
    {"synthetic_input_tokens_mean": 512, "batch_size_text": 10, "concurrency": 1},
    {"synthetic_input_tokens_mean": 512, "batch_size_text": 10, "concurrency": 3},
    {"synthetic_input_tokens_mean": 512, "batch_size_text": 10, "concurrency": 5},
    {"synthetic_input_tokens_mean": 512, "batch_size_text": 20, "concurrency": 1},
    {"synthetic_input_tokens_mean": 512, "batch_size_text": 20, "concurrency": 3},
    {"synthetic_input_tokens_mean": 512, "batch_size_text": 20, "concurrency": 5},
    {"synthetic_input_tokens_mean": 512, "batch_size_text": 40, "concurrency": 1},
    {"synthetic_input_tokens_mean": 512, "batch_size_text": 40, "concurrency": 3},
    {"synthetic_input_tokens_mean": 512, "batch_size_text": 40, "concurrency": 5},
]

# Loop through each parameter set and execute the command
for param in parameters:
    command = (
        f"{base_command} "
        f"--synthetic-input-tokens-mean {param['synthetic_input_tokens_mean']} "
        f"--batch-size-text {param['batch_size_text']} "
        f"--concurrency {param['concurrency']}"
    )
    print(f"Executing: {command}")
    try:
        # Execute the command
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"Output:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while executing the command:\n{e.stderr}")

