from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/test', methods=['GET'])
def test_connection():
    return jsonify({'status': 'success', 'message': 'Local AI server is running!'})

@app.route('/models', methods=['GET'])
def list_models():
    return jsonify({
        'models': ['sd15', 'sdxl'],
        'active': ['sd15', 'sdxl'],
        'message': 'Models available for download'
    })

if __name__ == '__main__':
    print("🚀 Local AI Server starting...")
    print("📍 Server will be available at: http://0.0.0.0:5001")
    print("🔗 Test endpoint: http://localhost:5001/test")
    print("📋 Models endpoint: http://localhost:5001/models")
    app.run(host='0.0.0.0', port=5001, debug=True)
