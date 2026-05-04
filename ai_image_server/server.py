from flask import Flask, request, jsonify, send_file
from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline
import torch
import io
import os
from datetime import datetime

app = Flask(__name__)

# Model cache
models = {
    'sd15': None,
    'sdxl': None
}

def load_model(model_name):
    if model_name == 'sd15' and models['sd15'] is None:
        print("Loading Stable Diffusion 1.5...")
        models['sd15'] = StableDiffusionPipeline.from_single_file(
            "models/v1-5-pruned-emaonly.safetensors",
            torch_dtype=torch.float16,
            use_safetensors=True
        )
        if torch.backends.mps.is_available():
            models['sd15'] = models['sd15'].to("mps")
        models['sd15'].enable_attention_slicing()

    elif model_name == 'sdxl' and models['sdxl'] is None:
        print("Loading Stable Diffusion XL...")
        models['sdxl'] = StableDiffusionXLPipeline.from_single_file(
            "models/sd_xl_base_1.0.safetensors",
            torch_dtype=torch.float16,
            use_safetensors=True
        )
        if torch.backends.mps.is_available():
            models['sdxl'] = models['sdxl'].to("mps")
        models['sdxl'].enable_attention_slicing()

@app.route('/generate', methods=['POST'])
def generate_image():
    data = request.json
    prompt = data.get('prompt', 'a beautiful landscape')
    model_type = data.get('model', 'sd15')  # Default to SD1.5

    try:
        # Load model if not loaded
        load_model(model_type)
        model = models[model_type]

        if model is None:
            return jsonify({'error': 'Model not found'}), 404

        # Generate image
        print(f"Generating image with {model_type}...")
        image = model(prompt).images[0]

        # Save to file (optional)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_{model_type}_{timestamp}.png"
        image.save(f"outputs/{filename}")

        # Return image
        img_io = io.BytesIO()
        image.save(img_io, 'PNG')
        img_io.seek(0)

        return send_file(img_io, mimetype='image/png')

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/models', methods=['GET'])
def list_models():
    return jsonify({
        'models': list(models.keys()),
        'active': [k for k, v in models.items() if v is not None]
    })

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('models', exist_ok=True)
    os.makedirs('outputs', exist_ok=True)

    # Check if models exist
    if not os.path.exists('models/v1-5-pruned-emaonly.safetensors'):
        print("Warning: SD1.5 model not found in models/ directory")
    if not os.path.exists('models/sd_xl_base_1.0.safetensors'):
        print("Warning: SDXL model not found in models/ directory")

    print("Server starting on http://0.0.0.0:5000")
    print("Available endpoints:")
    print("  POST /generate - Generate image")
    print("  GET  /models   - List available models")

    app.run(host='0.0.0.0', port=5000, debug=True)
