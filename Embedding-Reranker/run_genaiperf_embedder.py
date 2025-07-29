import subprocess

# Fixed parameters
model = "nvidia/nv-embedqa-e5-v5"
url = "http://10.96.2.144:8000"
service_kind = "openai"
endpoint_type = "embeddings"
extra_inputs = {"truncate": "END"}

# Test combinations exactly as per image
test_cases = [
    # passage rows
    {"input_type": "passage", "input_tokens": 300, "batch_size": 64, "concurrency": 1},
    {"input_type": "passage", "input_tokens": 300, "batch_size": 64, "concurrency": 3},
    {"input_type": "passage", "input_tokens": 300, "batch_size": 64, "concurrency": 5},
    {"input_type": "passage", "input_tokens": 512, "batch_size": 64, "concurrency": 1},
    {"input_type": "passage", "input_tokens": 512, "batch_size": 64, "concurrency": 3},
    {"input_type": "passage", "input_tokens": 512, "batch_size": 64, "concurrency": 5},

    # query rows
    {"input_type": "query", "input_tokens": 20, "batch_size": 1, "concurrency": 1},
    {"input_type": "query", "input_tokens": 20, "batch_size": 1, "concurrency": 3},
    {"input_type": "query", "input_tokens": 20, "batch_size": 1, "concurrency": 5},
    {"input_type": "query", "input_tokens": 20, "batch_size": 1, "concurrency": 7},
    {"input_type": "query", "input_tokens": 20, "batch_size": 1, "concurrency": 9},
    {"input_type": "query", "input_tokens": 20, "batch_size": 1, "concurrency": 11},
    {"input_type": "query", "input_tokens": 20, "batch_size": 1, "concurrency": 13},
    {"input_type": "query", "input_tokens": 20, "batch_size": 1, "concurrency": 15},
]

# Run each configuration
for case in test_cases:
    cmd = [
        "genai-perf", "profile",
        "-m", model,
        "--service-kind", service_kind,
        "--endpoint-type", endpoint_type,
        "--batch-size", str(case["batch_size"]),
        "--synthetic-input-tokens-mean", str(case["input_tokens"]),
        "--extra-inputs", f"input_type:{case['input_type']}",
        "--extra-inputs", f"truncate:{extra_inputs['truncate']}",
        "--concurrency", str(case["concurrency"]),
        "--url", url,
        "-v"
    ]

    print(f"\n▶ Running: input_type={case['input_type']}, tokens={case['input_tokens']}, "
          f"batch={case['batch_size']}, concurrency={case['concurrency']}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")

