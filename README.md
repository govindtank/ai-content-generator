# AI Content Generator

A versatile AI-powered content generation platform that provides both text completion and image generation capabilities through RESTful APIs.

## Features

- **Text Completion**: Generate human-like text using state-of-the-art language models
- **Image Generation**: Create high-quality images from text descriptions using diffusion models
- **RESTful API**: Easy-to-use HTTP endpoints for integration with any application
- **Scalable Design**: Built with Flask for easy deployment and scaling
- **Model Flexibility**: Supports multiple AI models that can be easily swapped

## Architecture

The project consists of two main services:

1. **AI Completion Service** (`ai_completion/`) - Text generation capabilities
2. **AI Image Server** (`ai_image_server/`) - Image generation using Stable Diffusion models

## Setup

### Prerequisites

- Python 3.8+
- Git LFS (for downloading model files)
- At least 8GB RAM recommended for model loading

### Installation

```bash
# Clone the repository
git clone https://github.com/govindtank/ai-content-generator.git
cd ai-content-generator

# Install Git LFS (required for model files)
git lfs install
git lfs pull

# Install Python dependencies
pip install -r ai_image_server/requirements.txt
pip install -r ai_completion/requirements.txt
```

### Model Downloads

The AI models are large files (>100MB each) and are not stored in this repository due to GitHub limitations. They will be automatically downloaded on first run or can be manually downloaded:

```bash
# For text completion models (example)
mkdir -p ai_completion/models
# Download your preferred LLM model (e.g., from HuggingFace)

# For image generation models
mkdir -p ai_image_server/models
# The server will automatically download Stable Diffusion weights on first run
# Or manually place:
# - sd_xl_base_1.0.safetensors
# - v1-5-pruned-emaonly.safetensors
```

## Usage

### Start the Services

```bash
# Start the image generation server
cd ai_image_server
python server.py

# In another terminal, start the completion service
cd ../ai_completion
python server.py
```

### API Endpoints

#### Image Generation
```
POST /generate-image
Content-Type: application/json

{
  "prompt": "A beautiful sunset over mountains",
  "negative_prompt": "low quality, blurry",
  "width": 512,
  "height": 512,
  "num_inference_steps": 30,
  "guidance_scale": 7.5
}
```

#### Text Completion
```
POST /generate-text
Content-Type: application/json

{
  "prompt": "Once upon a time",
  "max_length": 100,
  "temperature": 0.7,
  "top_p": 0.9
}
```

## Configuration

Edit `config.json` in the `ai_completion/` directory to adjust:
- Model paths
- Generation parameters
- Server ports

## Development

### Project Structure
```
ai-content-generator/
├── ai_completion/          # Text generation service
│   ├── server.py
│   └── config.json
├── ai_image_server/        # Image generation service
│   ├── server.py           # Main Flask server
│   ├── simple_server.py    # Alternative implementation
│   └── models/             # Stable Diffusion model files (not in repo)
└── README.md
```

## Deployment

### Docker (Coming Soon)
Dockerfiles will be provided for easy containerized deployment.

### Cloud Deployment
The services can be deployed to any cloud platform that supports Python applications (AWS, GCP, Azure, etc.).

## Model Attribution

- Stable Diffusion XL Base 1.0: Stability AI
- Stable Diffusion v1.5: CompVis/Stability AI

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Contact

For questions or support, please open an issue on GitHub.

---
*Built with ❤️ by Hermes Agent*
