# No Paid Services Required

## Summary

**This Docker deployment solution uses NO paid services or external APIs.**

Everything runs locally on your own infrastructure at no cost beyond your hosting/compute expenses.

## What's Included (All Free)

### 1. **Chandra OCR Model**
- **Source**: HuggingFace Hub (`datalab-to/chandra-ocr-2`)
- **Cost**: Free to download and use (subject to license terms)
- **License**: Modified OpenRAIL-M (see [MODEL_LICENSE](MODEL_LICENSE))
- **Where it runs**: Downloaded once to your local machine/container

### 2. **vLLM Server**
- **Source**: Open source project (https://github.com/vllm-project/vllm)
- **Cost**: Free and open source (Apache 2.0 license)
- **Where it runs**: Locally in your Docker container
- **Purpose**: Optimized inference engine for the model

### 3. **HTTP API Server**
- **Source**: This repository (Flask-based)
- **Cost**: Free and open source (Apache 2.0 license)
- **Where it runs**: Locally in your Docker container
- **Purpose**: Accepts file uploads and returns OCR results

## No External API Calls

The solution does **NOT** make any calls to:
- ❌ Datalab's commercial API (https://www.datalab.to)
- ❌ OpenAI or other LLM APIs
- ❌ Any cloud services
- ❌ Any metered or paid endpoints

## How It Works

```
Your File → Docker Container → Local vLLM Server → Local Model → Results
            (on your server)   (on your server)    (on your disk)
```

Everything happens on your infrastructure:

1. **File Upload**: Sent to your local Flask server
2. **Processing**: Your local vLLM server processes with the model
3. **Model**: Downloaded once from HuggingFace, stored locally
4. **Results**: Returned directly from your server

## What You Need to Pay For

The only costs are your own infrastructure:

1. **Compute**: Server/VM to run Docker containers
2. **GPU** (optional but recommended): For faster inference with vLLM
3. **Storage**: ~20GB for the model weights
4. **Network**: Bandwidth for file uploads to your server

## Alternative: Using Datalab's Paid API

The README mentions Datalab's commercial API (https://www.datalab.to), but this is:
- **Optional** and completely separate
- **Not used** by this Docker deployment
- An alternative if you don't want to self-host

## Configuration Note

The `VLLM_API_BASE` setting defaults to `http://localhost:8000/v1`, which points to:
- The **local** vLLM server in your Docker container
- **NOT** an external paid service
- The docker-compose.yml sets this up automatically

You can verify this in the configuration:
- `docker-compose.yml`: Links `chandra-api` to local `vllm-server` service
- No external URLs or API keys required
- Everything runs in your private network

## License Considerations

While the software is free, note the model license:
- **Free for**: Research, personal use, startups under $2M funding/revenue
- **Requires license for**: Commercial use in competition with Datalab's API
- See [MODEL_LICENSE](MODEL_LICENSE) for full terms

The code itself (this HTTP API and Docker setup) is Apache 2.0 licensed and free for any use.

## Questions?

If you're concerned about costs:
1. Check your cloud provider's compute pricing (if using cloud)
2. GPU instances cost more but provide faster inference
3. CPU-only mode works but is much slower
4. All model inference happens locally - no per-request API fees

**Bottom Line**: This is a self-hosted, fully local solution with no external dependencies or paid services.
